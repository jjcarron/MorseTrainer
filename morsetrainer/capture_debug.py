"""Outil de capture audio simple pour générer un fichier WAV debug."""

import argparse
import threading
import time
import wave
import numpy as np
import sounddevice as sd  # pylint: disable=import-error

try:  # pragma: no cover - Windows only
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None


def main():
    """Capture une entrée audio et l'enregistre dans un fichier WAV."""
    parser = argparse.ArgumentParser(
        description="Capture une entree audio et sauvegarde en WAV (debug)."
    )
    parser.add_argument(
        "--device", type=str, help="Nom ou index du peripherique input"
    )
    parser.add_argument(
        "--rate", type=int, default=48000, help="Frequence d echantillonnage"
    )
    parser.add_argument(
        "--blocksize", type=int, default=4096, help="Taille de bloc en echantillons"
    )
    parser.add_argument(
        "--duration", type=float, default=5.0, help="Duree de capture en secondes"
    )
    parser.add_argument(
        "--outfile",
        type=str,
        default="capture_test.wav",
        help="Fichier WAV de sortie",
    )
    parser.add_argument(
        "--quit-key",
        type=str,
        default="q",
        help="Touche clavier pour arrêter la capture (par défaut: q).",
    )
    args = parser.parse_args()

    # Normalize device id
    device = args.device
    try:
        if device is not None:
            device = int(device)
    except ValueError:
        pass

    # Query channels
    channels = 1
    try:
        info = sd.query_devices(device, "input")
        in_ch = info.get("max_input_channels", 0) if isinstance(info, dict) else 0
        channels = 2 if in_ch >= 2 else 1
    except Exception:  # pylint: disable=broad-exception-caught
        channels = 1

    print(f"Ouverture device={device} channels={channels} rate={args.rate}")

    frames_needed = int(args.duration * args.rate)
    captured = []

    quit_event = threading.Event()

    with sd.InputStream(
        samplerate=args.rate,
        blocksize=args.blocksize,
        device=device,
        channels=channels,
        dtype="float32",
    ) as stream:
        print(f"Taux reel negotiation: {stream.samplerate}")
        print(f"Appuie sur '{args.quit_key}' (console) ou Ctrl+C pour arrêter la capture.")

        def _watch_quit():  # pragma: no cover - interaction utilisateur
            if msvcrt:
                while not quit_event.is_set():
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        if ch and ch.lower() == args.quit_key.lower():
                            quit_event.set()
                            try:
                                stream.stop()
                            except Exception:
                                pass
                            break
                    time.sleep(0.05)
            else:
                try:
                    while not quit_event.is_set():
                        line = sys.stdin.readline()
                        if not line:
                            time.sleep(0.1)
                            continue
                        if line.strip().lower().startswith(args.quit_key.lower()):
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
        frames_captured = 0
        try:
            while frames_captured < frames_needed and not quit_event.is_set():
                try:
                    data, _ = stream.read(args.blocksize)
                except sd.PortAudioError as exc:
                    if "Stream is stopped" in str(exc):
                        quit_event.set()
                        break
                    raise
                captured.append(data.copy())
                frames_captured += data.shape[0]
        except KeyboardInterrupt:
            print("\nArrêt demandé (Ctrl+C).")
        finally:
            quit_event.set()
            try:
                stream.stop()
            except Exception:
                pass

    if not captured:
        print("Aucune donnée capturée.")
        return

    audio = np.concatenate(captured, axis=0)
    # Convert to mono if needed
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Normalize to int16
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

    with wave.open(args.outfile, "wb") as wf:
        wf.setnchannels(1)  # pylint: disable=no-member
        wf.setsampwidth(2)  # pylint: disable=no-member
        wf.setframerate(args.rate)  # pylint: disable=no-member
        wf.writeframes(audio_int16.tobytes())  # pylint: disable=no-member

    print(f"Capture terminee -> {args.outfile} (rate={args.rate})")


if __name__ == "__main__":
    main()
