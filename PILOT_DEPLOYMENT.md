# LA BUSE — Déploiement pilote

> Comment préparer, vérifier et lancer LA BUSE pour une **démo** ou un **pilote client**,
> de manière reproductible — sans dépendre d'une mémoire humaine.
> Principe : **un serveur qui tourne ne veut pas dire que LA BUSE est prête.**
> Quatre niveaux d'état, observables séparément :
>
> | Niveau | Question | Comment vérifier | Comment réparer |
> |---|---|---|---|
> | 1. App | le process répond ? | `GET /healthz` | relancer `labuse api` |
> | 2. Schéma | tables/colonnes/triggers/index OK ? | `GET /readyz` · `labuse doctor` | **auto au boot** (ou `doctor`) — secondes |
> | 3. Données | parcelles + PPR/SAR/DVF/OSM + évaluations ? | `GET /readyz` · `doctor` | `labuse rebuild-demo` (~5 min) |
> | 4. Démo | healthcheck 13/13 + parcelles conformes + cache chaud ? | `GET /demo-status` · `doctor` | `rebuild-demo` puis `labuse warm-demo` |

---

## 1. Prérequis

- **PostgreSQL 15+ / PostGIS 3+** démarré, avec une base (défaut : `labuse`).
- **Python 3.11+**, venv : `pip install -e ".[dev]"` (ou `pip install -r requirements.txt`).
- **Réseau sortant** pour la (re)construction des données : cadastre Etalab, geo-dvf
  (files.data.gouv.fr), API Carto GPU, Région Réunion ODS, IGN Géoplateforme, Overpass.
- Réseau pour l'interface : la carte charge Leaflet (unpkg) et des tuiles (CARTO/IGN) —
  **tester le réseau du lieu de démo à l'avance**.

## 2. Variables d'environnement

Copier `.env.example` → `.env`. Les essentielles :

| Variable | Défaut | Rôle |
|---|---|---|
| `LABUSE_DATABASE_URL` | `postgresql+psycopg://labuse:labuse@localhost:5432/labuse` | base PostGIS |
| `LABUSE_PILOT_COMMUNE_INSEE` / `_NAME` | `97415` / `Saint-Paul` | commune pilote |
| `LABUSE_CONFIG_DIR` | `config` | règles & poids (cascade/scoring) |
| `LABUSE_ENRICH_LIVE` | `1` | `0` = couper les appels externes RGE ALTI/GPU (offline) |
| `LABUSE_HTTP_TIMEOUT_S` | `20` | timeout des connecteurs |

## 3. Préparer un pilote — LA commande

```bash
labuse prepare-pilot --commune 97415
```

Elle enchaîne, **sans rien relancer inutilement** :
1. **Schéma** : réconciliation légère idempotente (tables, colonnes `geom_2975`/`prospection`,
   triggers, index — secondes, jamais de recalcul massif) ;
2. **Données** : healthcheck → s'il est déjà OK, le rebuild est **sauté** ; sinon
   `rebuild-demo` (cadastre si absent + couches PPR/SAR/DVF/OSM/pente/PLU + évaluation, ~5 min) ;
3. **Healthcheck final** : doit être ✅ PRÊT (13/13), sinon exit 1 ;
4. **Pré-chauffe** (`warm-demo`) : les 8 fiches de démo deviennent instantanées, leurs statuts
   et exports sont vérifiés ;
5. Confirmation : `✅ PILOTE PRÊT`.

Codes de sortie : `0` = prêt · `≠0` = pas prêt (la sortie dit **quoi lancer**).
Déjà prêt ? La commande complète prend **~6 secondes**.

Variante sans reconstruction (CI / vérification pure) : `labuse prepare-pilot --skip-rebuild`
(échoue proprement si l'état n'est pas prêt, sans rien toucher).

## 4. Vérifier que tout est prêt

```bash
labuse doctor            # diagnostic complet : DB → schéma → données → démo + quoi faire
labuse demo-healthcheck  # les 13 contrôles de la base de démo (exit ≠ 0 si KO)
```

Côté HTTP (monitoring / intégration) :
- `GET /healthz` → 200 = le process répond (ne dit rien des données) ;
- `GET /readyz` → 200 = schéma + données critiques ; **503** sinon, avec `missing` et `actions` ;
- `GET /demo-status` → état complet (healthcheck, parcelles de démo, cache chaud,
  `ready_for_demo`, actions).

Dans l'interface : bouton **« 🎬 Démo guidée »** → le panneau **« État de la démo »** affiche
les mêmes informations, avec la commande à lancer si quelque chose manque.

## 5. Lancer

```bash
labuse api               # http://127.0.0.1:8000 → interface /app/
```

Au démarrage, l'app **auto-répare le schéma** (léger : colonnes/triggers/index) — utile après
un recyclage d'environnement. Elle ne télécharge **jamais** de données et ne recalcule
**jamais** une commune au boot : si des données manquent, `/readyz` répond 503 et nomme
l'action (`labuse rebuild-demo`).

## 6. Si le healthcheck échoue

1. Lire les `✗` de `labuse demo-healthcheck` (chaque ligne nomme la couche en cause).
2. `labuse doctor` — confirme le niveau en panne et la commande à lancer.
3. Cas le plus courant (environnement recyclé : couches/évaluations perdues) :
   `labuse rebuild-demo --commune 97415` (~5 min), puis `labuse warm-demo`.
4. Re-vérifier : `labuse demo-healthcheck` → ✅ PRÊT.
5. Une parcelle de démo a « dérivé » (statut ≠ attendu, signalé par warm-demo / le panneau) :
   relancer `rebuild-demo` ; si la dérive persiste, les données publiques ont changé →
   mettre à jour `DEMO_PARCELS` (`src/labuse/demo.py`) en conscience.

## 7. Relancer proprement (environnement recyclé)

```bash
git fetch origin claude/brave-davinci-NaRd4 && git reset --hard FETCH_HEAD
labuse prepare-pilot --commune 97415     # schéma + rebuild si besoin + healthcheck + warm
labuse api
```

## 8. Checklist avant rendez-vous client

- [ ] `labuse prepare-pilot` → **✅ PILOTE PRÊT** (la veille, puis le matin même) ;
- [ ] réseau du lieu testé (tuiles carte + unpkg accessibles) ;
- [ ] `labuse api` lancé, `/app/` ouvert, panneau « Démo guidée » → **✅ Démo prête** ;
- [ ] fiches BP0571 / BO0845 / BN1351 ouvertes une fois (instantanées si warm fait) ;
- [ ] un export (md/html) ouvert et gardé sous la main ;
- [ ] relire `DEMO_PACK.md` (script, objections, limites) — et ses versions imprimables.

## 9. Limites actuelles (assumées)

- **Pilote mono-commune** (Saint-Paul) — le multi-communes existe (`ingest-island`) mais n'est
  pas l'état vendu.
- **Pas d'authentification / multi-utilisateur** : ne pas exposer publiquement en l'état
  (CORS ouvert, aucune gestion d'accès).
- **Reconstruction des données = réseau + ~5 min** : prévue AVANT le rendez-vous, pas pendant.
- **Prospection 100 % manuelle** (choix légal, cf. `PROPRIETAIRES_NIVEAU_2.md`).
- La carte dépend de CDN externes (Leaflet/tuiles).

## 10. Pas encore industrialisé (honnêteté)

- Pas de conteneurisation/orchestration (Dockerfile, compose, CI de déploiement).
- Pas de sauvegarde/restauration automatique de la base (le rebuild reconstruit depuis
  les sources publiques — c'est le filet actuel).
- Pas de supervision continue (les endpoints `/healthz`/`/readyz` sont prêts à être branchés
  sur un monitoring, mais aucun n'est configuré).
- Pas de gestion de secrets centralisée (`.env` local).

---

*LA BUSE vérifie, priorise, explique et organise la prospection. Elle ne garantit jamais
constructibilité, propriété ni rentabilité — y compris dans ce document.*
