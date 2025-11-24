# Instructions agent (exemple pour prochains projets)

- **Structure du dépôt** :
  - Sources dans un package dédié (ici `morsetrainer/`).
  - Dossiers `tests/`, `docs/`, `config/`, `data/` (ce dernier ignoré par git).
  - Ajout d'`__init__.py` pour rendre le package importable.

- **Configuration** :
  - Fichiers YAML commentés dans `config/` (ex : `morse_trainer.yaml`, `morse_decoder.yaml`).
  - Les valeurs CLI ont la priorité sur le YAML ; le YAML surcharge les valeurs par défaut du code.
  - Validation des paramètres (positifs, types) ; ignorer silencieusement YAML absent.

- **Qualité/code** :
  - Docstrings sur modules/classes/fonctions.
  - Respect pylint (ou désactivations ciblées), tests Pytest.
  - Paramètres par défaut maintenus via code + YAML.
  - Capture propre (quitter sans stacktrace, gérer Ctrl+C/quit-key).

- **Flux audio (exemple)** :
  - Décodage : Goertzel sur freq cible, seuil auto p20/p95 ou seuil manuel ; timing fixe (unit_ms, dash_units, letter_gap_units, word_gap_units).
  - Live : message quit-key, arrêt propre du stream, enregistrement debug optionnel.
  - Conversion mp3 → wav via ffmpeg avec rééchantillonnage `target_rate`.

- **Tests/CI** :
  - `pytest` doit passer après chaque changement significatif.
  - Décodage de fichiers de référence comparé aux textes attendus.

- **Commandes typiques** :
  - Entraîneur : `python -m <package>.morse_trainer` (options `--tests`, `--length`, `--config`).
  - Décodeur fichier/live : `python -m <package>.morse_decoder --file ...` ou `--device ...` (quitter avec quit-key).
  - Capture debug : `python -m <package>.capture_debug --device ... --quit-key q`.
  - Tests : `pytest`.

- **Git** :
  - Ne pas suivre `data/` ni les fichiers générés (captures, sessions).
  - Commits fréquents avec message clair.
