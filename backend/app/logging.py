import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure le logging pour toute l'app — format simple, sortie stderr."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,  # Écrase la config par défaut d'uvicorn
    )
    # Réduit le bruit des libs tierces
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
