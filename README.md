# MorseTrainer
Outils d'apprentissage et de décodage du Morse (méthode Koch).

## Structure
- `morsetrainer/` : sources (`morse_trainer.py`, `morse_decoder.py`, `capture_test.py`).
- `tests/` : tests Pytest.
- `docs/` : documentation.
- `data/` : non versionné (captures, fichiers audio persos).

## Utilisation
- Entraînement Koch :  
  `python -m morsetrainer.morse_trainer --tests 1`
- Décodage d'un fichier :  
  `python -m morsetrainer.morse_decoder --file chemin.wav`
- Décodage live (VB-Cable) :  
  `python -m morsetrainer.morse_decoder --device "CABLE Output (VB-Audio Virtual Cable)" --rate 96000 --blocksize 2048`
- Capture brute pour debug :  
  `python -m morsetrainer.capture_debug --device 31 --rate 96000 --duration 5`

## Tests
```
pytest
```
