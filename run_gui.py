"""Point d'entree de l'application graphique (utilise par PyInstaller)."""
import sys

from epsbuilder.gui import main

if __name__ == "__main__":
    sys.exit(main())
