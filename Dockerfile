# LA BUSE — image pilote minimale (API + CLI). Aucun secret dans l'image :
# tout passe par les variables d'environnement (cf. docker-compose.yml / .env).
# PROPRETE-FIX-0 — 3.12 : aligné sur le VPS (deploy/scripts/deploy_app.sh = python3.12) et sur
# l'environnement testé (le verrou requirements.lock épingle numpy 2.5.2, qui exige Python ≥ 3.12).
FROM python:3.12-slim

# postgresql-client : labuse backup-db / restore-db (pg_dump, pg_restore) depuis le conteneur.
# curl : healthcheck Docker sur /healthz.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/labuse

# Dépendances d'abord (cache de build), puis le code.
# PROPRETE-FIX-0 — installe depuis le VERROU (versions testées, CVE corrigées) puis le paquet
# lui-même sans re-résoudre (--no-deps : le closure cœur vient déjà de requirements.lock).
COPY pyproject.toml README.md requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps .

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
