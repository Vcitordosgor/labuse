# LA BUSE — image pilote minimale (API + CLI). Aucun secret dans l'image :
# tout passe par les variables d'environnement (cf. docker-compose.yml / .env).
FROM python:3.11-slim

# postgresql-client : labuse backup-db / restore-db (pg_dump, pg_restore) depuis le conteneur.
# curl : healthcheck Docker sur /healthz.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/labuse

# Dépendances d'abord (cache de build), puis le code.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Règles & poids (cascade/scoring) — chemin ABSOLU car le paquet est installé en site-packages.
COPY config ./config
ENV LABUSE_CONFIG_DIR=/srv/labuse/config

# Utilisateur non-root (pilote propre).
RUN useradd --create-home --uid 10001 labuse
USER labuse

EXPOSE 8000

# Vivant ≠ prêt : le healthcheck Docker sonde le PROCESS (/healthz) ; l'état des données
# se vérifie avec /readyz et `labuse doctor` (cf. PILOT_SECURITY_DEPLOYMENT.md).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["labuse", "api", "--host", "0.0.0.0", "--port", "8000"]
