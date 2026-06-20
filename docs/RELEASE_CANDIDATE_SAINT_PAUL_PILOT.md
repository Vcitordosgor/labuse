# Release Candidate — LA BUSE, pilote Saint-Paul complet

> Candidate à devenir la **version pilote Saint-Paul** avant merge vers `main` et déploiement VPS.
> Audit du **2026-06-20**, branche `claude/brave-davinci-NaRd4` (79 commits devant `main`).
> **Aucune base modifiée, aucune cascade, aucun verdict changé** lors de cet audit (lecture seule).

## Verdict

| Décision | Statut |
|---|---|
| **Note de confiance** | **9 / 10** |
| **Merge vers `main`** | **GO** |
| **Déploiement VPS** | **GO sous réserve** (poser les secrets dans `/etc/labuse/labuse.env` ; HTTPS) |

Aucun point **bloquant**. Détails en fin de document.

---

## 1. Saint-Paul complet (données)

| Indicateur | Valeur | Source |
|---|---|---|
| Parcelles Saint-Paul | **51 129** | `parcels` |
| Sections cadastrales | **98** | `parcels.section` |
| Parcelles évaluées | **51 129 (100 %)** | `parcel_evaluations` |
| Géométries `geom_2975` invalides / nulles | **0 / 0** | `/demo-status` |
| Index GIST géométriques | **2/2** + index voirie partiel | `/demo-status` |

**Verdicts (dernière évaluation par parcelle) :**

| Verdict | Nombre |
|---|--:|
| Opportunité | **524** |
| À creuser | 19 172 |
| Écartée (exclue) | 1 490 |
| Faux positif probable | 29 943 |
| **Total** | **51 129** |

Dont **156 micro-opportunités** (opportunités 251–500 m²) — verdict **inchangé**, nuancées par badge.

## 2. Couches critiques (ingérées)

| Couche | Entités | | Couche | Entités |
|---|--:|---|---|--:|
| Bâtiments (BD TOPO) | **83 981** | | Pente (RGE ALTI) | 13 062 |
| Voirie (BD TOPO) | **5 000** | | Zonage PLU/GPU | 1 097 |
| SAR | 303 | | PPR | 4 |
| DVF (mutations) | 3 651 (2021–2025) | | OSM faux positifs | 808 |

Couches non bloquantes en statut explicite (jamais de faux « vacant »/« pas de risque »).

## 3. Index voirie (perf cascade)

`idx_spatial_layers_voirie_geom2975` — index GIST **partiel** (`WHERE kind = 'voirie'`), **présent** en
base et **recréé automatiquement** par `models.ensure_geom_2975` (VPS / restauration / déploiement neuf).
Sans lui, le KNN distance-voirie parcourait les 84 k bâtiments (cascade en heures). Verrouillé par test.

## 4. Assistant IA « Expliquer cette parcelle »

- **Sans clé** : synthèse **règles déterministe** en 5 blocs (Potentiel / Contraintes / Bâti-libre /
  Économie indicative / Recommandation), dérivée des **seuls faits** — anti-hallucination par construction,
  jamais « cassé ». État actuel : `/assistant/status` → `configured:false`.
- **Avec clé** (`ANTHROPIC_API_KEY`) : bouton « Enrichir avec l'IA », prose bridée par un prompt système
  strict (provenance imposée, refus de conclure si données minces, jamais « constructible » certain).
- **Dégradation** : clé absente / 401 / timeout / réseau → synthèse règles + message, **jamais de 500**.
- Réf. : `docs/AI_ASSISTANT_SAFETY_AND_DEMO.md`, `docs/AI_DEMO_CHECKLIST.md`.

## 5. Bilan transparent

Provenance **ligne par ligne** : prix de sortie **sourcé** (DVF réel) · coûts construction/VRD/marge
**estimés** · totaux **calculés**. Microcopy « Simulation indicative — paramètres calibrables selon vos
ratios promoteur ». Marge alignée code/doc (**9 %** net, honoraires + frais déduits séparément).

## 6. Barème documenté

`docs/BAREME_VERDICT_MUTABILITE.md` : score d'opportunité (base 50, pénalités, bonus), complétude
(12 familles), arbre du verdict, contraintes bloquantes vs vigilance, déclassement métier, mutabilité,
récap des seuils + **5 PLACEHOLDER** signalés. Tooltip fiche : « score élevé mais à creuser » expliqué.

## 7. Micro-opportunités

Audit `docs/AUDIT_PETITES_OPPORTUNITES_251_500.md` : 156 parcelles 251–500 m² (100 % U/AUc, libres,
desservies, mais SDP/économie marginales). **Option A appliquée** : badge « micro-opportunité » (affichage,
**0 verdict changé**), microcopy + mise en avant assemblage. **Option B** (déclassement économique) en
attente de validation.

## 8. Démo conforme

`/demo-status` → `ready_for_demo: true`, **8 parcelles scénarisées `all_conform: true`**, healthcheck
**14/14** (parcelles, géométries, index, DVF, PPR/SAR/OSM/bâti, déclassement, top-20 sans faux positif,
badge « opportunité vérifiée », prospection, pipeline, exports). Parcours guidé prêt.

## 9. Sauvegardes (hors git)

| Backup | Fichier | Taille | SHA-256 |
|---|---|---|---|
| LOT 1 (pré-import) | `labuse-labuse-20260620-101644.dump` | 235 M | (vérifié LOT 1) |
| **Post-LOT 2** (étalon) | `labuse-post-lot2-saint-paul-complet-20260620-140347.dump` | **477 M** | `9c6d26af…9a61d1` |

Dans `/var/backups/labuse/` sur l'hôte, **jamais commités** (`.gitignore` : `*.dump`, `backups/`).
Restauration testée. Documentés ici, hors dépôt.

## 10. Pack de déploiement VPS

`deploy/` : `systemd/labuse.service` (EnvironmentFile=/etc/labuse/labuse.env, 2 workers, durcissement) ·
`nginx/labuse.conf` (reverse proxy 127.0.0.1:8000) · `Caddyfile.example` · `scripts/{smoke_test,
backup_postgres,db_maintenance}.sh` · `postgresql/postgresql.vps2.conf` · `env/labuse.env.example`.
Docs : `docs/DEPLOYMENT_OVH_VPS.md` (0→13 + annexe merge), `docs/VPS_GO_LIVE_CHECKLIST.md`.

## 11. Variables d'environnement de production

Gabarit : **`deploy/env/labuse.env.example`** (variables RÉELLES, préfixe `LABUSE_`, **aucun secret**).
À installer en `/etc/labuse/labuse.env` (640 root:labuse, hors git) :
`LABUSE_DATABASE_URL`, `LABUSE_ENV=production`, `LABUSE_AUTH_PASSWORD`, `LABUSE_SECRET_KEY`,
`LABUSE_PUBLIC_URL`, `ANTHROPIC_API_KEY=` (vide = mode règles), `LABUSE_ASSISTANT_MODEL=claude-sonnet-4-6`.

---

## Tests & santé (cette recette)

| Vérification | Résultat |
|---|---|
| **Full pytest** | **404 passed** |
| **Ruff** | **clean** |
| Tests ciblés (Saint-Paul qualité + assistant + micro + démo) | **44 passed** |
| **e2e Playwright** (standalone) | **0 échec** |
| `/readyz` | `ready:true`, schema/data OK |
| `/demo-status` | `ready_for_demo:true`, 8/8 conformes, healthcheck 14/14 |
| `/assistant/status` | `configured:false` (attendu, sans clé) |

## Sécurité

Aucun secret dans git (`git grep sk-ant-` = rien hors stubs de test) · `.env` **et** `deploy/env/*.env`
ignorés (seuls les `*.env.example` versionnés) · aucune vraie clé API · aucune clé loggée · aucun endpoint
ne renvoie de secret (`/assistant/status` = booléen, `/explain` sans champ clé) · backups hors dépôt.

## Cohérence déploiement

`LABUSE_DATABASE_URL` partout (aucun `DATABASE_URL` nu) · `ANTHROPIC_API_KEY` seulement comme **nom de
variable** (valeur uniquement dans `/etc/labuse/labuse.env`, hors repo) · systemd lit bien
`EnvironmentFile=/etc/labuse/labuse.env` · Nginx reverse-proxy cohérent · `smoke_test.sh` présent ·
rollback documenté (§13 + rollback IA express).

---

## Points NON bloquants (à savoir)

- **e2e sous charge concurrente** : si la suite pytest tourne EN MÊME TEMPS que l'e2e, 1–2 scénarios async
  (filtre verdict, KPI) peuvent flaker par timeout serveur. **Standalone : 0 échec.** → lancer l'e2e seul en CI.
- **IA** : `configured:false` (aucune clé) — volontaire ; la démo est premium en mode règles. Activer la clé
  reste un geste serveur (voir checklist).
- **Bilan** : valeurs encore à calibrer (case C, ratios réels Vic) — affichées « estimé/indicatif », non bloquant.
- **5 PLACEHOLDER** de barème (seuils A/N, ER, ravine, pente) documentés comme « à calibrer ».
- **Option B** micro-opportunités (déclassement économique) en attente de décision (change des verdicts).

## Points BLOQUANTS

**Aucun.**

---

*Release candidate prête. Merge `main` : GO. Déploiement : GO une fois les secrets posés sur le VPS et
HTTPS actif. Procédure de merge : annexe de `docs/DEPLOYMENT_OVH_VPS.md`.*
