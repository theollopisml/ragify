FROM python:3.12-slim

# Installer uv (gestionnaire de paquets Python ultra-rapide)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# On copie d'abord les fichiers de dépendances seuls
# Docker cache cette couche : si les dépendances ne changent pas, pas de réinstallation
COPY pyproject.toml uv.lock ./

# --frozen : installe exactement ce qui est dans le lockfile, sans le mettre à jour
# --no-dev : pas de dépendances de développement en production
RUN uv sync --frozen --no-dev

COPY . .

# --reload : uvicorn redémarre quand le code change (dev uniquement)
# --host 0.0.0.0 : écoute sur toutes les interfaces (nécessaire dans Docker)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
