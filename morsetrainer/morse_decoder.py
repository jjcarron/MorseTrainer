"""Décodage Morse à partir d'un flux audio live ou d'un fichier."""
# pylint: disable=duplicate-code,broad-exception-caught,too-many-instance-attributes

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import wave
import time
import signal
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

try:  # pragma: no cover - Windows only
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None

try:
    import sounddevice as sd
except ImportError:
    sd = None  # sounddevice is optional; required for live capture

try:
    import yaml
except ImportError:
    yaml = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None  # optional, for decoding mp3/ogg/etc.

MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "(": "-.--.",
    ")": "-.--.-",
    "&": ".-...",
    ":": "---...",
    ";": "-.-.-.",
    "=": "-...-",
    "+": ".-.-.",
    "-": "-....-",
    "_": "..--.-",
    '"': ".-..-.",
    "$": "...-..-",
    "@": ".--.-.",
}

MORSE_REVERSE = {v: k for k, v in MORSE.items()}

DEFAULT_CONFIG_PATHS = [
    os.path.join("config", "morse_decoder.yaml"),
    "morse_decoder.yaml",
]
DEFAULT_OUTPUT_DIR = "data"
DEFAULT_TARGET_RATE = 44100
DEFAULT_QUIT_KEY = "q"


def load_yaml_config(paths: List[str]) -> Dict[str, Any]:
    """Charge le premier fichier YAML existant parmi la liste."""
    if yaml is None:
        return {}
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as cfg_file:
                data = yaml.safe_load(cfg_file) or {}
                if isinstance(data, dict):
                    return data
    return {}


def validate_decoder_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Valide et normalise les valeurs de configuration issues du YAML."""
    cfg = dict(raw or {})

    def positive(name: str, default: Union[int, float]) -> Union[int, float]:
        val = cfg.get(name, default)
        if val is None:
            return default
        if not isinstance(val, (int, float)) or val <= 0:
            raise ValueError(f"{name} doit etre un nombre positif")
        return val

    validated = {
        "output_dir": cfg.get("output_dir", DEFAULT_OUTPUT_DIR),
        "debug": bool(cfg.get("debug", False)),
        "unit_ms": positive("unit_ms", 60.0),
        "dash_units": positive("dash_units", 2.0),
        "letter_gap_units": positive("letter_gap_units", 9.0),
        "word_gap_units": positive("word_gap_units", 20.0),
        "freq": positive("freq", 600.0),
        "rate": positive("rate", DEFAULT_TARGET_RATE),
        "blocksize": int(positive("blocksize", 1024)),
        "threshold": cfg.get("threshold"),
        "word_sep": cfg.get("word_sep", " "),
        "target_rate": positive("target_rate", DEFAULT_TARGET_RATE),
        "quit_key": cfg.get("quit_key", DEFAULT_QUIT_KEY),
        "device": cfg.get("device"),
    }
    thr = validated["threshold"]
    if thr is not None:
        if not isinstance(thr, (int, float)) or thr <= 0:
            raise ValueError("threshold doit etre > 0 ou None")
        validated["threshold"] = float(thr)
    return validated


@dataclass
class DecoderConfig:
    """Configuration des seuils et de la cadence Morse."""

    unit_ms: float = 60.0  # base Morse unit (dot length), ~20 WPM
    dash_units: float = 2.0  # threshold (in units) to decide dash vs dot
    letter_gap_units: float = 9.0  # >= means end of letter
    word_gap_units: float = 20.0  # >= means space
    min_rms_threshold: float = 0.02  # floor to avoid zero threshold
    on_hysteresis: float = 1.2  # multiplier for noise floor
    calibration_seconds: float = 2.0
    target_freq: Optional[float] = None  # if set, use Goertzel band energy


class MorseDecoder:  # pylint: disable=too-many-instance-attributes
    """Machine à états pour transformer un flux audio en texte Morse."""

    def __init__(
        self,
        cfg: DecoderConfig,
        output: Callable[[str], None],
        debug: bool = False,
        space_char: str = " ",
    ):
        self.cfg = cfg
        self.output = output
        self.current_state = False  # False = silence, True = tone
        self.state_time = 0.0
        self.current_pattern: List[str] = []
        self.rms_threshold: Optional[float] = None
        self.debug = debug
        self._debug_events = 0
        self.max_debug_events = 400
        self.space_char = space_char
        self.gap_state: Optional[str] = None  # None, "letter", "word"

    def set_threshold(self, noise_levels: List[float], user_threshold: Optional[float]):
        """Calcule ou applique le seuil de détection."""
        if user_threshold is not None:
            self.rms_threshold = max(user_threshold, self.cfg.min_rms_threshold)
            return

        if not noise_levels:
            self.rms_threshold = self.cfg.min_rms_threshold
            return

        noise_mean = float(np.mean(noise_levels))
        noise_std = float(np.std(noise_levels))
        auto = max(
            noise_mean + 3 * noise_std,
            noise_mean * self.cfg.on_hysteresis,
            self.cfg.min_rms_threshold,
        )
        self.rms_threshold = auto

    def process_block(self, block: np.ndarray, sample_rate: int):
        """Consume an audio block and update Morse state machine."""
        if block.size == 0:
            return

        level = measure_level(block, sample_rate, self.cfg.target_freq)
        block_duration = block.size / sample_rate

        if self.rms_threshold is None:
            raise RuntimeError("Threshold not initialized")

        is_on = level > self.rms_threshold

        if is_on == self.current_state:
            self.state_time += block_duration
            if not is_on:
                duration_ms = self.state_time * 1000.0
                units = duration_ms / self.cfg.unit_ms
                if units >= self.cfg.word_gap_units and self.gap_state != "word":
                    self._flush_symbol()
                    self.output(self.space_char)
                    self.gap_state = "word"
                elif (
                    units >= self.cfg.letter_gap_units
                    and self.gap_state not in ("letter", "word")
                ):
                    self._flush_symbol()
                    self.gap_state = "letter"
            return

        # Transition : traiter la durée de l'état précédent, puis démarrer le nouveau
        duration_ms = self.state_time * 1000.0
        if self.current_state:
            self._handle_tone(duration_ms)
        else:
            if self.gap_state is None:
                self._handle_gap(duration_ms)

        self.current_state = is_on
        self.state_time = block_duration
        self.gap_state = None

    def finalize(self):
        """Flush pending tone/gap when stream ends."""
        # Treat remaining state as silence gap to close current symbol.
        if self.current_state:
            self._handle_tone(self.state_time * 1000.0)
            self.current_state = False
            self.state_time = 0.0
        if self.gap_state is None:
            self._handle_gap(self.state_time * 1000.0, final=True)

    def _handle_tone(self, duration_ms: float):
        """Ajoute un point ou un tiret selon la durée du ton."""
        units = duration_ms / self.cfg.unit_ms
        symbol = "." if units < self.cfg.dash_units else "-"
        if self.debug and self._debug_events < 200:
            print(
                f"\n[TONE] {duration_ms:.1f} ms ({units:.2f} u) -> {symbol}",
                file=sys.stderr,
            )
            self._debug_events += 1
        self.current_pattern.append(symbol)

    def _handle_gap(self, duration_ms: float, final: bool = False):
        """Gère une pause pour savoir si on termine un symbole ou un mot."""
        units = duration_ms / self.cfg.unit_ms
        if units >= self.cfg.word_gap_units:
            self._flush_symbol()
            self.output(self.space_char)
        elif units >= self.cfg.letter_gap_units:
            self._flush_symbol()
        elif final:
            self._flush_symbol()
        if self.debug and self._debug_events < 200:
            print(f"\n[GAP ] {duration_ms:.1f} ms ({units:.2f} u)", file=sys.stderr)
            self._debug_events += 1

    def _flush_symbol(self):
        """Pousse le symbole courant vers la sortie sous forme de caractère."""
        if not self.current_pattern:
            return
        code = "".join(self.current_pattern)
        char = MORSE_REVERSE.get(code, "?")
        self.output(char)
        self.current_pattern.clear()


def list_devices():
    """Affiche la liste des périphériques audio disponibles."""
    if sd is None:
        print("sounddevice non installe. Installez-le avec: pip install sounddevice")
        return

    print(sd.query_devices())


def read_wave_file(path: str, blocksize: int):
    """Lit un fichier WAV et renvoie des blocs normalisés."""
    with wave.open(path, "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(width)
        if dtype is None:
            raise ValueError(f"Unsupported sample width: {width}")

        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=dtype).astype(np.float32)
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        # Normalize to [-1, 1]
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val

        cursor = 0
        while cursor < audio.size:
            yield audio[cursor : cursor + blocksize], sample_rate
            cursor += blocksize


def read_audio_file(path: str, blocksize: int, target_rate: int = DEFAULT_TARGET_RATE):
    """Lit un fichier audio (wav ou via pydub) et renvoie des blocs normalisés."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        yield from read_wave_file(path, blocksize)
        return

    if AudioSegment is None:
        # Fallback: tenter une conversion rapide via ffmpeg si disponible.
        if not shutil.which("ffmpeg"):
            raise ValueError(
                f"Format {ext} non supporte sans pydub ni ffmpeg. "
                f"Installez 'pydub' + ffmpeg ou convertissez en WAV "
                f"(ex: ffmpeg -i input{ext} output.wav)."
            )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    path,
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    str(target_rate),
                    tmp_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode != 0:
                raise ValueError(f"ffmpeg n'a pas pu convertir {path}")
            yield from read_wave_file(tmp_path, blocksize)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return

    ffmpeg_bin = AudioSegment.converter or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise ValueError(
            "ffmpeg introuvable. Installez ffmpeg et ajoutez-le au PATH "
            "(ou definissez FFMPEG_BINARY=<chemin/vers/ffmpeg.exe>)"
        )

    segment = AudioSegment.from_file(path)
    segment = segment.set_channels(1).set_frame_rate(target_rate)
    sample_rate = segment.frame_rate
    samples = np.array(segment.get_array_of_samples()).astype(np.float32)

    max_val = float(np.max(np.abs(samples))) or 1.0
    samples = samples / max_val

    cursor = 0
    while cursor < samples.size:
        yield samples[cursor : cursor + blocksize], sample_rate
        cursor += blocksize


def measure_level(block: np.ndarray, sample_rate: int, target_freq: Optional[float]):
    """Return energy level of the block; if target_freq set, use Goertzel at that freq."""
    if block.size == 0:
        return 0.0
    if target_freq is None:
        return float(np.sqrt(np.mean(np.square(block))))

    n = block.size
    k = int(0.5 + (n * target_freq) / sample_rate)
    if k <= 0 or k >= n:
        return float(np.sqrt(np.mean(np.square(block))))

    omega = (2.0 * np.pi * k) / n
    coeff = 2.0 * np.cos(omega)
    s_prev = 0.0
    s_prev2 = 0.0

    for x in block:
        s = x + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s

    real = s_prev - s_prev2 * np.cos(omega)
    imag = s_prev2 * np.sin(omega)
    magnitude = np.sqrt(real * real + imag * imag) / n
    return float(magnitude)


def capture_stream(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    args, decoder: MorseDecoder, record_path: Optional[str] = None
):
    """Capture live audio via sounddevice et envoie les blocs au décodeur."""
    if sd is None:
        print("sounddevice non installe. Installez-le avec: pip install sounddevice")
        sys.exit(1)

    device = args.device
    # Normalize numeric device ids
    try:
        if device is not None:
            device = int(device)
    except ValueError:
        pass
    extra_settings = None
    if args.loopback:
        try:
            extra_settings = sd.WasapiSettings(loopback=True)  # pylint: disable=unexpected-keyword-arg
        except Exception:
            extra_settings = None

        def resolve_output_dev(dev_arg):
            if dev_arg is not None:
                try:
                    return int(dev_arg)
                except (TypeError, ValueError):
                    return dev_arg  # name string
            # try default output from sounddevice tuple
            try:
                out_idx = sd.default.device[1]
            except Exception:
                out_idx = None
            if out_idx is None or out_idx == -1:
                # fallback to an arbitrary output device
                try:
                    out_idx = sd.query_devices(kind="output")["index"]
                except Exception:
                    out_idx = None
            if out_idx is None or out_idx == -1:
                raise ValueError(
                    "Aucun peripherique de sortie detecte pour le loopback. "
                    "Precisez --device <id_sortie> d apres --list-devices."
                )
            return out_idx

        out_dev = resolve_output_dev(device)
        info = sd.query_devices(out_dev, "output")
        out_ch = info.get("max_output_channels", 0) if isinstance(info, dict) else 0
        channels = out_ch if out_ch and out_ch > 0 else 2
        # For WASAPI loopback, pass the output device id directly
        device = out_dev
    else:
        # Pick a sensible number of input channels (prefer 2 if available)
        try:
            info = sd.query_devices(device, "input")
            in_ch = info.get("max_input_channels", 0) if isinstance(info, dict) else 0
        except Exception:
            in_ch = 0
        channels = 2 if in_ch >= 2 else 1

    sample_rate = args.rate
    blocksize = args.blocksize

    # Calibration for noise threshold
    noise_levels: List[float] = []

    # Try opening the stream with a set of candidate channel counts to avoid
    # driver-specific "Invalid number of channels" errors.
    channel_candidates: List[int] = []
    if args.loopback:
        # Prefer output channel count, then input, then common fallbacks.
        channel_candidates.extend([channels])
        channel_candidates.extend([2, 1])
    else:
        channel_candidates.extend([channels, 2, 1])

    stream = None
    last_err = None
    for ch in channel_candidates:
        if ch is None or ch <= 0:
            continue
        try:
            stream = sd.InputStream(
                samplerate=sample_rate,
                blocksize=blocksize,
                device=device,
                channels=ch,
                dtype="float32",
                extra_settings=extra_settings,
            )
            channels = ch
            break
        except Exception as exc:  # keep trying fallbacks
            last_err = exc
            stream = None
            continue

    if stream is None:
        raise last_err if last_err else RuntimeError(
            "Impossible d'ouvrir le flux audio. Verifiez le peripherique et les canaux."
        )

    with stream:
        # Use the actual samplerate negotiated by PortAudio (can differ from requested)
        sample_rate = int(stream.samplerate)
        print(
            f"Capture ouverte sur device={device} channels={channels} rate={sample_rate}"
        )
        quit_event = threading.Event()
        quit_key = getattr(args, "quit_key", None) or DEFAULT_QUIT_KEY

        if quit_key:
            print(f"Appuie sur '{quit_key}' pour quitter proprement (console active).")

        def _watch_quit():  # pragma: no cover - interaction utilisateur
            if msvcrt:
                while not quit_event.is_set():
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        if ch and ch.lower() == quit_key.lower():
                            quit_event.set()
                            try:
                                stream.stop()
                            except Exception:
                                pass
                            break
                    time.sleep(0.05)
            else:
                # Fallback : lire stdin (taper la touche + Entrée)
                try:
                    while not quit_event.is_set():
                        line = sys.stdin.readline()
                        if not line:
                            time.sleep(0.1)
                            continue
                        if line.strip().lower().startswith(quit_key.lower()):
                            quit_event.set()
                            try:
                                stream.stop()
                            except Exception:
                                pass
                            break
                except Exception:
                    pass

        watcher = threading.Thread(target=_watch_quit, daemon=True)
        watcher.start()
        record_writer = None
        if decoder.debug:
            target_record = record_path or "debug_capture.wav"
            try:
                record_writer = wave.open(target_record, "wb")
                record_writer.setnchannels(channels if channels else 1)
                record_writer.setsampwidth(2)  # int16
                record_writer.setframerate(sample_rate)
                print(f"Enregistrement debug vers {target_record}")
            except Exception as exc:
                print(f"⚠️  Impossible d'ouvrir {target_record} pour enregistrement: {exc}")
                record_writer = None
        calibrate_blocks = int(
            (args.calibration or decoder.cfg.calibration_seconds)
            * sample_rate
            / blocksize
        )
        try:
            for _ in range(max(calibrate_blocks, 1)):
                data, _ = stream.read(blocksize)
                if data.ndim > 1:
                    data_mono = data.mean(axis=1)
                else:
                    data_mono = data
                level = measure_level(data_mono, sample_rate, decoder.cfg.target_freq)
                noise_levels.append(level)
                if record_writer is not None:
                    record_writer.writeframes(
                        np.clip(data * 32767, -32768, 32767).astype(np.int16).tobytes()
                    )
        except sd.PortAudioError as exc:
            if "Stream is stopped" not in str(exc):
                raise
            quit_event.set()

        decoder.set_threshold(noise_levels, args.threshold)
        print(f"Seuil RMS: {decoder.rms_threshold:.4f}")
        print("Decodage en cours... Ctrl+C pour arreter.\n")

        try:
            while not quit_event.is_set():
                try:
                    data, _ = stream.read(blocksize)
                except sd.PortAudioError as exc:
                    # Si le flux est arreté (abort) à cause de la quit-key, sortir proprement.
                    if "Stream is stopped" in str(exc):
                        quit_event.set()
                        break
                    raise
                if data.ndim > 1:
                    data_mono = data.mean(axis=1)
                else:
                    data_mono = data
                decoder.process_block(data_mono, sample_rate)
                if record_writer is not None:
                    record_writer.writeframes(
                        np.clip(data * 32767, -32768, 32767)
                        .astype(np.int16)
                        .tobytes()
                    )
        except KeyboardInterrupt:
            print("\nArret demande par l utilisateur.")
        finally:
            quit_event.set()
            try:
                stream.stop()
            except Exception:
                pass
            decoder.finalize()
            if record_writer is not None:
                record_writer.close()


def decode_file(args, decoder: MorseDecoder):
    """Décode un fichier audio déjà chargé."""
    # First pass: load blocks and estimate threshold automatically if none provided.
    blocks = []
    sample_rates = []
    for block, sample_rate in read_audio_file(
        args.file, args.blocksize, target_rate=args.target_rate
    ):
        blocks.append(block)
        sample_rates.append(sample_rate)

    if not blocks:
        print("Fichier audio vide ou illisible.")
        return

    # Ensure consistent sample rate
    sample_rate = sample_rates[0]
    if any(sr != sample_rate for sr in sample_rates):
        print("⚠️  Sample rates varies in file; using first value.")

    rms_levels = [measure_level(b, sample_rate, decoder.cfg.target_freq) for b in blocks]
    if args.threshold is None:
        noise_p20 = float(np.percentile(rms_levels, 20))
        signal_p95 = float(np.percentile(rms_levels, 95))
        auto = noise_p20 + (signal_p95 - noise_p20) * 0.35
        auto = max(auto, noise_p20 * 1.5, decoder.cfg.min_rms_threshold)
        auto = min(auto, signal_p95 * 0.9) if signal_p95 > 0 else auto
        decoder.set_threshold(rms_levels, auto)
        print(
            f"Seuil RMS (offline auto): {decoder.rms_threshold:.4f} "
            f"(p20={noise_p20:.4f}, p95={signal_p95:.4f})"
        )
    else:
        decoder.set_threshold(rms_levels, args.threshold)
        print(f"Seuil RMS (offline fixe): {decoder.rms_threshold:.4f}")

    for block in blocks:
        decoder.process_block(block, sample_rate)
    decoder.finalize()


def merge_config_with_args(args: argparse.Namespace) -> Tuple[DecoderConfig, Dict[str, Any]]:
    """Fusionne valeurs par défaut, YAML et CLI (CLI prioritaire)."""
    raw_cfg = load_yaml_config([args.config] if args.config else DEFAULT_CONFIG_PATHS)
    cfg_dict = validate_decoder_config(raw_cfg)

    def pick(name: str, default_key: Optional[str] = None):
        val = getattr(args, name)
        if val is not None:
            return val
        if default_key:
            return cfg_dict.get(default_key)
        return cfg_dict.get(name)

    unit_ms = pick("unit", "unit_ms")
    if args.wpm:
        unit_ms = 1200.0 / args.wpm

    decoder_cfg = DecoderConfig(
        unit_ms=unit_ms,
        dash_units=pick("dash_units", "dash_units"),
        letter_gap_units=pick("letter_gap", "letter_gap_units"),
        word_gap_units=pick("word_gap", "word_gap_units"),
        min_rms_threshold=cfg_dict["min_rms_threshold"]
        if "min_rms_threshold" in cfg_dict
        else DecoderConfig.min_rms_threshold,
        calibration_seconds=cfg_dict.get("calibration_seconds", DecoderConfig.calibration_seconds),
        target_freq=pick("freq", "freq"),
    )

    resolved = {
        "output_dir": cfg_dict["output_dir"],
        "debug": bool(args.debug or cfg_dict["debug"]),
        "rate": pick("rate", "rate"),
        "blocksize": int(pick("blocksize", "blocksize")),
        "threshold": cfg_dict["threshold"] if args.threshold is None else args.threshold,
        "word_sep": pick("word_sep", "word_sep") or " ",
        "target_rate": cfg_dict["target_rate"],
        "quit_key": args.quit_key or cfg_dict.get("quit_key", DEFAULT_QUIT_KEY),
        "device": pick("device", "device") or cfg_dict.get("device"),
    }

    os.makedirs(resolved["output_dir"], exist_ok=True)
    return decoder_cfg, resolved

def build_parser():
    """Construit le parser CLI."""
    p = argparse.ArgumentParser(
        description="Decode le Morse a partir du son (loopback ou micro)."
    )
    p.add_argument("--config", type=str, help="Chemin vers un fichier YAML de configuration")
    p.add_argument(
        "--quit-key",
        type=str,
        help="Touche clavier pour quitter proprement en live (ex: q).",
    )
    p.add_argument("--unit", type=float, help="Duree d un point (ms)")
    p.add_argument(
        "--wpm",
        type=float,
        help="Vitesse en mots par minute (PARIS). Si definie, unit = 1200 / wpm.",
    )
    p.add_argument("--rate", type=int, help="Frequence d echantillonnage")
    p.add_argument(
        "--blocksize", type=int, help="Taille de bloc en echantillons"
    )
    p.add_argument(
        "--dash-units",
        type=float,
        help="Seuil (en unites) pour distinguer tiret de point (defaut 2.0).",
    )
    p.add_argument(
        "--letter-gap",
        type=float,
        help="Seuil (en unites) de fin de lettre.",
    )
    p.add_argument(
        "--word-gap",
        type=float,
        help="Seuil (en unites) de fin de mot.",
    )
    p.add_argument(
        "--word-sep",
        type=str,
        help="Caractere a afficher entre les mots (defaut: espace). Ex: '/'",
    )
    p.add_argument(
        "--freq",
        type=float,
        help="Frequence cible du bip (Goertzel).",
    )
    p.add_argument("--device", type=str, help="Nom ou index du peripherique audio")
    p.add_argument(
        "--loopback",
        action="store_true",
        help="Sous Windows (WASAPI), capture la sortie systeme (haut-parleurs).",
    )
    p.add_argument(
        "--file", type=str, help="Chemin vers un fichier WAV a decoder (offline)."
    )
    p.add_argument(
        "--threshold",
        type=float,
        help="Seuil RMS manuel (0-1). Sinon calcule automatiquement.",
    )
    p.add_argument(
        "--calibration",
        type=float,
        help="Duree (s) de calibration du bruit avant decodage live.",
    )
    p.add_argument(
        "--list-devices",
        action="store_true",
        help="Affiche les peripheriques disponibles et quitte.",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Affiche les evenements de transitions (premiers 200) pour tuning.",
    )
    return p


def main():
    """Point d'entrée CLI pour le décodage Morse."""
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(signal, "SIGQUIT"):
        signal.signal(signal.SIGQUIT, lambda *_: sys.exit(0))

    if args.list_devices:
        list_devices()
        return

    decoder_cfg, resolved = merge_config_with_args(args)
    args.rate = resolved["rate"]
    args.blocksize = resolved["blocksize"]
    args.threshold = resolved["threshold"]
    args.word_sep = resolved["word_sep"]
    args.debug = resolved["debug"]
    args.target_rate = resolved["target_rate"]
    args.device = resolved["device"]
    transcript: List[str] = []

    def emit(char: str):
        transcript.append(char)
        print(char, end="", flush=True)

    decoder = MorseDecoder(decoder_cfg, emit, debug=args.debug, space_char=args.word_sep)

    if args.file:
        decode_file(args, decoder)
    else:
        record_path = None
        if args.debug and resolved["output_dir"]:
            record_path = os.path.join(resolved["output_dir"], "debug_capture.wav")
        capture_stream(args, decoder, record_path=record_path)

    print("\n\nTexte decode:\n" + "".join(transcript))


if __name__ == "__main__":
    main()
