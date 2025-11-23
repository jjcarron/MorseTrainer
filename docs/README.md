# MorseTrainer

Structure réorganisée :
- `morsetrainer/` : sources Python (`morse_trainer.py`, `morse_decoder.py`, `capture_test.py`).
- `tests/` : tests Pytest.
- `docs/` : documentation et notes.

## Utilisation
- Entraînement Koch : `python -m morsetrainer.morse_trainer --tests 1`
- Décodage fichier : `python -m morsetrainer.morse_decoder --file chemin.wav`
- Décodage live (ex VB-Cable) : `python -m morsetrainer.morse_decoder --device <id_entree> --rate 96000 --blocksize 2048`
- Capture brute pour debug : `python -m morsetrainer.capture_debug --device <id> --rate 96000 --duration 5`

## Tests
```
pytest
```
