# CHASSE-APP-FIX-2 — rapport

Branche `fix/chasse-app-2` · worktree `~/Desktop/labuse-chasse-app2` · ports 8840 / 6040 · Opus.
Correctifs des défauts relevés par la campagne du 19-20/10 (`CHASSE-APP/CHASSE-APP-20-10.md`).

**Piège d'environnement consigné :** le venv `~/Desktop/labuse/.venv` est en *editable install*
pointant vers `~/Desktop/labuse-main/src`. Lancer l'API avec `PYTHONPATH=…/labuse-chasse-app2/src`
(sinon elle sert le code de `labuse-main`, pas celui du worktree). Front = `labuse-chasse-app2`
directement (Vite). Chaque correctif backend a été rejoué contre le code du worktree.

Chaque constat a été **revérifié contre le code actuel** (main a reçu `fix/chasse-app-1`). Les
constats disparus sont signalés, pas refaits.

## Correctifs (un commit par point, dans l'ordre du mandat)

| # | Point | État | Commit |
|---|---|---|---|
| 1 | **Courrier dit la vérité (C)** — `disponible:false` affiche la `raison` serveur, la ligne de prix n'est plus présentée comme une prestation en cours | corrigé | `af9b1254` |
| 2 | **Adresses barre principale (H)** — l'ordre numérique de `/api/recherche/suggest` était **déjà corrigé par chasse-app-1** (vérifié live : 5<15, 2<12, 1<10). Reste : **doublon `/flash`** supprimé (dédoublonnage `/adresses/autocomplete`) | partiel / corrigé | `b5684338` |
| 3 | **Surface carte CRM (I)** — contenance cadastrale (1 111 m²) au lieu du dessin (1 150). `/flash` était **déjà aligné** par chasse-app-1 (contenance + espace des milliers) | corrigé | `c0114167` |
| 4N | **Projets « 0 ressortent »** — phrase reformulée sur ensemble vide (`748d8172`) PUIS **cause racine** corrigée : le compteur lisait des libellés de tier LEGACY absents des runs v2 → 0 partout ; corrigé via le mapping canonique `codes_stockes` (`68c60612`). Voir vérif pré-merge §2. | corrigé | `748d8172`+`68c60612` |
| 4O | **Projets date de liste** — carte de liste affiche la date du **run servi** (valeurs_run), plus la date du jour (proposee_at) | corrigé | `977beb07` |
| 4P | **Projets étape 5** — « rien n'est retiré » remplacé par la phrase « figeable » de l'étape 4 | corrigé | `a3d5073c` |
| 4R | **Courrier « EY 0109 »** — référence dérivée de l'IDU partout (objet, corps, synthèse, opposition RGPD) | corrigé | `96618556` |
| 4S | **Courrier étape 2** — renommée « Relecture » (décision Vic : renommer, pas de saisie libre) | corrigé | `8dd18ad1` |
| 4T | **Courrier « sur 2023-2025 »** — période réelle des mutations au lieu de « 3 dernières années » | corrigé | `231e02e4` |
| 4S' | **Courrier étape 3** — le retour mène à l'étape précédente (Relecture), plus à l'étape 1 | corrigé | `dc50bf52` |
| 4U | **Copilote** — plus de noms de colonnes (`surface_parcelle_m2`, `zone_plu_famille`) dans la réponse ni la source lisible | corrigé | `02edbeee` |
| 4J | **/flash pied** — « LABUSE ne remplace ni le certificat d'urbanisme… » | corrigé | `b604e932` |
| 5 | **Accessibilité (L)** — « Aucun résultat » en `role="status"` hors du `<ul role="listbox">` (le listbox n'est rendu que s'il y a des propositions) | corrigé | `77da9fa3` |
| 6 | **CRM (Q)** — défile jusqu'à la colonne de destination après déplacement ; la fiche nomme l'étape (« ✓ Dans le CRM · Repérée ») — le déplacer/retirer existait déjà (DA-FIX-5c) | corrigé | `8fc9b78d` |
| 7 | **Radar** — « les portails » → « Leboncoin » ; date de relevé retirée (décision Vic 18/09) | corrigé | `59e2732d` |

Captures avant/après : `docs/audit-2026-10/CHASSE-APP-FIX/captures/`.

## Constats disparus (déjà corrigés par `fix/chasse-app-1`, vérifiés live)

- **Ordre des adresses dans la barre** (`/api/recherche/suggest`) : commit `1b18f639`
  (PARCOURS-EXPERT-19-10 A). Les 3 requêtes du tableau H donnent le bon numéro en tête.
- **Surface `/flash`** : affiche « 1 111 m² » (contenance) + « Dessin du plan : 1 150 m² », espace
  des milliers compris (`_fmt_m2`). Il ne restait donc QUE la carte CRM à aligner.
- **Fiche « Dans le CRM », chemin de retour** : le menu « Déplacer vers… » (déplacer/retirer) est
  déjà présent sur la fiche (DA-FIX-5c). Il manquait seulement l'étape → ajoutée.

---

# Questions (réponses, sans code)

## D — Émetteur du courrier : paramétrable ?

**Oui, le modèle PRÉVOIT un émetteur paramétrable — mais rien dans « Mon compte » ne permet de le
remplir.**

- `expediteur_du_compte(marque, commune)` — `src/labuse/courrier_compose.py:180`. Il lit la
  **marque blanche** du compte : `raison_sociale` (→ société, **défaut « LABUSE »** si vide),
  `signataire`, `coordonnees` (→ téléphone via `_telephone`).
- La signature (`_signature`, `courrier_compose.py:190`) et le pied PDF
  (`_PIED.format(societe=…)`, `api/courrier.py:511`) utilisent cette société. Si la marque porte une
  raison sociale, le courrier part **au nom du client** ; sinon il retombe sur « LABUSE » — ce que
  l'audit a vu.
- Stockage : colonne `comptes.marque` (JSONB) — `src/labuse/marque.py:26` ; lue par
  `_marque_du_compte()` — `api/courrier.py:441` ; injectée dans `composer(…, marque=…)`.

**Donc :** l'émetteur est paramétrable **côté données** (`comptes.marque.raison_sociale` /
`signataire` / `coordonnees`), mais **aucun écran « Mon compte » ne l'expose** — d'où l'impossibilité
pour le client de mettre son nom. Décision/UI pour toi : exposer ces champs de marque dans « Mon
compte », ou assumer l'adressage « pour le compte de LABUSE » et l'écrire sur l'écran d'envoi.

## M — Radar : 0 rattachement sur 110 biens ? 149 vs 110 ?

**0 rattachement — conforme aux décisions, pas un bug de calcul.**

- Base : `pige_biens` = **352 lignes, 0 avec `idu`** (aucun bien rattaché dans toute la table).
- Le rattachement n'est « Sourcé » (idu posé) qu'à **confiance forte** : GPS 0,95 ou BAN 0,75-0,90
  (`src/labuse/pige/rattachement.py:83-95`). DPE/morphologie (0,40-0,65) ne donnent que des
  **candidats « Estimé »** (idu = None, pistes listées), jamais un rattachement automatique.
- **Radar est gelé depuis le 06/10** : les jobs `radar-cycle`, `radar-cycle-dvf`, `radar-cloche`,
  `radar-cycle-mensuel` portent `gel="Phase 8 Stéphanie"` (`src/labuse/jobs.py:471-499`, posé au
  commit `3a906ea2` du 06/10 — cf. [[crons-prod-fix-1]]). Le cycle de rattachement ne tourne pas.
- **Conclusion :** n_rattaches = 0 parce que (a) le cycle de rattachement est gelé et (b) aucun bien
  n'a de géoloc/adresse produisant un « Sourcé ». C'est le comportement voulu (rattachement à
  confiance forte seulement, dégel = geste prod). Rien à corriger dans le code.
- *Note code :* `rattachement.py` **n'exclut pas** explicitement les terrains de l'auto-rattachement
  (Sourcé GPS/BAN s'applique à tous les types). La règle « pas de rattachement automatique des
  terrains » est donc une **décision** non matérialisée dans ce chemin — à confirmer si elle doit
  l'être (hors scope ici).

**149 vs 110 — oui, c'est la règle « collecte totale, service filtré ».**

- `b.est_copro = false` (`src/labuse/pige/client.py:35`) : les **appartements (copropriété) sont
  collectés et comptés par type, mais jamais servis** comme annonces. `biens_en_vente` (compte
  canonique servi) = terrain + maison ; `par_type` (stats marché) inclut les appartements → la somme
  par type dépasse le compte servi. (Sur la base locale aujourd'hui : servi 70 = 6 terrains + 63
  maisons ; par_type ajoute 33 appartements = 102.) **C'est voulu.**
- *Libellé juste proposé (sans le coder) :* la colonne Marché le dit déjà honnêtement
  (« Les appartements comptent dans les chiffres mais ne sont pas listés. »,
  `RadarMarcheColonne.tsx:203`). Pour l'écran Radar lui-même, une ligne du type
  **« N biens en vente servis (hors copropriété) — dont K terrains »** lèverait l'ambiguïté entre le
  compte servi et la somme par type. Les 8 terrains sur 110 (maigre pour des chasseurs de foncier)
  gagneraient aussi à être affichés en clair plutôt que découverts.

**Corrigé (autorisé par le mandat) :** « les portails » → « Leboncoin » (seule source servie) ;
**aucune date de relevé** affichée (« dernière capture le … » retirée de la colonne Marché, décision
Vic 18/09).

## Fiche à 9,1 s — qu'est-ce qui est attendu avant le premier affichage ?

**Le premier affichage (identité + les 6 tuiles SURFACE/ZONE/PENTE/EXPOSITION/RISQUES/SDP + le nom
du Secteur) est bloqué par UNE requête : `getFiche` → `GET /parcels/{idu}?source=q_v19`**
(`frontend/src/lib/api.ts:439` ; endpoint `parcel_fiche`, `src/labuse/api/app.py:6658`, qui sert la
fiche premium `_q_v2_fiche`). Tout le reste (faisabilité, gabarit, pipeline, projets, veille,
exposition, dossier) est **secondaire** : ces requêtes sont `enabled` après l'arrivée de la fiche
(`Fiche.tsx:568-569`, `enabled: !!f`) ou à l'ouverture d'un menu — elles ne retardent pas le premier
paint.

**Mesure locale (worktree, base Mac) :** `/parcels/{idu}?source=q_v19` répond en **6-11 ms**,
`/modules/faisabilite/{idu}` en 4-12 ms. **Les 9,1 s ne se reproduisent pas ici** — c'est une latence
**côté serveur prod**, pas une attente front structurelle.

Pistes (le code lui-même les désigne) : la fiche premium est un **bundle d'une cinquantaine de
requêtes**, dont **2 sondes `dryrun_parcel_evaluations` lentes** (plan générique → 60-180 ms chacune,
cf. commentaire `app.py:3213`). Sur prod (cache froid, plan générique, base plus grosse) elles
s'empilent. **Prochain pas pour localiser :** `parcel_fiche` accepte un paramètre `trace=1`
(`app.py:6660`) — appeler `/parcels/{idu}?source=q_v19&trace=1` sur prod donne le détail par requête
et pointera la ou les requêtes responsables des 9,1 s.

---

---

# Vérifications pré-merge (demandées) — et correctif de fond du compteur

## 1. « valeurs au » : figé ou en direct ? → EN DIRECT, le commit O reste

Un projet **n'est pas figé** sur sa date. Les **décidées** (retenue/écartée) sont stockées ; les
**proposées** (le vivier classé qui porte les « valeurs ») sont *« servies EN DIRECT »* sur le run
SERVI courant (`projets.py:1104`, scoring `_score_v2_run_id`). `proposee_at` est l'horodatage du
**cache de total de cadrage**, réécrit à `now()` à **chaque ouverture** (`projets.py:1152`) — pas une
date de valeurs. Le projet ouvert affiche déjà `valeurs_run` (le run servi) : le commit O
(`977beb07`) ne fait qu'aligner la liste dessus. **Conservé.**

## 2. « ressortent » = 0 partout — CAUSE RACINE : bug de libellé de tier (corrigé en profondeur)

Oui, 0 sur **tous** les projets — mais **pas** parce que le run ne classe rien : q_v19 classe
**142 Priorité + 662 À suivre** (île). `_analyse_cadrage` filtrait `tier = 'brulante'/'chaude'` EN
DUR (libellés LEGACY absents des runs v2, qui stockent `'priorite'/'a_suivre'`).

**Correctif de fond (`68c60612`)** — par le **mapping canonique** `codes_stockes(palier)` (legacy + v2,
suit `PRIORITE_SERVIE`), plus de libellé en dur. Appliqué à `_analyse_cadrage` (bandeau) **et à
`_restant_a_trier`** (chips) — moitié couplée du **même** compteur R8, sinon les chips restaient faux
sur v2 et le test verrouillait un bug. `test_r8` recalé sur la sémantique repliée + **nouvelle garde**
`test_r8_compteur_voit_les_tiers_v2_du_run_servi` (sème des tiers v2 → échoue sur l'ancien code,
`signalees=0` ; passe sur le correctif). Résultat : projet 238 « 7 ressortent » (était 0). Ma
reformulation N (`748d8172`) reste : phrase d'origine en cas normal, « aucune ne se détache » seulement
si le vrai compte vaut 0. Captures `N2-bandeau-compteur-{avant,apres}.png`.

### Autres endroits lisant 'brulante'/'chaude' (listés, NON corrigés)

**Sûrs — gèrent les DEUX vocabulaires (legacy + v2), aucune action :**
- `golden_ops.py:41` (`_promues` additionne brulante/chaude **+ priorite/a_suivre**)
- `verdict_servi.py:31` (`TIERS_SERVABLES` inclut les deux)
- `veille_plu.py:175` (`_TIERS_SURSIS` inclut les deux)
- `demo.py:116,175` ; `shortlist.py:188` (`_action_defaut`) ; `filtres/sources.py:810`
- `registre/moteurs/plateforme.py:bascules_tiers_hauts` — la **SQL** inclut `'priorite','a_suivre'`
  (seule la docstring/`n_bascules_7j.py` dit « {brûlante, chaude} »)

**À surveiller — mappés/clés sur les codes LEGACY seuls (même classe de bug possible) :**
- `copilote_v2/outils.py:52` `_TIER_ALIAS` : facette Copilote « opportunités/brûlante/chaude » →
  `'brulante,chaude'`. Correct **si** `mvt_parcels.tier_v2` stocke du legacy (table MVT, vocabulaire à
  confirmer) ; sinon la facette par tier ne matcherait aucune tête sur un run v2.
- `shortlist.py:22` `verdict_base = {brulante:120, chaude:120, …}` : poids de figement **clés sur les
  tiers legacy** ; un run v2 (`priorite/a_suivre`) retomberait sur le défaut. À vérifier à l'usage.

*(Faux positifs du grep, non pertinents : `cli.py` q_chaude/a_chaude = params de calibrage ;
`models.py` colonne/commentaires ; `exports/miroir.py` « eau chaude solaire » ; prompts LLM
`copilote_v2/answering.py`.)*

---

## Tests & vérifs

- `tsc -b` vert à chaque étape ; `vitest` front 198/198 (+ crm/fiche 32/32).
- Back : `test_adresses_autocomplete` 7/7 (+ garde dédoublonnage), copilote/resume_fiche 148 passed.
- Chaque correctif rejoué live (curl / navigateur piloté) contre le code du worktree.
