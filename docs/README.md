# MorseTrainer

## 1. Objectif du projet
Outils d'apprentissage et de décodage du code Morse (méthode Koch) avec synthèse vocale, génération de bips et décodage audio (fichiers ou capture live).

### 1a. Fonctionnalités et principe
- **Entraîneur** (`morse_trainer.py`) : génère des séquences Koch, annonce les lettres (TTS), émet les bips, enregistre la progression.
- **Décodeur** (`morse_decoder.py`) : décode des fichiers audio (mp3/wav) ou une capture live (micro/loopback/VB-Cable) en texte.
- **Capture brute** (`capture_debug.py`) : enregistre une entrée audio dans un WAV pour diagnostic.

Génération : point = `dot_ms`, tiret = `dot_ms * dash_factor`, espace inter-éléments = `space_ms`. La séquence Koch détermine l'ordre d'introduction des caractères.

### 1b. Technologies
Python 3, `pyttsx3` (TTS), `sounddevice` (capture), `pydub` + `ffmpeg` (mp3), `numpy`, `PyYAML`.

### 1c. Prérequis
- Python 3.9+.
- `ffmpeg` dans le PATH pour lire les mp3 (sinon convertir en wav).
- Périphérique d'entrée disponible pour le live.

### 1d. Paramètres configurables (config YAML)
Chaque fichier YAML est commenté :

**config/morse_trainer.yaml**
- `output_dir` : répertoire des fichiers générés (progression, sessions).
- `debug` : booléen.
- `freq` : fréquence des bips (Hz).
- `dot_ms`, `dash_factor`, `space_ms` : durées (ms).
- `tests`, `length` : nombre et longueur des séquences de test.

**config/morse_decoder.yaml**
- `output_dir` : répertoire pour `debug_capture.wav`.
- `debug` : booléen.
- `unit_ms`, `dash_units`, `letter_gap_units`, `word_gap_units` : cadence et seuils (unités Morse).
- `freq` : fréquence cible (Hz, Goertzel).
- `rate`, `blocksize` : fréquence d'échantillonnage demandée, taille de bloc.
- `target_rate` : fréquence cible pour la conversion ffmpeg.
- `threshold` : seuil RMS manuel (`null` pour auto).
- `word_sep` : séparateur de mots en sortie.

## 2. Installation
```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install pyttsx3 sounddevice pydub numpy PyYAML pytest
# Installer ffmpeg et l'ajouter au PATH
```

## 3. Configuration
- Éditez `config/morse_trainer.yaml` et `config/morse_decoder.yaml` (commentés).
- Les options CLI priment sur le YAML, qui lui-même sur les valeurs par défaut.

## 4. Exécution
- Entraîneur Koch :
  `python -m morsetrainer.morse_trainer`
  (options : `--tests`, `--length`, `--last`, `--config`).
- Décodage fichier :
  `python -m morsetrainer.morse_decoder --file data/lcwo-001.mp3`
- Décodage live (ex. VB-Cable entrée 31) :
  `python -m morsetrainer.morse_decoder --device 31 --rate 44100 --blocksize 1024 --debug`
- Capture brute :
  `python -m morsetrainer.capture_debug --device 31 --rate 44100 --duration 5`

## 5. Tests
```bash
pytest
```
