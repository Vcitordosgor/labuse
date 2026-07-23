# Tenue en charge + cartographie des secrets — rapport

> **Mandat `infra/charge-et-secrets` · 2026-07-23 · branche pushée, non mergée (Vic merge)**
> Volet A (M6) : combien de clients le VPS tient. Volet B (M5) : où vit chaque secret (lecture seule).
> Golden 116/116 · suite 1139/0 · smoke prod vert. Aucune valeur de secret ici.

---

# VOLET A — Le VPS tient combien de clients ?

## A1 — Baseline (au repos)
| Ressource | Valeur |
|---|---|
| VPS | **6 vCores · 11 Gio RAM · 100 Go NVMe** (56 Go libres) |
| Au repos | loadavg **0.00**, ~1 Gio RAM utilisée, 9,5 Gio en cache page |
| uvicorn | **2 workers** (`--workers 2`, loopback :8000, derrière Caddy) |
| SQLAlchemy | pool par défaut **5 + 10** overflow → ~15 conn/worker → ~30 max à 2 workers |
| PostgreSQL | `max_connections=100` · `shared_buffers=128 Mo` · `work_mem=4 Mo` · `effective_cache_size=4 Go` (défauts d'usine — jamais tuné pour ce boîtier) |
| Caddy | aucune limite de débit/taille explicite (s'appuie sur la garde applicative P0) |

## A2 — Test de charge (prod, IP QA exemptée de la garde → capacité BRUTE)
**Outil** : script maison `qa/loadtest.py` (httpx + threads). Choisi pour l'arrêt instantané, zéro install, et parce que la charge part du Mac dont l'IP est dans `LABUSE_QA_ALLOWLIST` → **exemptée du rate-limit/quota** (on mesure la capacité réelle, pas la protection). Vérifié **zéro session/trafic réel** pendant toute la campagne (monitoring continu, prêt à stopper).

**Paliers, scénario NAVIGATION** (parcours client : dashboard → liste → fiches → outil ; *charge continue, sans temps de réflexion*) :
| Users | RPS | Err | p50 | p95 | p99 | CPU idle |
|--:|--:|--:|--:|--:|--:|--:|
| 5 | 15.4 | 0 % | 28 ms | 990 ms | 1 072 ms | 13 % |
| 10 | 15.6 | 0 % | 45 ms | **1 664 ms** | 1 837 ms | **0 %** |
| 25 | 21.0 | 0 % | 125 ms | 3 731 ms | 4 253 ms | 0 % (load 12) |
| 50 | 19.1 | 0 % | 2 320 ms | 5 992 ms | 7 143 ms | 0 % (load 19) |

**Carte** (tuiles, majoritairement en cache) : c=25 → RPS 17.7, p95 2 326 ms, CPU idle 29 % (moins gourmand, mais plafonné par les 2 workers).
**Mixte réaliste** (70 % nav / 20 % carte / 10 % lourds) : c=5 → p95 11 s ; c=10 → p95 2,5 s ; c=25 → RPS 10.9, p95 5,4 s. Le **PDF banquier (22 s)** écrase la queue.

**Latences 1 utilisateur** (référence) : endpoints légers 27-40 ms · **fiche `/parcels/{idu}` p50 628 ms / p95 1,7 s** · CSV 1,3 s · **PDF banquier 22 s**.

### 🔴 Où ça casse en premier : **le CPU de PostgreSQL**
Sous charge nav, snapshot processus : **PostgreSQL = 93 % CPU, uvicorn = 5 %**. vmstat : `us=92-94 %, wa=0 %, id=0 %`, données 100 % en RAM (aucune I/O). → **100 % CPU-bound, dans PostGIS**, à cause du calcul spatial live **par fiche** (`/parcels/{idu}`). La saturation CPU arrive dès **~10 utilisateurs actifs continus**. Le débit plafonne (~15-21 req/s) et n'augmente plus — seule la latence grimpe. **Taux d'erreur ~0 % partout** : l'app **ralentit, elle ne casse pas** (dégradation gracieuse, pas de 500/429).

## A3 — Corrections testées (avec avant/après)
Le mandate suggérait workers/pool/work_mem. **Je les ai testés — aucun ne s'applique**, car la charge est CPU-bound dans PG (pas I/O, pas uvicorn) :

| Réglage testé | Avant | Après | Verdict |
|---|---|---|---|
| **uvicorn 2 → 4 workers** | nav c12 **18.0 rps** / p95 1963 | nav c12 **14.1 rps** / p95 2202 (c25 : 21.0 → 21.4, plat) | ❌ **Aucun gain, léger recul** → plus de workers = plus de requêtes PG lourdes concurrentes sur les mêmes 6 cœurs. **Reverté.** |
| **`max_parallel_workers_per_gather` 2 → 0** | nav c12 18.0 / p95 1963 | nav c12 18.0 / p95 1938 | ❌ Nul (les requêtes fiche sont trop petites pour paralléliser). **Reverté.** |
| **`shared_buffers` / `work_mem`** | — | *non modifiés* | Inopérants sur une charge **compute-bound** (`wa=0`, tout en cache) — ne toucheraient pas le CPU. |

**Conclusion A3 : aucun réglage de config ne débloque le débit.** Le goulot est le calcul PostGIS par fiche — un problème **applicatif** (à matérialiser, hors périmètre « pas de refonte »), pas un problème de dimensionnement. Prod laissée **exactement dans son état initial** (workers=2, per_gather=2). Seule correction posée : **A5** (verrou schema-heal, commit séparé).

## A4 — Verdict opérationnel (pour vendre)
- **Capacité sereine aujourd'hui** : **~5-10 clients cliquant activement en même temps** (p95 < 2 s). Comme les vrais clients **réfléchissent entre deux clics**, cela couvre **plusieurs dizaines de clients connectés** qui naviguent — tant qu'ils ne cliquent pas tous à la même seconde. **Au-delà de ~15-20 clients simultanément actifs, ça rame** (p95 > 3 s). Chiffre honnête et prudent à annoncer : **« confortable jusqu'à ~10 sessions actives concurrentes »**.
- **Premier signe d'alerte** : le **CPU**. `loadavg` VPS **> 6** (= nb de cœurs) soutenu, ou PostgreSQL proche de 100 % CPU. ⚠ **Ce n'est pas exposé aujourd'hui** : `/healthz` ne porte aucune métrique de perf. **Reco** : ajouter la `loadavg` à `/healthz` (ou à `watch_prod.sh`) pour que la saturation soit visible avant que le client ne la sente.
- **Plan de croissance (ordre des leviers)** :
  1. **D'abord régler l'app, pas grossir** : **matérialiser le calcul spatial de la fiche** (comme `mvt_parcels`/`parcel_zone_plu` le font déjà pour les tuiles) au lieu de le recalculer en PostGIS à chaque requête. C'est le **plus gros gain** (potentiellement ×3-5 de capacité sans nouveau matériel) — mais c'est une **refonte** → mandat dédié, décision Vic.
  2. **Ensuite, plus gros VPS** : charge CPU-bound et ~linéaire → **12 vCores / 24 Gio** ≈ **×2** de capacité concurrente. À faire **après** le levier 1 si encore contraint.
  3. **Ne PAS ajouter de workers** (prouvé sans gain — PG est le mur, pas uvicorn).
- **Risque N+1 (un gros client qui aspire)** : **bien couvert**. (a) Exfiltration données = quotas P0-2 (40 000 tuiles/j, 400 geojson/j, abuse-scan) + masquage propriétaire. (b) **Monopolisation CPU** = le **rate-limit 60 req/min par sujet** + **quota 300 fiches/j** plafonnent un client à ~1 fiche/s (~5 % de la capacité) ; le **PDF est capé à 20/mois/plan**. → **un seul client ne peut pas saturer le boîtier.** Le quota carto P0-2 protège suffisamment.

## A5 — Verrou du schema-heal (commit `9744896`)
La course entre les 2 workers uvicorn sur `CREATE TYPE` au 1er boot (constatée à la matérialisation P0-1) est corrigée par un **`pg_advisory_lock`** tenu pendant toute la remédiation : le 2e worker attend, ne voit que des objets existants → les deux finissent `schéma=ok`. Fini le faux positif d'alerte à chaque migration. Boot local vérifié, suite 1139/0.

---

# VOLET B — Cartographie des secrets (lecture seule)

Détail complet : [`docs/audits/SECRETS_CARTOGRAPHIE.md`](../audits/SECRETS_CARTOGRAPHIE.md) · Rotation pas-à-pas : [`docs/RUNBOOK_ROTATION_CLES.md`](../RUNBOOK_ROTATION_CLES.md).

**Bilan** : ~15 secrets cartographiés (Postgres, `SECRET_KEY`, Stripe ×2, Anthropic, mot de passe pilote, rideau Caddy, INPI, Merci Facteur, SMTP, clé SSH). **Aucune valeur exposée dans ce mandat.**

**Findings** :
- ✅ **Aucun secret réel dans git** (les `+…=` des `.example` sont des placeholders ; `.env` réel jamais tracké), **ni dans le code**, **ni dans `~/.zsh_history`**. Propre.
- 🟠 **Secrets en clair au repos** sur le Mac : `.env` (gitignoré) + `~/labuse-backups/M7_SECRETS.txt` (chmod 600). Acceptable, mais → **passer à Bitwarden** comme source de vérité.
- ⚠ **Deux secrets vivent à plusieurs endroits couplés** : le **mot de passe Postgres** (env VPS + `.pgpass` + `.env` Mac) et le **hash basic_auth** (`/etc/caddy/labuse.env`) — à faire bouger ensemble (runbook §8/§5).

---

# Liste priorisée pour Vic

**Charge (M6)** :
1. *(Info)* Capacité sereine ~5-10 sessions actives ; N+1 couvert par les quotas P0.
2. *(Reco, mandat dédié)* **Matérialiser la fiche** — le seul vrai levier de capacité sans matériel.
3. *(Reco rapide)* Exposer `loadavg` sur `/healthz` / `watch_prod.sh` — voir la saturation avant le client.
4. *(Quand ~15+ clients actifs)* Passer à **12 vCores**.
5. ✅ *(Fait)* Verrou schema-heal (A5) — à merger.

**Secrets (M5)** — aucune urgence (rien de fuité) :
6. Rentrer les ~11 secrets dans **Bitwarden** (checklist runbook B4).
7. Rotation d'hygiène planifiée aux heures creuses : `SECRET_KEY` puis Postgres (les deux qui coupent).
8. Roter en priorité **tout secret précis ayant transité par un canal moins maîtrisé** (chat, capture, e-mail), si applicable.

---

*Livrables : `qa/loadtest.py` (outil), ce rapport, `SECRETS_CARTOGRAPHIE.md`, `RUNBOOK_ROTATION_CLES.md`, commit A5. Golden 116/116, suite 1139/0, smoke prod vert. Prod laissée dans son état initial (réglages de test tous revertés).*
