"""Tests unitaires pour l'entraîneur Morse."""
from morsetrainer import morse_trainer as mt


def test_get_letters_default_starts_with_km():
    """Par défaut, on commence avec K et M sans nouvelle lettre."""
    learned, next_letter = mt.get_letters_apprises()
    assert learned == ["K", "M"]
    assert next_letter is None


def test_get_letters_progression_and_invalid():
    """Progression Koch et gestion d'un caractère invalide."""
    learned, next_letter = mt.get_letters_apprises("K")
    assert learned[-1] == "M"
    assert next_letter == "M"

    learned, next_letter = mt.get_letters_apprises("R")
    assert learned[-1] == "S"
    assert next_letter == "S"

    learned, next_letter = mt.get_letters_apprises("$")
    assert learned == ["K", "M"]
    assert next_letter is None
