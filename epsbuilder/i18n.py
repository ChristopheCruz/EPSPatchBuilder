"""Langue de l'application : francais (textes d'origine) ou anglais (table de traduction).

La langue est choisie, dans l'ordre : par la variable d'environnement EPSBUILDER_LANG, par le
choix enregistre depuis le menu « Langue », puis d'apres la langue du systeme.
"""
from __future__ import annotations

import os
import sys

LANGUAGES = {"fr": "Français", "en": "English"}


def _config_path() -> str:
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "EPSBuilder", "language.txt")


def _system_language() -> str:
    try:
        if sys.platform == "win32":
            import ctypes
            return "fr" if (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x0C else "en"
        for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
            value = os.environ.get(name)
            if value:
                return "fr" if value.lower().startswith("fr") else "en"
    except Exception:
        pass
    return "en"


def _initial_language() -> str:
    forced = (os.environ.get("EPSBUILDER_LANG") or "").lower()[:2]
    if forced in LANGUAGES:
        return forced
    try:
        with open(_config_path(), encoding="utf-8") as f:
            saved = f.read().strip().lower()[:2]
        if saved in LANGUAGES:
            return saved
    except OSError:
        pass
    return _system_language()


LANG = _initial_language()


def set_language(lang: str, save: bool = True) -> None:
    """Change la langue. Les textes deja affiches ne changent qu'au prochain lancement."""
    global LANG
    if lang not in LANGUAGES:
        raise ValueError(lang)
    LANG = lang
    if save:
        try:
            os.makedirs(os.path.dirname(_config_path()), exist_ok=True)
            with open(_config_path(), "w", encoding="utf-8") as f:
                f.write(lang)
        except OSError:
            pass


def T(text: str) -> str:
    """Texte dans la langue courante (le francais sert de cle)."""
    if LANG == "en":
        from .translations import EN
        return EN.get(text, text)
    return text


def number(text: str) -> str:
    """Separateur decimal : virgule en francais, point en anglais."""
    return text.replace(".", ",") if LANG == "fr" else text
