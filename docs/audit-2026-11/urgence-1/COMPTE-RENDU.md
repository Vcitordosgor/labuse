# URGENCE-1 — compte-rendu

- **Branche** : `fix/urgence-1` · worktree `~/Desktop/labuse-urgence` · ports 9110/6310.
- **Portée** : les huit points du mandat, rien d'autre. Aucun merge, aucun accès prod.
- **Registre source lu avant correction** : `docs/audit-2026-11/nu-1/{A,D,E,F}/RAPPORT.md`
  (commits `32777671b`, `4df48eadd`, `914fff1d7`, `a533aefd6` — lus, non mergés).
- **Merge = geste de Vic.**

## Décisions de cadrage (Vic)

1. **Point 1 — NU-D-017 (Blocs fonciers RGPD) : RETIRÉ du mandat par Vic.** Aucun masquage de noms,
   aucun retrait de CSV, ni dans Blocs fonciers, ni dans Scan patrimoine, ni dans Prospection solaire,
   ni dans Projets. **Rien touché de ce côté.**
2. **NU-F-023 (/moi role/statut_compte) : SKIP (décision Vic).** La trouvaille suppose ces champs
   « inutiles », mais dans l'arbre courant ils sont **lus par le front** : `role === 'admin'` garde
   l'UI admin (Rail, AdminView, VeillePromoteurs, ContextePanel) et `statut_compte === 'paiement_requis'`
   pilote le bandeau de paiement (App.tsx). Les retirer verbatim serait une régression → non touché.

## Les sept points traités

### 1. SSRF — NU-F-004 (Estimer un bien) + NU-F-007 (dépôt agence)
- **NU-F-004** : `POST /radar/annonce/analyser` (`src/labuse/pige/api.py`) **ne fait plus de repli
  `_fetch_page_oneshot`**. Un bien absent du Radar renvoie le **message existant** (`url_bloquee`,
  phrase imposée côté front) **sans aucune requête sortante**. Le PDF `GET /analyse-annonce.pdf?url=`
  (`documents.py`) délègue à cette route → hérite du correctif.
- **NU-F-007** : `_fetch_page_oneshot` (seul appelant restant = dépôt agence) est durci —
  `_valider_cible()` exige un **schéma http(s)**, un **hôte d'une liste blanche de portails**
  (`leboncoin.fr`, `seloger.com`, `pap.fr`, `logic-immo.com`, `bienici.com`, dérivée de `portails.py`)
  et **jamais une adresse privée/interne** (`_resout_public` rejette loopback/lien-local/RFC1918/
  réservé/multicast). Les **redirections ne sont plus suivies** (`allow_redirects=False`) → un 3xx ne
  peut pas échapper à la liste blanche.
- **Garde légal** : `test_pige_socle` reste VERT. `_fetch_page_oneshot` reste un **one-shot sans boucle
  ni retry** (aucun `for/while` avec `.get(` dans la fonction), import `requests` confiné localement.
- **Fichiers** : `src/labuse/pige/api.py`.

### 2. Fuites de l'interne — NU-F-002 / NU-A-009
- **NU-F-002** (Copilote) : `fiche_parcelle` n'embarque **plus** de `verdict` (le repli lisait le `tier`
  brut `sans_signal`/`a_creuser`… jamais traduit). `_substance()` ne ré-imprime plus « verdict LABUSE :
  … ». Vocabulaire client gravé seulement : le palier ne reste accessible que par la voie dédiée
  (`resume_fiche` → `verdict_potentiel`, une phrase client). `outils.py`, `answering.py`.
- **NU-A-009** (fiche) : `ScoreV2Block` reçoit `montreRang` et masque **percentile + rang bruts** sauf
  tier **actionnable** (priorité / à suivre), derrière la **même condition** que le verdict d'en-tête
  (`montreMultiple`). `ScoreV2Block.tsx`, `Fiche.tsx`.

### 3. NU-E-049 — payload fiche_parcelle du Copilote
- Même correctif que NU-F-002 : `fiche_parcelle` est un outil **factuel** (commune/surface/zone) et
  n'embarque plus le verdict de scoring quand il n'est pas demandé. `outils.py` (clé `verdict` retirée,
  `sv2` plus lu), description du catalogue mise à jour. `answering.py`.

### 4. NU-F-026 / NU-F-028 — identifiants internes
- **NU-F-026** : `resume_fiche.tuiles[].id` et `resume_fiche.sections[].id` (ids de registre
  `surface_parcelle_m2`, `pente_deg`…) **ne sont plus sérialisés** (non lus, ni par le front ni par
  `phrase()`). `resume_fiche.py` + type `frontend/src/lib/api.ts`.
- **NU-F-028** : le message d'erreur d'étiquette CRM joint désormais les **libellés** client
  (`CONTACT_ETIQUETTES.values()`), jamais les clés internes snake_case. `src/labuse/api/app.py`.

### 5. NU-F-018 — liens des mails
- `config.exiger_base_url_publique()` (nouveau) : **fail-closed** — lève si l'URL de base est absente/
  vide ou localhost. Appelé en tête des deux chemins d'envoi digest (`events.envoyer_digests`,
  `pige.digests.envoyer`) hors `dry_run`. `LABUSE_PUBLIC_BASE_URL` est donc **obligatoire** pour
  envoyer ; en prod le défaut est `https://app.labuse.immo`. `config.py`, `events.py`, `pige/digests.py`.
- **Test qui échoue si la variable manque** : `tests/test_mail_base_url_obligatoire.py`.

### 6. Décision 5 / NU-E-012 — « valeur créée »
- Déjà **interne** : `valeur_creee_eur` (CA brut sans coût, jusqu'à ~878 M€) n'apparaît sur **aucune**
  surface client — vérifié sur `api/`, `exports/`, `copilote_v2/`, `frontend/src` et le dict `score_v2`
  servi (`tier`/`rang`/`label`/`motif`/`percentile` seulement). Elle reste libre dans le module de
  calcul `scoring/p_v2/` et l'outillage CLI admin. **Garde** : `tests/test_valeur_creee_interne.py`
  échoue si une surface client la nomme.

## Recette

- **Hook backend** : famille unitaire `not db` = **2768 passed** (1 échec `test_boot_verrou_1::
  test_boot_sans_verrou_sur_tables_chaudes` **pré-existant & environnemental** : `failed to resolve host
  'None'` — base applicative non configurée dans ce shell ; **échoue à l'identique sur `main` propre
  `dfc01dd33`**, non lié au diff). DB ciblée des zones touchées = **60 passed** (pige/annonce/dépôt/
  digests/veille/cloisonnement/scoring3/socle).
- **Tests neufs** : `test_mail_base_url_obligatoire.py` (6), `test_ssrf_depot_agence.py` (5),
  `test_valeur_creee_interne.py` (1) ; `test_annonce_lien.py` reciblé (le fetch-repli retiré devient une
  garde SSRF : `_fetch_page_oneshot` absent de `radar_annonce_analyser`).
- **Front** : `tsc -b` **OK** · `vitest run` **305 passed (64 fichiers)** · `vite build` **OK**
  (worktree : `npm ci` RÉEL — le symlink `node_modules` casse maplibre sous Vitest, cf. mémoire).
- **Captures** (`captures/`) :
  - `ssrf-lien-inconnu.txt` — curl : lien Leboncoin inconnu du Radar → `{"ok":false,"erreur":"url_bloquee"}`
    + journal serveur « aucun fetch (SSRF fermé) » ; dépôt agence sur `169.254.169.254` / `10.0.0.5` /
    hôte non-portail → refusés sans requête.
  - `mail-lien-correct.txt` — digest rendu avec `https://app.labuse.immo/socle/#idu=…` + liens désabo/
    préférences ; preuve fail-closed (localhost/vide refusés).
  - `copilote-payload.txt` — `fiche_parcelle.data` = `[commune, etage0, idu, surface_m2, zone]` (plus de
    `verdict`) ; `_substance` sans « verdict LABUSE » ; `resume_fiche` sans ids.
  - `fiche-rang-percentile.txt` — diff du garde `montreRang` (ScoreV2Block/Fiche).

*Recette jouée le 2026-10-31. Branche `fix/urgence-1`, commit sur la branche, pas de merge, pas de
push. Uvicorn 9110 arrêté. Merge = geste de Vic.*
