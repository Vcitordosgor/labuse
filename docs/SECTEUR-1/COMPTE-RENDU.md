# SECTEUR-1 — compte-rendu

Branche `feat/secteur-1` (depuis `origin/main`, arbre propre à l'ouverture). **Un seul commit. Ne pas merger.**
Golden non touché · un seul moteur, rien en dur au front · API + front redémarrés avant recette (preuves : `docs/SECTEUR-1/captures/`).

---

## S1 — Outil « Mon secteur »

Adresse **ou** IDU → les prix du secteur autour de la parcelle. **Aucun calcul parallèle** : réutilise
les moteurs existants.

- Backend `src/labuse/api/mon_secteur.py` — `GET /outils/mon-secteur?idu=` :
  - **Secteur bâti** = `sector_price(db, pid, Hypotheses.charger(commune))` (le moteur de la fiche parcelle) : médiane locale, n, rayon adaptatif 500→1500 m, période, **tendance 12 mois**.
  - **Par type** (maison / appartement / terrain nu) = `_ref_local(...)` (FICHE-COMMUNE-2 C5) + `_dvf_terrain` pour le terrain — chacun porte son **n** et son **millésime**.
  - **Annonces Radar** dans le rayon (biens validés, `badges_pour_biens`) avec prix demandé + écart demandé/acté.
  - Sous le seuil (`SEUIL_N=5`) → **absent, jamais inventé** (terrain nu sort « échantillon insuffisant »).
  - Chaque chiffre porte sa **source** (liste `sources` renvoyée).
- Front `frontend/src/components/outils/MonSecteur.tsx` (`ParcelInput onPick`), enregistré au registre (groupe *marché*, num S1).
- **Recette** : IDU Saint-Denis `97411000AW0735` → bâti **2 209 €/m²** (appartement, 417 ventes, 500 m, 2021–2025, **+9 %**), maison 2 680 €/m² (n=28), appart 2 225 €/m² (n=443), terrain nu absent. Captures `01`, `02`.

## S2 — Page « Contacts institutionnels » (admin)

- Backend `src/labuse/api/ops.py::admin_contacts` — `GET /admin/contacts-institutionnels` (admin-gardé) :
  les **24 mairies** (`mairies`, la **même donnée** que la fiche commune via `mairie_de` — adresse, tel, courriel, site), les **EPCI** (`config/epci_974.yaml` : CINOR, CIREST, TCO, CIVIS, CASUD), la **DEAL** et l'**ADIL** (contacts publics Réunion). **Pas de notes de relation** (le CRM reste dans Notion).
  - Le *service urbanisme* n'est pas porté par la source (service-public.fr) → **absent, jamais inventé**.
- Front `frontend/src/components/admin/Contacts.tsx` — section admin « Contacts », tableau **triable** (commune / téléphone / courriel), filtre plein-texte, blocs EPCI + DEAL/ADIL.
- **Recette** : 24 mairies, 5 EPCI, 2 services (DEAL, ADIL) ; tri par courriel ; « absent » honnête (Saint-Benoît). Captures `08`, `09`.

## S3 — Outil « Veille promoteurs »

**Diagnostic d'abord** (voir plus bas) : l'extraction Sitadel ne porte que rarement le demandeur (SDES ouvert
anonymise les personnes physiques). L'**identité fiable = `parcelle_personne_morale`** (dénomination + SIREN +
groupe MAJIC), le **même SIREN que Scan patrimoine**. → aucune migration nécessaire.

- Backend `src/labuse/api/veille_promoteurs.py` :
  - `GET /outils/veille-promoteurs` — permis (`sitadel_permits`) joints à `parcelle_personne_morale` via `idu_codes` (LATERAL), `WHERE nb_lgt≥1 AND groupe IN (…)`. Catégories : **promoteur** (groupe 0), **bailleur social** (5), **SEM** (6). Filtrable commune / catégorie / période. Plafond 200, « N sur M » affiché, **millésime** montré.
  - `GET /outils/veille-promoteurs/{siren}/acquisitions` — le patrimoine foncier du promoteur (mêmes parcelles PM, par commune). Chiffres = **comptes SQL**.
- Front `frontend/src/components/outils/VeillePromoteurs.tsx` — parcelle **cliquable** (`select`), sous-bloc « ses acquisitions », enregistré au registre (menu **« Veille promoteurs »**, num S3).
- **Recette** : 3 301 permis, promoteurs réels (SIDR bailleur → 4 241 parcelles ; CBO TERRITORIA, MAGGO, SEM). Captures `03`, `04`.

## S4 — Légende des couches en accordéon

`frontend/src/components/map/Legend.tsx` réécrite :

- **Repliée par défaut**, une seule ligne en bas de carte : **« Légende · N couches ▾ »** (N = couches *actives*, pas le nombre de groupes).
- Dépliée : plafonnée à **35 % de la hauteur carte** (`max-h-[35vh]`) avec scroll interne.
- Chaque groupe (Zonage PLU, Équipements BPE, Aléas, Périmètres…) est un **accordéon** : le **premier ouvert**, les autres repliés. Les notes de source vont dans le **« i »** du groupe, jamais dans le corps.
- **Seuls les groupes de couches actives** apparaissent.
- État **replié/déplié + groupe ouvert mémorisé** (`localStorage 'labuse.legende'`).
- **Recette** : « LÉGENDE · 4 COUCHES » repliée ; dépliée = accordéon, groupe « Zonage PLU (par type) » ouvert. Captures `05`, `06`.

## S5 — Dépôt agence visible pour l'admin

- Le bouton **« Déposer une page de résultats »** / bloc « Dépôt agence » apparaît **toujours pour l'admin**, avec la mention **« drapeau fermé — invisible des clients »** quand le drapeau est fermé.
  - Backend `src/labuse/pige/api.py` : `radar_depot_agence_etat` renvoie `{actif, admin:True}` ; `analyser` / `publier` ne sont plus derrière la porte drapeau côté **admin** (la porte `_porte_depot_agence` reste sur l'endpoint **client** `radar_interesse`).
  - Front `frontend/src/components/admin/Radar.tsx` : chip `data-depot-drapeau-ferme`.
- Côté **client**, le dépôt n'apparaît que **drapeau ouvert** (inchangé). Vic peut tester le flux sans toucher la config.
- **Recette** : bloc « Dépôt agence · BÊTA » visible en admin avec le chip « drapeau fermé — invisible des clients ». Capture `07`.

## S6 — Modèle Haiku retiré (bug prod)

**Occurrences des noms de modèles** (toutes recensées ; le fautif `claude-3-5-haiku-20241022` n'existait déjà
**plus** dans le code — il vivait dans l'**env VPS** `LABUSE_AI_MODEL`) :

| Emplacement | Rôle |
|---|---|
| `src/labuse/ai_models.py` | **Source unique** des noms — `MODEL_FACTUAL`, `MODEL_REASONING`, `MODEL_VISION`, `DEFAULT_AGENT_MODEL` + `RETIRED_MODELS` + `check_model()` |
| `src/labuse/ai/core.py` | ré-exporte les constantes (`from ..ai_models import …`), tarifs `PRICE`, défaut `complete()` |
| `src/labuse/config.py` | `ai_model` (défaut = constante) + **validateur** qui refuse un modèle retiré au boot |
| `copilote/interpreteur.py`, `copilote_v2/*`, `pige/extraction.py`, `api/ia.py`, `api/traducteur.py`, `api/assistant.py`, `api/nl_aggregate.py`, `api/banquier.py`, `api/modules.py`, `api/fiche_ask.py` | consomment `core.MODEL_*` (jamais un littéral) |
| `ml/juge_vlm.py` | **était un littéral en dur** `"claude-haiku-4-5-20251001"` → **corrigé** : `MODELE = MODEL_VISION` |

- **Nom actif** : `MODEL_FACTUAL = MODEL_VISION = claude-haiku-4-5-20251001`, `MODEL_REASONING = claude-sonnet-4-6`. Une seule constante de configuration.
- **Cause profonde (le try/except qui avalait l'erreur)** : `ai/core.py::complete()`, `except Exception` (ligne ~458). Il n'appelait que `_note_error` (un bandeau interne) puis renvoyait `degraded=True` **sans aucun log** → le `not_found_error` du modèle mort échouait **en silence** depuis février dans un mode dégradé invisible.
  - **Corrigé** : `log.error("appel modèle %s échoué (kind=%s) : %s: %s", …)` — le modèle et l'erreur sont **toujours** journalisés. `_note_error` nomme désormais la piste « modèle inconnu ou retiré » sur un `not_found`.
  - **Fail-closed** : `config.py` fait échouer le **boot** si `LABUSE_AI_MODEL` est un modèle retiré (message clair) — c'est ce qui aurait empêché la prod de démarrer sur le haiku mort au lieu d'échouer silencieusement à chaque appel.
- **Test garde** `tests/test_ai_models_garde.py` (8 tests) — échoue si :
  - un nom retiré réapparaît **dans le code** (scan source, nomme le fichier fautif) ;
  - un littéral `claude-…` vit **hors `ai_models.py`** (source unique) ;
  - une constante servie est retirée ; `LABUSE_AI_MODEL` retiré au boot ;
  - un échec d'appel modèle **n'est pas journalisé** (vérifie le `log.error` + le bandeau « retiré »).

> Note : pas de clé Anthropic valide en local (VP-003) → l'appel réussi post-correctif se vérifie en prod ; le chemin d'erreur (journalisation + bandeau) est **prouvé par le test** `test_un_echec_d_appel_modele_est_journalise`.

---

## Vérifications

- **tsc** 0 · **vitest** 108/108 · **vite build** OK.
- **pytest** : **2012 passed**, 42 skipped. Les **5 échecs** (`test_front_m2.py`, `test_front_reliquats.py` — vieux HTML kanban/M2) sont **pré-existants** et **branch-indépendants** (prouvé par `git stash` : ils échouent sans mes changements). **Zéro régression.**
- **Golden** : **119/119 PASS**, 0 FAIL, GARDE-RUN OK (431 663/431 663 parcelles, `q_v11_m137`). **Intact** — le mandat ne touche **aucun** fichier de scoring.
- **API + front redémarrés** (uvicorn :8000, build servi sous `/socle/`), recette Playwright → 9 captures `docs/SECTEUR-1/captures/`, **0 erreur JS**.

## Fichiers

Nouveaux : `src/labuse/ai_models.py`, `src/labuse/api/mon_secteur.py`, `src/labuse/api/veille_promoteurs.py`,
`tests/test_ai_models_garde.py`, `frontend/src/components/admin/Contacts.tsx`,
`frontend/src/components/outils/MonSecteur.tsx`, `frontend/src/components/outils/VeillePromoteurs.tsx`,
`frontend/qa/secteur1_captures.mjs`.
Modifiés : `ai/core.py`, `config.py`, `ml/juge_vlm.py`, `api/ops.py`, `api/app.py`, `pige/api.py`,
`frontend/src/lib/api.ts`, `frontend/src/components/admin/AdminView.tsx`, `.../admin/Radar.tsx`,
`.../map/Legend.tsx`, `.../outils/registry.ts`, `.../outils/ModulePanel.tsx`.
