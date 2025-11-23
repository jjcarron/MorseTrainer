import numpy as np

from morsetrainer.morse_decoder import DecoderConfig, MorseDecoder, measure_level


def test_measure_level_detects_sine_wave():
    sample_rate = 96000
    freq = 600
    t = np.arange(sample_rate // 10)
    block = np.sin(2 * np.pi * freq * t / sample_rate)
    level = measure_level(block, sample_rate, freq)
    assert level > 0.05


def test_decoder_parses_simple_k():
    cfg = DecoderConfig(unit_ms=60, dash_units=2, letter_gap_units=4.5, word_gap_units=12)
    output = []
    decoder = MorseDecoder(cfg, output.append)
    decoder.rms_threshold = 0.5

    sample_rate = 1000

    def push(value: float, ms: float) -> None:
        samples = int(sample_rate * (ms / 1000.0))
        decoder.process_block(np.full(samples, value, dtype=float), sample_rate)

    # K = -.- with short gaps then letter gap
    push(1.0, 180)
    push(0.0, 60)
    push(1.0, 60)
    push(0.0, 60)
    push(1.0, 180)
    push(0.0, 300)
    decoder.finalize()

    assert "".join(output).strip() == "K"
