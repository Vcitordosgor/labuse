# M54-INV — Inventaire des features construites mais non exposées au front

**Lecture seule. Aucune correction, aucun retrait.** Repo `main` (1debf33d). Méthode : 215 routes
FastAPI extraites de `src/labuse/api/` (préfixes résolus), chaque route croisée avec `frontend/src/`
(api.ts + copilote.ts + fetch directs) ; générateurs d'exports tracés jusqu'à leur bouton ; tous
les composants `frontend/src/components/` croisés avec App.tsx + `outils/registry.ts` + Rail/Header.
Trois agents parallèles, recoupés avec l'inventaire existant `qa/m49/routes_inventaire.csv`.

## Chiffres

- **215 routes**. Front en appelle ~120 (106 fonctions api.ts + fetch directs + liens `<a>`).
- **Composants front : 0 orphelin.** Les 28 clés de `outils/registry.ts` ⇄ 28 entrées de dispatch,
  aucune entrée cachée/`disabled`/`EXPOSE`. `MapView`/`TimeMachine` atteints via `lazy()` (App.tsx:27-28).
  → **Tout le front construit est routé.** L'asymétrie est 100 % côté backend.
- **~19 routes ORPHELINES** (capacité user-facing sans bouton) + 3 partielles (statut/journal ignorés).

---

## Catégorie 1 — ORPHELIN (construit, aucun accès UI)

Trié par effort croissant. « Bouton simple » = un `<a>`/appel sur une surface existante (le cluster
export de la fiche `Fiche.tsx:1916-1924` sert de patron). « Page » = surface à concevoir.

| # | Endpoint | Fichier:ligne | Ce que ça fait | Effort |
|---|---|---|---|---|
| 1 | `GET /parcels/{idu}/export?format=onepager\|html\|md` | app.py:3295 → export.py:26/171/431 | One-pager A4 « document de comité » + fiche HTML/Markdown détaillées | **Bouton simple** (1-3 `<a>` dans le cluster export fiche) |
| 2 | `GET /parcels/{idu}/spf-letter` | app.py:3316 | Courrier au Service de la Publicité Foncière pré-rempli (réf. cadastrale) — l'UI *dit* d'utiliser ce workflow (Fiche.tsx:1206/1762) sans jamais le câbler | **Bouton simple** (lien près des notes propriétaire ou module M09 Courrier) |
| 3 | `GET /parcels/{idu}/explain` | app.py:3284 | Explication lisible du score d'une parcelle (distinct de `/modules/faisabilite/{idu}/explain`, lui câblé) | **Bouton simple** (tiroir Synthèse) |
| 4 | `POST /modules/division/compute` | modules.py:81 | Calcule une division parcellaire à la demande (seul le `GET /modules/division` listing est câblé) | **Bouton simple** (l'outil Division existe déjà) |
| 5 | `GET /pre-dossier/{idu}.zip` | pre_dossier.py:209 | Pack pré-dossier PC : CERFA 13406*17 pré-rempli + plan de situation + fiche règles zonage + PCMI | **Bouton + gating** (Intégral-only ; sonde de dispo type `/dossier/statut`) |
| 6 | `POST /moi/logo` · `DELETE /moi/logo` · `POST /moi/marque` | onboarding.py:658/678/689 | Upload/suppression du logo + marque client (marque blanche M23-A). Backend prêt ; **widget d'upload jamais construit** (« reliquat UI upload » M23) | **Bouton + widget** upload dans `/moi` |
| 7 | `GET /shortlist` | app.py:2777 | Liste raccourcie de parcelles | **Bouton/onglet** (petit) |
| 8 | `GET /compare` | app.py:3525 | Comparaison de parcelles (≠ `/comparateur-communes`, lui câblé) | **Page** (surface de comparaison à concevoir) |
| 9 | `GET/POST /filters` · `DELETE /filters/{id}` | app.py:3367/3378/3389 | Filtres sauvegardés côté serveur, scopés compte. Le front persiste les filtres dans l'URL → capacité serveur inutilisée | **Page** (gestion « mes filtres ») |
| 10 | `GET/POST /watch-zones` · `DELETE /watch-zones/{id}` | app.py:3623/3632/3646 | Zones de veille géographiques (table vivante M49) | **Page** (dessin de zone + liste) |
| 11 | `GET /alertes` · `POST /alertes/refresh` · `POST /alertes/ack` | app.py:3657/3667/3676 | Flux d'alertes (rafraîchir / acquitter) | **Page** (adossée aux watch-zones) |
| 12 | `POST /feedback` | app.py:3695 | Soumission d'un retour utilisateur (M49 : « feature future possible ») | **Bouton simple** |

**Partiels** (le générateur/bouton EST exposé, mais le statut/journal associé est ignoré — câbler
= affiner un bouton existant, pas exposer un nouvel artefact) :
- `GET /dossier/statut` (dossier.py:43) — dispo/quota du Dossier (le `.pdf` est câblé, sans le grisé).
- `GET /courrier/statut` · `POST/GET /courrier/envois` (courrier.py:27/43/81) — statut + journal d'envois (seul `/courrier/demande` est câblé).

**À confirmer (peut-être interne, pas user-facing)** :
- `GET /parcels/{idu}/enrichment` (app.py:3236) — payload d'enrichissement d'une parcelle ; sans
  appelant front. Sonne diagnostic/interne autant qu'orphelin — à trancher par Vic avant d'exposer.
- `GET /map/bati` (app.py:2681) · `GET /map/permits.geojson` (app.py:2934) — couches bâti/permis en
  GeoJSON ; **vraisemblablement remplacées par les tuiles vectorielles** (`/map/tiles/ov/...`, câblées).
  Probablement VOLONTAIRE (supplantées) plutôt qu'orphelines — à confirmer.
- `GET /assemblages` · `GET /assemblage/study` (app.py:2700/2712) — listing/étude assemblage en GET ;
  le front pilote l'assemblage par `POST /moteurs/assemblage`. Probablement supplantées.

---

## Catégorie 2 — VOLONTAIRE (fermé par décision — cités, NON rouverts)

| Endpoint | Fichier:ligne | Décision |
|---|---|---|
| `GET /api/v1/parcels` · `GET /api/v1/docs` | partners.py:466/509 | **API partenaire externe** (apikey + quota). Externe par conception. |
| `POST /partners/match/run` · `GET /partners/match/compatibilite/{idu}` · `GET /partners/share/{idu}/list` | partners.py:98/125/234 | Helpers front `runMatch`/`matchCompatibilite`/`listShares` **RETIRÉS** (M49, « 0 importeur », api.ts:456). |
| `POST /ia/synthese/{idu}` · `POST /ia/pourquoi/{idu}` | ia.py:669/679 | Marqués « douteuses » (api.ts:401) ; helpers front retirés. |
| `GET /api/copilote/runs/{run_id}` | copilote.py:128 | Remplacé par le flux SSE `/events` (seul un script de démo l'appelle). |
| `GET /p/{token}` | partners.py:353 | Page de partage publique (lien e-mail). Externe par conception. |
| `GET /events/desabonner` | events.py:772 | Désinscription digest (lien e-mail à token). Externe par conception. |
| `POST /stripe/webhook` | onboarding.py:283 | Callback Stripe (HMAC). Externe par conception. |
| `GET /parcels` · `GET /stats` | app.py:1135/1461 | Legacy, supplantés par `/filtre` (exercés par QA/e2e). |

**Rails déjà retirés du code (historique, pas des routes vivantes — pour mémoire)** :
`/app` proto Vue (auth.py:69) · `/ia/segments-search` spin-off Vues (ia.py:425) ·
`DELETE /partners/share/token/{token}` 0-caller (partners.py:229) · cron catnat (ops.py:27) ·
`matrice_statut` v1 morte (tiles.py:148/340).

---

## Catégorie 3 — INTERNE (admin / CLI / ops / diagnostic par design)

| Groupe | Endpoints | Gate |
|---|---|---|
| **Admin** (gate `exiger_admin`) | `POST /bilan/params` (app.py:3510) · `POST /parcels/{idu}/evaluate` (app.py:3540) · `GET /protection/admin` · `POST /protection/admin/gel/{sujet}` · `.../degel/{sujet}` (protection.py:433/452/462) | 403 admin |
| **Santé / ops** (public allowlist) | `/health` · `/healthz` · `/readyz` · `/healthz/crons` (ops.py:48) | public |
| **Diagnostic / calibration (lecture)** | `/demo-status` · `/coverage` · `/demo` · `/assistant/status` · `/communes/status` · `GET /bilan/params` | auth (panneau admin) |
| **QA / audit scoring** | `POST /sources/{id}/test` · `POST /audit/reference\|adresse\|polygone` · `GET /signalements` + `/signalements/export.csv` | auth/admin |
| **Cron / event-detection** | `POST /events/detect` · `POST /events/demo` · `POST /events/reprise/{idu}` · `GET /events/digest` (JSON ; seul `.html` est lié) | auth, CLI/cron |
| **Anti-abus** | `POST /protection/defi` (protection.py:409) | challenge/token |

**Librairies d'export sans endpoint (internes, transitives)** : `briques_pdf.py` (chrome/sections PDF
partagés par argumentaire/banquier/lettre_zonage), `resume.py` (bloc de synthèse injecté dans le PDF
premium), `export_commun.py` (helper partagé). Exposées *à travers* leurs consommateurs, jamais seules.
Pas de « rapport potentiel » autonome : n'existe que comme *section* de brique (briques_pdf.py:388),
aucun endpoint dédié.

---

## Notes de fiabilité

- **Générateurs de documents : aucun `EXPOSE=False`.** Le seul `EXPOSE` du repo est
  `division_or.py:55 EXPOSE = True # VALIDÉ Vic 28/07/2026` (segment O12 « Division en or »,
  **activé** — pas un générateur de document).
- **`dossier` soft-gated par déploiement** : `GET /dossier/{idu}.pdf` renvoie **501** si le module
  `labuse.flash` n'est pas importable (dossier.py:89). Le bouton « Dossier » (Fiche.tsx:1920) peut
  donc 501 hors environnement Flash — exposé mais fragile selon le déploiement.
- Recoupement `qa/m49/routes_inventaire.csv` (54 lignes, mandat M49) : mêmes verdicts
  (`DOUTEUSE/LISTÉE` conservées, cluster onboarding/partners/ops = `EXTERNE-PAR-CONCEPTION`).
- Les lignes « navigation navigateur » (login/logout/légal/flash/onboarding, `/`, `/guide`,
  `/events/digest.html`, `/moteurs/barometre.pdf`) sont atteintes par `<a>`/redirect, pas `fetch` —
  comptées CÂBLÉES, non orphelines.

## Synthèse (1 phrase)
Le front est intégralement routé ; **la dette d'exposition est côté backend** : ~12 orphelins nets
(dont 6 « bouton simple » à quasi-zéro effort : one-pager comité, lettre SPF, explain, division/compute,
feedback, upload marque) + 3 partiels de statut, le reste étant volontairement fermé ou interne.
