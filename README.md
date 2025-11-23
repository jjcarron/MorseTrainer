# MorseTrainer
Outils d'apprentissage et de décodage du Morse (méthode Koch).

## Structure
- `morsetrainer/` : sources (`morse_trainer.py`, `morse_decoder.py`, `capture_debug.py`).
- `config/` : fichiers YAML commentés (`morse_trainer.yaml`, `morse_decoder.yaml`).
- `tests/` : tests Pytest.
- `docs/` : documentation détaillée.
- `data/` : non versionné (captures, fichiers audio persos).

## Utilisation rapide
- Entraîneur Koch :  
  `python -m morsetrainer.morse_trainer --tests 1`  
  (les options CLI priment sur `config/morse_trainer.yaml`)
- Décodage d'un fichier :  
  `python -m morsetrainer.morse_decoder --file data/lcwo-001.mp3`
- Décodage live (ex. VB-Cable) :  
  `python -m morsetrainer.morse_decoder --device 31 --rate 44100 --blocksize 1024 --debug`
- Capture brute pour debug :  
  `python -m morsetrainer.capture_debug --device 31 --rate 44100 --duration 5`

## Config et tests
- Configurer via `config/*.yaml` (voir commentaires). CLI > YAML > valeurs par défaut.
- Tests : `pytest`
