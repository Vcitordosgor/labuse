# QA Radar Mutation V1 — end-to-end (lecture seule)

> **Document de QA** (artefact de recette). Rédigé le **2026-06-27**, versionné après validation humaine.
> Périmètre testé : moteur (Phase 2A) + API (Phase 2B) + UI sobre (Phase 2C).
> Base de code figée à `main = origin/main = bfa5631`.
> **Aucune modification** de code / DB / scoring / verdict / UI / migration durant cette QA.

---

## Verdict global : ✅ **GO**

Radar Mutation V1 est **fonctionnellement correct, sûr et sobre**. Aucun bug bloquant, aucun
bug important. Score de mutation visuellement et sémantiquement **distinct du verdict
d'opportunité**, wording prudent respecté partout, endpoints en **lecture seule** (DB inchangée).
Seul point de vigilance, **non bloquant** : la latence de la liste `/mutation` (~4,7 s, asynchrone
et non bloquante) — candidate à une optimisation V2.

---

## 1 · État initial

| Élément | Valeur | Attendu | OK |
|---|---|---|---|
| `git status` | clean, `## main...origin/main` | clean | ✅ |
| `main` == `origin/main` | `bfa5631c…` == `bfa5631c…` | identiques | ✅ |
| DB accessible | oui (psql) | oui | ✅ |
| parcelles | **431 663** | 431 663 | ✅ |
| `parcel_evaluations` | **1 132 371** | inchangé | ✅ |
| opportunités (verdict, dernier état) | **9 103** | 9 103 | ✅ |
| évaluations « stale » (≠ `fb6a5478b2bf`) | **0** | 0 | ✅ |
| `cascade_results` | 8 997 413 | inchangé | ✅ |
| Disque (`/`) | 93 % util., **3,0 G libre** | suffisant lecture seule | ⚠️ noté |

---

## 2 · API testée

Endpoints : `GET /mutation/{idu}` (fiche) et `GET /mutation` (liste). Contrat JSON vérifié :
`score_mutation` (0–100), `niveau` ∈ {prioritaire, forte, surveiller, faible}, `confiance`,
`confiance_bande`, `badges[]`, `raisons[{cle, points, detail}]`, `limites[]`.

| Cas | idu | HTTP | Latence | Résultat |
|---|---|---|---|---|
| Prioritaire | `97415000DM0031` | 200 | ~10 ms | score **100** / prioritaire / confiance 92 (forte) ; 6 raisons ; badges ✓ |
| Faible | `97415000ET1719` | 200 | ~14 ms | score **33** / faible / confiance 92 ; raisons zonage+marché+foncier ✓ |
| Déjà opportunité | `97415000CP0024` | 200 | ~13 ms | score **75** / prioritaire (le verdict reste « opportunité » par ailleurs) ✓ |
| Déjà opportunité | `97415000CT0348` | 200 | ~11 ms | score **75** / prioritaire ✓ |
| Inexistante | `00000000000000` | **404** | ~4 ms | 404 correct (parcelle inconnue) ✓ |
| Liste prioritaire `limit=8` | — | 200 | ~4,7 s | count=8, **triée décroissante** [100×8], tous `prioritaire` ✓ |
| Liste `min_score=80` | — | 200 | ~4,7 s | tous score ≥ 80 ✓ |
| Liste `niveau=bidon` (invalide) | — | 200 | ~4,7 s | count=0, liste vide — **dégradation gracieuse**, pas de crash |

**Wording prudent (API)** — la note `limites[0]` est constante :
> « Potentiel de mutation à étudier — ni constructibilité ni vente garanties. »

Aucun terme interdit (`constructible certain`, `à acheter`, `le propriétaire vendra`) dans
aucune réponse. ✅

**Observation de conception (non-bug)** : `/mutation?niveau=faible` renvoie **count=0** en
prod. C'est **voulu** : la liste fait une présélection SQL (prescore) qui ne remonte que des
candidats à **fort** potentiel ; les parcelles « faibles » ne sont jamais candidates. L'UI ne
demande de toute façon que `niveau=prioritaire` — sans impact utilisateur.

---

## 3 · UI testée

Page `/app/` (commune pilote Saint-Paul). Tests Playwright (Chromium) automatisés.

| Élément | Constat | OK |
|---|---|---|
| Chargement app | titre « LA BUSE — radar foncier · La Réunion », DOM monté | ✅ |
| Sidebar « Radar Mutation — à surveiller » | section `.ck-radar` présente, **8 items**, compteur « 8 » | ✅ |
| Intro sidebar | « Potentiel de transformation foncière à étudier — score distinct du verdict d'opportunité. » | ✅ |
| Bloc fiche (parcelle prioritaire) | `.mut-card` rendu, **100/100**, niveau, confiance, badges, raisons chiffrées (+pts), note prudente | ✅ |
| Accent visuel distinct du verdict | bordure gauche **`rgb(139,127,214)` (violet `#8B7FD6`)** — hors palette verdict (vert/orange/gris/rouge) | ✅ |
| Wording fiche | « potentiel de transformation » ✓, « distinct du verdict » ✓, **0 terme interdit** | ✅ |
| **Coexistence** verdict + mutation | fiche `CP0024` : badge verdict « Opportunité » **ET** bloc « Radar Mutation — Prioritaire 75/100 » côte à côte, sans confusion | ✅ |
| Fiche faible | `ET1719` : bloc « Faible 33/100 » rendu correctement | ✅ |
| Carte (non-régression) | `#map` + canvas Leaflet présents | ✅ |

---

## 4 · Cas UX

| Cas | Attendu | Constat | OK |
|---|---|---|---|
| Parcelle prioritaire | bloc riche (badges + raisons) | OK | ✅ |
| Parcelle faible | bloc sobre, score bas | OK | ✅ |
| Parcelle déjà opportunité | verdict + mutation coexistent | OK | ✅ |
| Parcelle inexistante / erreur API | **bloc masqué**, fiche non cassée | `#mut-block` vide, `.mut-card` absent, `#sheet` intact | ✅ |
| Chargement lent de la liste (~4,7 s) | non bloquant (async sidebar) | app interactive immédiatement, liste se peuple ensuite | ✅ |
| Absence de bloc si erreur | oui | garde anti-course + `catch` → `innerHTML=""` | ✅ |
| Crash de fiche | aucun | aucun | ✅ |
| Erreurs console bloquantes | aucune | **0 exception JS non capturée** | ✅ |

**Erreurs console** : 30 × `net::ERR_CONNECTION_CLOSED` — **toutes** des tuiles de fond de carte
externes `*.basemaps.cartocdn.com` (CDN bloqué par la politique réseau du bac à sable).
**0 échec** touchant l'app locale (`127.0.0.1:8000`), **0 échec** sur `/mutation`.
→ **Environnemental et pré-existant**, sans rapport avec Radar Mutation, **non bloquant**
(le conteneur de carte se monte ; en prod avec réseau, le fond de carte se charge normalement).

---

## 5 · Performance

| Appel | Latence observée | Appréciation |
|---|---|---|
| `GET /mutation/{idu}` (fiche) | **~10 ms** (4 mesures : 10,4 / 10,1 / 10,8 / 10,1) | ✅ excellent — bloc fiche quasi-instantané |
| `GET /mutation` liste `limit=8` | **~4,7 s** (4,74 / 4,73 / 4,81) | ⚠️ lent mais stable |
| `GET /mutation` liste `limit=20` | **4,73 s** | latence **identique** à `limit=8` |

**Analyse** : la latence de la liste est un **coût fixe** (présélection SQL + `bati.stats_batch`
sur le pool de candidats), **indépendant de `limit`**. Elle est **du même ordre que les endpoints
lourds existants** (`/shortlist` 5,8 s, `/map/parcels.geojson` 5,5 s) — ce n'est pas une
aberration. Surtout, la liste est chargée **en asynchrone dans la sidebar** (dans le `Promise.all`
du boot) : elle **ne bloque pas** le rendu ni l'interactivité de l'app.

**Acceptable en V1.** Optimisation V2 recommandée (cf. §9).

---

## 6 · Non-régression

| Vérification | Résultat |
|---|---|
| `node --check app.js` | ✅ syntaxe OK |
| Suites pytest pertinentes (`test_mutation` + `test_mutation_api` + `test_api`) | ✅ **43 passed** (1 warning Starlette pré-existant, hors sujet) |
| `/health` `/healthz` `/readyz` | 200 (2,7 ms / 1,3 ms / 2,2 s) |
| `/stats` `/coverage` `/communes/status` | 200 (832 ms / 220 ms / 2 ms) |
| `/map/parcels.geojson` | 200 (5,5 s, 34 Mo — pré-existant) |
| `/shortlist` | 200 (5,8 s — pré-existant) |
| `/parcels/{idu}` (fiche) + `/enrichment` | 200 (146 ms / 6 ms) |
| `/pipeline/meta` + `/pipeline` | 200 (1,4 ms / 10 ms) |

Aucune régression : tous les endpoints existants répondent 200, les tests passent.

---

## 7 · DB inchangée après QA

| Mesure | Avant QA | Après QA | OK |
|---|---|---|---|
| parcelles | 431 663 | **431 663** | ✅ |
| `parcel_evaluations` | 1 132 371 | **1 132 371** | ✅ (aucune ligne créée) |
| opportunités | 9 103 | **9 103** | ✅ |
| stale | 0 | **0** | ✅ |
| `cascade_results` | — | 8 997 413 | ✅ stable |
| `max(evaluated_at)` | — | 2026-06-27 13:39 (antérieur à la QA) | ✅ aucune écriture |

Endpoints `/mutation` strictement en lecture seule (garanti aussi par le test
`test_mutation_aucune_ecriture_db`). Les suites pytest n'écrivent pas dans la base métier.

---

## 8 · Screenshots

(Fichiers livrés au validateur — non versionnés.)

- `qa2_sidebar.png` — sidebar « Radar Mutation — à surveiller » (8 items, compteur).
- `qa2_fiche_prioritaire.png` — fiche `DM0031` : bloc violet « Prioritaire 100/100 », badges, raisons chiffrées, note prudente.
- `qa2_fiche_coexistence.png` — fiche `CP0024` : **verdict « Opportunité » + bloc « Radar Mutation »** dans la même fiche, sans confusion.

---

## 9 · Anomalies & recommandations

### Bugs bloquants
**Aucun.**

### Bugs importants
**Aucun.**

### Détails mineurs (non bloquants)
1. **Latence liste `/mutation` ~4,7 s** — coût fixe (bati.stats_batch sur candidats). Masquée par le chargement async, mais perceptible si on rouvre la sidebar.
2. **`/mutation?niveau=bidon`** renvoie `200` + liste vide au lieu d'un `422`. Dégradation gracieuse, mais un paramètre invalide pourrait être rejeté explicitement.
3. **`/mutation?niveau=faible`** renvoie `count=0` en prod (présélection biaisée vers le fort potentiel). Voulu, sans impact UI, mais à documenter pour éviter toute surprise d'un futur appelant.

### Recommandations V2 (hors périmètre V1)
- **Pré-calcul / cache du score mutation** (table matérialisée ou cache mémoire) pour ramener la liste sous ~500 ms et permettre un vrai filtrage multi-niveaux.
- **Validation du paramètre `niveau`** (enum → `422` si invalide).
- Les échecs de tuiles `cartocdn` sont **environnementaux** (politique réseau) : aucun correctif Radar Mutation requis.

---

## 10 · Conclusion

> ## ✅ GO
>
> Radar Mutation V1 (moteur + API + UI) est **prêt**. Fonctionnellement correct, sûr (lecture
> seule, DB inchangée), wording prudent respecté, score **distinct du verdict** et clairement
> identifié visuellement (accent violet). **Aucun bug bloquant ni important.** Seul point de
> vigilance non bloquant : la latence de la liste `/mutation` (~4,7 s, asynchrone), à optimiser
> en V2.
>
> **→ Validation humaine requise avant toute suite.**
