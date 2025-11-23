"""Outil de capture audio simple pour générer un fichier WAV debug."""

import argparse
import wave
import numpy as np
import sounddevice as sd


def main():
    """Capture une entrée audio et l'enregistre dans un fichier WAV."""
    parser = argparse.ArgumentParser(
        description="Capture une entree audio et sauvegarde en WAV (debug)."
    )
    parser.add_argument("--device", type=str, help="Nom ou index du peripherique input")
    parser.add_argument("--rate", type=int, default=48000, help="Frequence d echantillonnage")
    parser.add_argument("--blocksize", type=int, default=4096, help="Taille de bloc en echantillons")
    parser.add_argument("--duration", type=float, default=5.0, help="Duree de capture en secondes")
    parser.add_argument("--outfile", type=str, default="capture_test.wav", help="Fichier WAV de sortie")
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
    except Exception:
        channels = 1

    print(f"Ouverture device={device} channels={channels} rate={args.rate}")

    frames_needed = int(args.duration * args.rate)
    captured = []

    with sd.InputStream(
        samplerate=args.rate,
        blocksize=args.blocksize,
        device=device,
        channels=channels,
        dtype="float32",
    ) as stream:
        print(f"Taux reel negotiation: {stream.samplerate}")
        frames_captured = 0
        while frames_captured < frames_needed:
            data, _ = stream.read(args.blocksize)
            captured.append(data.copy())
            frames_captured += data.shape[0]

    audio = np.concatenate(captured, axis=0)
    # Convert to mono if needed
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Normalize to int16
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

    with wave.open(args.outfile, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(stream.samplerate))
        wf.writeframes(audio_int16.tobytes())

    print(f"Capture terminee -> {args.outfile} (rate={int(stream.samplerate)})")


if __name__ == "__main__":
    main()
