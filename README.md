# LA BUSE — radar foncier intelligent de La Réunion

> **LA BUSE ne vend pas une carte. LA BUSE vend une lecture foncière complète :
> tout ce qui est public, au même endroit, puis interprété.**

LA BUSE ne garantit jamais la constructibilité, la propriété, la rentabilité ni
la faisabilité juridique. Elle produit une **pré-analyse** à partir de données
publiques et d'hypothèses explicitement signalées comme telles.

---

## L'idée en une phrase

Un **seul moteur** d'évaluation parcellaire — une **cascade d'exclusion** — et
trois manières de le pointer :

| Offre | Le moteur tourne sur… | Produit |
|-------|------------------------|---------|
| **A — Qualification** | une parcelle fournie | fiche de pré-qualification |
| **B — + Découverte** | toutes les parcelles d'une commune | survivantes classées (le radar) |
| **C — + Veille** | re-tourne sur signal (SITADEL, DVF, zonage) | alerte poussée (post-MVP) |

Conséquence d'architecture : **le moteur accepte un *ensemble* de parcelles**.
Une parcelle isolée est le cas N=1.

## La cascade d'exclusion (le cœur)

Chaque parcelle traverse une **séquence ordonnée de couches**. Chaque couche
rend un verdict et écrit son **motif humain** — *la traçabilité EST le produit*.

```
HARD_EXCLUDE  → élimination (faux positif quasi certain)   → score d'opportunité = 0
SOFT_FLAG     → contrainte non éliminatoire (faible/moyen/fort)
POSITIVE      → signal favorable
PASS          → traversée sans remarque
UNKNOWN       → donnée indisponible → impacte la COMPLÉTUDE, pas l'opportunité
```

- **Phase 1** (géométrique, locale, PostGIS) : eau, Parc National (cœur/adhésion),
  forêts, SAR, zonage PLU/GPU, SAFER, Géorisques/PPR, trait de côte, pente*,
  ABF, ENS, OCS GE, faux-positifs OSM, surface*. Tourne en **batch** sur toute la commune.
- **Phase 2** (coûteuse, externe, IA) : DVF, SITADEL, Potentiel foncier Région,
  propriétaire/indivision, BPE/SIRENE/BAN. **Uniquement** sur parcelles promues.

\* *Pente et surface sont CALCULÉES et AFFICHÉES mais n'excluent ni ne pénalisent*
*(décision produit). Les seuils existent dans la config, désactivés par défaut.*

## Deux scores, toujours affichés ensemble

- **Complétude (0–100)** — combien on *sait* (poids des sources qui ont répondu).
- **Opportunité (0–100)** — dérivé de la cascade (base 50 − pénalités + bonus + IA).

> **Règle d'or :** le score d'opportunité ne s'affiche **jamais seul**, toujours
> avec la complétude. Complétude < 50 → statut plafonné à `a_creuser`.

---

## Socle technique (contraintes dures)

- **PostgreSQL 15+ / PostGIS 3+** — toutes les intersections sont du PostGIS, index GIST.
- **CRS** : géométries stockées en **EPSG:4326** ; **toute** mesure (surface,
  distance, buffer) reprojetée en **EPSG:2975** (RGR92 / UTM 40S — La Réunion).
  La Réunion n'est **pas** en Lambert-93. Voir `src/labuse/geo.py`.
- **Couche connecteurs/géo** : Python (FastAPI), écosystème géo mûr.
- **Enrichissement asynchrone à résultats partiels** : une source en panne
  n'empêche jamais l'affichage du reste ; cache + backoff sur les quotas.

## Démarrage rapide

```bash
# 1. Une PostGIS locale (ou docker compose up -d, voir docker-compose.yml)
#    Pour une install bare-metal Debian/Ubuntu : voir scripts/dev_db.sh

# 2. Dépendances
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"          # cœur + outils de tests/lint (ajouter ai pour le provider Anthropic)

# 3. Config
cp .env.example .env          # ajuster LABUSE_DATABASE_URL si besoin
export LABUSE_DATABASE_URL=postgresql+psycopg://labuse:labuse@localhost:5432/labuse

# 4. Initialiser le schéma + le catalogue de sources + un jeu de démo Saint-Paul
labuse init-db
labuse seed-sources
labuse seed-demo            # parcelles + couches structurantes synthétiques

# 5. Faire tourner la cascade + le scoring sur la commune pilote
labuse evaluate --commune 97411
labuse discover --commune 97411   # vue Découverte (offre B) : survivantes classées

# 6. API (page Sources, fiche parcelle, découverte)
labuse api      # uvicorn sur http://localhost:8000 (docs : /docs)

# 7. Tests (les tests `db` se skippent si PostGIS injoignable)
pytest
```

## Structure

```
config/                  règles & poids (cascade, complétude, opportunité, WFS) — TUNABLES
src/labuse/
  geo.py                 discipline CRS 4326↔2975 (le point dur)
  models.py              modèle de données (§5) + couches spatiales + DVF/SITADEL
  cascade/               moteur : registry de couches ordonnées + verdicts
  scoring/               complétude + opportunité + décision de statut
  connectors/            sources externes (REST/WFS/CSV) — statut honnête par source
  ai/                    agent LA BUSE : prompt anti-hallucination + JSON borné validé
  ingestion/             catalogue de sources + jeu de démo Saint-Paul
  api/                   FastAPI (Sources de données, fiche, découverte)
tests/                   dont le test de SURFACE obligatoire (m² en 2975, jamais en degrés)
```

## Posture juridique / RGPD (résumé)

Personnes **morales et publiques** uniquement (acquérables) ; **jamais** de
personne physique nominative. DVF agrégé, jamais réidentifié (R112 A-3 LPF).
Indivision via Fichiers fonciers **anonymisés, sous convention** ; champ manuel
en attendant. OSM = signal, jamais vérité juridique. Non-garantie affichée partout.

## État d'avancement

Voir [`STATUS.md`](STATUS.md) pour ce qui est branché, mocké, ou à connecter, et
la suite (ordre de construction du brief §12).
