import time
import random
import pyttsx3
import winsound
import sys

# Configuration audio
FREQ = 600   # fréquence du ton CW en Hz
DOT = 100    # durée du point en ms
DASH = DOT * 3
SPACE = DOT  # espace entre éléments

# Dictionnaire Morse
MORSE = {
    "A": ".-",
    "N": "-.",
    "K": "-.-",
    "M": "--",
    "O": "---",
    "E": ".",
    "T": "-"
    # tu peux compléter au fur et à mesure
}

# Synthèse vocale doit être créé pour chaque appel pour éviter les conflits
#engine = pyttsx3.init()

def speak(text):
    engine = pyttsx3.init()   # réinitialisation à chaque appel
    engine.say(text)
    engine.runAndWait()
    engine.stop()

def play_morse(symbols):
    for s in symbols:
        if s == ".":
            winsound.Beep(FREQ, DOT)
        elif s == "-":
            winsound.Beep(FREQ, DASH)
        time.sleep(SPACE/1000.0)
    time.sleep(0.5)  # pause entre lettres

def train_letter(letter, repeat=5):
    for _ in range(repeat):
        speak(letter)
        time.sleep(0.3)  # pause pour séparer voix et son
        play_morse(MORSE[letter])
        time.sleep(0.5)

def test_sequence(letters, length=6):
    seq = [random.choice(letters) for _ in range(length)]
    print("\n--- Séquence test ---")
    for l in seq:
        play_morse(MORSE[l])
        time.sleep(0.5)
    return seq

def save_session(letters, seq, user_input, success_rate):
    with open("sessions_morse.txt", "a", encoding="utf-8") as f:
        f.write("Lettres connues: " + " ".join(letters) + "\n")
        f.write("Séquence émise: " + "".join(seq) + "\n")
        f.write("Réponse donnée: " + user_input + "\n")
        f.write(f"Taux de réussite: {success_rate:.2f}\n")
        f.write("-"*40 + "\n")

def main(letters, nb_tests=5):
    try:
        # Présentation
        for l in letters:
            train_letter(l)

        # Boucle de tests
        for test_num in range(1, nb_tests+1):
            print(f"\n=== Test {test_num}/{nb_tests} ===")
            seq = test_sequence(letters)

            # Attente de la réponse utilisateur
            user_input = input("Tape la séquence entendue (ex: ANANA): ").strip().upper()
            user_seq = list(user_input)

            # Calcul du taux de réussite
            correct = sum(1 for i, l in enumerate(seq) if i < len(user_seq) and user_seq[i] == l)
            success_rate = correct / len(seq)

            # --- Affichage clair ---
            print("\nRésultat du test")
            print("Séquence émise :", "".join(seq))
            print("Séquence tapée :", "".join(user_seq))
            print(f"Taux de réussite : {correct}/{len(seq)} → {success_rate*100:.1f}%")

            # Sauvegarde
            save_session(letters, seq, "".join(user_seq), success_rate)

    except KeyboardInterrupt:
        print("\nArrêt demandé (Ctrl+Q). Fin du programme.")
        sys.exit(0)

if __name__ == "__main__":
    # Exemple: état d’avancement (lettres connues)
    letters_apprises = ["A", "N"]
    main(letters_apprises, nb_tests=5)

