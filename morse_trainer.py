import time
import random
import pyttsx3
import winsound  # sous Windows ; sinon remplacer par simpleaudio

# Configuration audio
FREQ = 600   # fréquence du ton CW en Hz
DOT = 100    # durée du point en ms
DASH = DOT * 3
SPACE = DOT  # espace entre éléments

# Dictionnaire Morse
MORSE = {
    "A": ".-",
    "N": "-."
}

# Synthèse vocale
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def play_morse(symbols):
    for s in symbols:
        if s == ".":
            winsound.Beep(FREQ, DOT)
        elif s == "-":
            winsound.Beep(FREQ, DASH)
        time.sleep(SPACE/1000.0)
    time.sleep(0.5)  # pause entre lettres

def train_letter(letter, repeat=5):
    # prononce la lettre
    speak(letter)
    # joue le son plusieurs fois
    for _ in range(repeat):
        play_morse(MORSE[letter])

def test_sequence(letters, length=6):
    seq = [random.choice(letters) for _ in range(length)]
    print("Séquence test (solution) :", " ".join(seq))
    for l in seq:
        play_morse(MORSE[l])
        time.sleep(0.5)

# --- Programme principal ---
if __name__ == "__main__":
    letters = ["A", "N"]

    # Présentation
    for l in letters:
        train_letter(l)

    # Séquence d’entraînement
    sequence = ["A", "A", "N", "A", "N", "N", "A"]
    for l in sequence:
        play_morse(MORSE[l])

    # Séquence de test
    test_sequence(letters)
import time
import random
import pyttsx3
import winsound  # sous Windows ; sinon remplacer par simpleaudio

# Configuration audio
FREQ = 600   # fréquence du ton CW en Hz
DOT = 100    # durée du point en ms
DASH = DOT * 3
SPACE = DOT  # espace entre éléments

# Dictionnaire Morse
MORSE = {
    "A": ".-",
    "N": "-."
}

# Synthèse vocale
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def play_morse(symbols):
    for s in symbols:
        if s == ".":
            winsound.Beep(FREQ, DOT)
        elif s == "-":
            winsound.Beep(FREQ, DASH)
        time.sleep(SPACE/1000.0)
    time.sleep(0.5)  # pause entre lettres

def train_letter(letter, repeat=5):
    # prononce la lettre
    speak(letter)
    # joue le son plusieurs fois
    for _ in range(repeat):
        play_morse(MORSE[letter])

def test_sequence(letters, length=6):
    seq = [random.choice(letters) for _ in range(length)]
    print("Séquence test (solution) :", " ".join(seq))
    for l in seq:
        play_morse(MORSE[l])
        time.sleep(0.5)

# --- Programme principal ---
if __name__ == "__main__":
    letters = ["A", "N"]

    # Présentation
    for l in letters:
        train_letter(l)

    # Séquence d’entraînement
    sequence = ["A", "A", "N", "A", "N", "N", "A"]
    for l in sequence:
        play_morse(MORSE[l])

    # Séquence de test
    test_sequence(letters)

