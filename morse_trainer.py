import os
import time
import random
import pyttsx3
import winsound
import argparse
import sys

# Configuration audio
FREQ = 600
DOT = 100
DASH = DOT * 3
SPACE = DOT

# Dictionnaire Morse (alphabet, chiffres, ponctuation)
MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "(": "-.--.",
    ")": "-.--.-",
    "&": ".-...",
    ":": "---...",
    ";": "-.-.-.",
    "=": "-...-",
    "+": ".-.-.",
    "-": "-....-",
    "_": "..--.-",
    '"': ".-..-.",
    "$": "...-..-",
    "@": ".--.-.",
}

# Séquence Koch (au début K et M sont apprises en premier ensemble)
KOCH_SEQUENCE = [
    "K",
    "M",
    "R",
    "S",
    "U",
    "A",
    "P",
    "T",
    "L",
    "O",
    "N",
    "E",
    "I",
    "D",
    "C",
    "H",
    "F",
    "Y",
    "V",
    "G",
    "5",
    "Q",
    "9",
    "Z",
    "3",
    "J",
    "4",
    "B",
    "8",
    "7",
    ".",
    ",",
    "?",
    "/",
    "0",
    "6",
    "1",
    "2",
    ":",
    ";",
    "=",
    "+",
    "-",
    "_",
    '"',
    "@",
]

LAST_FILE = "last_known_letter.txt"


def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def play_morse(symbols):
    for s in symbols:
        if s == ".":
            winsound.Beep(FREQ, DOT)
        elif s == "-":
            winsound.Beep(FREQ, DASH)
        time.sleep(SPACE / 1000.0)
    time.sleep(0.5)


def train_letter(letter, repeat=5):
    speak("Début de la répétition de la lettre " + letter)
    for _ in range(repeat):
        speak(letter)
        time.sleep(0.3)
        play_morse(MORSE[letter])
        time.sleep(0.5)


def test_sequence(letters, length=10):
    seq = [random.choice(letters) for _ in range(length)]
    print("\n--- Séquence test ---")
    speak("Début du test")
    time.sleep(0.5)
    for l in seq:
        play_morse(MORSE[l])
        time.sleep(0.5)
    return seq


def save_session(letters, seq, user_input, success_rate):
    with open("sessions_morse.txt", "a", encoding="utf-8") as f:
        f.write("Lettres connues: " + "".join(letters) + "\n")
        f.write("Séquence émise: " + "".join(seq) + "\n")
        f.write("Réponse donnée: " + user_input + "\n")
        f.write(f"Taux de réussite: {success_rate:.2f}\n")
        f.write("-" * 40 + "\n")


def get_letters_apprises(last_known=None):
    if last_known is None:
        # Cas 1 : rien donné → commencer avec K et M
        learned = ["K", "M"]
        next_letter = None  # pas de nouvelle lettre unique, on entraîne les deux
        print("Début de l’apprentissage : lettres K et M")
        return learned, next_letter

    if last_known not in KOCH_SEQUENCE:
        print(f"Signe {last_known} non reconnu, utilisation de K et M par défaut.")
        return ["K", "M"], None

    idx = KOCH_SEQUENCE.index(last_known)
    learned = KOCH_SEQUENCE[: idx + 1]

    # Cas 2 : si K est donné → ajouter M
    if last_known == "K":
        learned.append("M")
        next_letter = "M"
        print("Nouvelle lettre à apprendre : M")
    elif idx + 1 < len(KOCH_SEQUENCE):
        next_letter = KOCH_SEQUENCE[idx + 1]
        learned.append(next_letter)
        print(f"Nouvelle lettre à apprendre : {next_letter}")
    else:
        next_letter = None
        print("Toutes les lettres de la séquence Koch sont déjà apprises.")

    return learned, next_letter


def main():
    parser = argparse.ArgumentParser(description="Entraînement Morse méthode Koch")
    parser.add_argument(
        "--last", type=str, help="Dernière lettre apprise (ex: K, M, R...)"
    )
    parser.add_argument(
        "--tests", type=int, default=3, help="Nombre de séquences de test"
    )
    args = parser.parse_args()

    # Priorité : paramètre > fichier > défaut K,M
    if args.last:
        last_known = args.last.upper()
    elif os.path.exists(LAST_FILE):
        with open(LAST_FILE, "r", encoding="utf-8") as f:
            last_known = f.read().strip().upper()
        print(f"Lecture de la dernière lettre réussie depuis {LAST_FILE}: {last_known}")
    else:
        last_known = None

    letters, new_letter = get_letters_apprises(last_known)
    print("Lettres connues pour cette session:", "".join(letters))

    # Entraînement
    if last_known is None:
        for l in letters:  # K et M ensemble
            train_letter(l)
    elif new_letter:
        train_letter(new_letter)

    # Tests
    for test_num in range(1, args.tests + 1):
        print(f"\n=== Test {test_num}/{args.tests} ===")

        # Commentaire vocal avant le test
        speak(f"Début du test numéro {test_num}")
        time.sleep(0.5)  # petite pause pour éviter de couper le premier bip

        while True:
            seq = test_sequence(letters, length=10)

            user_input = (
                input("Tape la séquence entendue (ex: KMKM...): ").strip().upper()
            )
            user_seq = list(user_input)

            correct = sum(
                1 for i, l in enumerate(seq) if i < len(user_seq) and user_seq[i] == l
            )
            success_rate = correct / len(seq)

            print("\nRésultat du test")
            print("Séquence émise :", "".join(seq))
            print("Séquence tapée :", "".join(user_seq))
            print(f"Taux de réussite : {correct}/{len(seq)} → {success_rate*100:.1f}%")

            save_session(letters, seq, "".join(user_seq), success_rate)

        if success_rate >= 0.9:
            print("✅ Bravo, tu as atteint 90%. Tu peux passer à la lettre suivante.")
            # Sauvegarde de la dernière lettre réussie
            with open(LAST_FILE, "w", encoding="utf-8") as f:
                f.write(letters[-1])
            break
        else:
            print("❌ Entraîne-toi encore avant de passer à la suivante.")
            retry = input("Veux-tu refaire ce test ? (O/N): ").strip().upper()
            if retry != "O":
                break


if __name__ == "__main__":
    main()
