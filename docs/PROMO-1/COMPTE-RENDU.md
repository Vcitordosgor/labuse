# PROMO-1 — compte-rendu

Branche `feat/secteur-1` (relie les opérations aux programmes publiés), arbre propre à l'ouverture.
**Un commit de plus. Ne pas merger.** Golden non touché · API + front redémarrés avant recette (preuves :
`docs/PROMO-1/captures/`).

**Doctrine contenu tenue** : on ne stocke et n'affiche QUE des FAITS et un LIEN — **jamais les photos ni
les textes** des promoteurs (droit d'auteur), même règle que le Radar collecté. Grep de recette : aucune
`<img>`, aucun `background-image`, aucune colonne photo/descriptif, aucun visuel externe servi.

---

## P1 — Référentiel programmes (migration)

`src/labuse/promo/tables.py` — table **`programmes`** (idempotente, `ensure_tables`, câblée au heal de
démarrage comme les autres modules) : `promoteur_siren` (si connu), `promoteur_nom`, `nom`, `commune`,
`url` (le lien), `url_portfolio` (provenance), `source`, `annee`, `date_releve`, + le rattachement P3
stocké par les **coordonnées stables** de l'opération (`op_siren`, `op_commune`, `op_annee`,
`rattachement_confiance`, `rattachement_mode`) — les opérations sont recalculées à la volée (union-find),
elles n'ont pas d'id persistant. **Aucune** colonne de texte descriptif ni de photo (garde de test).

## P2 — Collecte assistée (admin)

`src/labuse/promo/collecte.py` + `api/promo.py` + `admin/Programmes.tsx`. L'admin colle l'URL d'un
portfolio → la page est lue (**parseur stdlib `html.parser`, zéro dépendance externe** ; geste admin
ponctuel sur le site propre du promoteur, pas une collecte de portail) → le **modèle** (`ai_models.py`
via `core.complete`, `MODEL_FACTUAL`, jamais en dur) extrait la liste **{nom, commune, url, année}**.
**Anti-invention** : champ absent = null, URL non-http jetée, année bornée ; tout descriptif est **jeté**.
L'appel modèle est **journalisé** (`log.info`/`log.error`, leçon S6) en plus du ledger de `core.complete`.
L'admin **corrige et valide LIGNE À LIGNE** (`/collecter` ne propose ; `/valider` insère, dédoublonne) —
**rien n'entre sans validation**.

## P3 — Rattachement programme ↔ opération

`src/labuse/promo/rattachement.py` — rapprochement par **promoteur (SIREN) + commune + proximité de
période**. Score de confiance en **constantes** : `BASE_SIREN_COMMUNE = 0.6`, `POIDS_PERIODE = 0.4`
(dégressif sur `FENETRE_ANS = 5`), seuil auto `SEUIL_RATTACHEMENT_AUTO = 0.7`. **Sous le seuil, pas de
rattachement automatique** — donc SANS année de programme (0,6 < 0,7) c'est toujours l'admin qui lie
(`/{id}/lier`). Jamais un rattachement **ambigu** (ex æquo de score → abstention). Un programme non
rattaché reste visible sur la page du promoteur, section **« publiés sur leur site »**.

## P4 — Dans l'outil

`veille_promoteurs.py` (`_operations` attache le programme par coordonnées stables ; `promoteur_frise`
porte les noms + la section non-rattachés) + `VeillePromoteurs.tsx`. Une **opération rattachée** affiche
le **nom du programme** + « **voir sur le site de {promoteur} →** » (lien externe). La **frise** du
promoteur porte les noms quand ils existent. **Aucun visuel externe** affiché — un fait + un lien.

---

## Recette réelle (collecte sur 2 promoteurs, clé live locale)

- **CBO Territoria** (`cbo-immobilier.com/programme/974-reunion/1`) → **9 programmes** réunionnais
  extraits (Résidence KALOUPILE · Sainte-Marie · 2022 ; Les Jardins d'Ugo · Saint-Pierre · 2021 ;
  Hamélia · Saint-Leu · *année null* [anti-invention] ; Zirondelles/Zoiseau Blanc/Bengali · Saint-Paul…),
  URLs et années relevées. À la validation : **5 rattachés automatiquement** (Jardins d'Ugo 0,92 ;
  Zirondelles/Zoiseau/Kaisary/Bengali 1,0), 4 restés « publiés sur leur site » (dont Hamélia, sans année).
- **Océanis** (`oceanis.com/lesprogrammes`) → **27 programmes** proposés mais **métropole** (Toulouse,
  Bordeaux, Montpellier…) : l'admin les **dévalide ligne à ligne** (aucun programme réunionnais sur cette
  page) — démontre exactement le « corrige et valide ligne à ligne » et l'honnêteté (rien d'imposé).
- **Une opération rattachée cliquée** ouvre la page du promoteur : capture `01` — l'opération CBO
  TERRITORIA (Saint-Paul, 2024) porte « **Bengali** · voir sur le site de CBO TERRITORIA → » vers
  `cbo-immobilier.com/programme/974-reunion/3-st-paul/10-bengali/`.

Captures : `01` opération rattachée (outil), `02` frise, `03` référentiel admin (rattachement visible),
`04` collecte IA en action (9 propositions éditables). `_report.json` : 0 erreur JS.

## Vérifications

- **tsc** 0 · **vitest** 108/108 · **vite build** OK.
- **pytest** : **2041 passed, 0 failed**, 32 skipped (+9 tests `test_promo.py` : score P3, extraction
  anti-invention P2, parseur stdlib, garde de schéma « aucune colonne texte/photo »).
- **Golden** : **119/119 PASS**, GARDE-RUN OK (431 663/431 663, `q_v11_m137`). **Intact** — 0 fichier de
  scoring touché.
- **Grep doctrine** : zéro image externe servie (front + back), aucune colonne de texte/photo.

## Fichiers

Nouveaux : `src/labuse/promo/__init__.py`, `.../promo/tables.py`, `.../promo/collecte.py`,
`.../promo/rattachement.py`, `src/labuse/api/promo.py`, `frontend/src/components/admin/Programmes.tsx`,
`tests/test_promo.py`, `frontend/qa/promo1_captures.mjs`.
Modifiés : `api/app.py` (heal `promo` + montage routeur), `api/veille_promoteurs.py` (attache programme +
frise), `frontend/src/lib/api.ts`, `.../outils/VeillePromoteurs.tsx`, `.../admin/AdminView.tsx`.
