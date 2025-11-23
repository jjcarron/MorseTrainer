# MorseTrainer
Outils d'apprentissage du morse télégraphique

## Capture audio (Windows)
- Lecture de fichiers : `py morse_decoder.py --file tonfichier.mp3` (pydub+ffmpeg requis).
- Capture sortie PC (sans écouter) via VB-CABLE :
  1. Installer VB-CABLE, choisir `CABLE Input` comme sortie audio par défaut.
  2. Lancer le décodeur sur `CABLE Output` (entrée) :  
     `py morse_decoder.py --device "CABLE Output (VB-Audio Virtual Cable)" --rate 96000 --blocksize 2048 --threshold 0.02`
  3. Pour réentendre en même temps, ajouter Voicemeeter ou activer l'écoute du câble vers vos HP.
```
