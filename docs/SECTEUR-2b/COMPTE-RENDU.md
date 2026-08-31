# SECTEUR-2b — compte-rendu

Branche `feat/secteur-1` (approfondit la couche VEFA + déplace le dépôt côté app), arbre propre à
l'ouverture. **Un commit de plus. Ne pas merger.** Golden non touché · API + front redémarrés avant
recette (preuves : `docs/SECTEUR-2b/captures/`).

---

## U1 — Diagnostic d'abord : ce que DVF porte sur le VEFA au 974

Inventaire rendu **avant de coder** (mesuré sur la base réelle) :

- **Champs DVF présents** pour le VEFA : `type_local` (appartement/maison — quasi 100 % appartements, le
  VEFA neuf est collectif) et `surface_reelle_bati` (souvent, pas toujours peuplée).
- **Champ ABSENT** : le **nombre de pièces** — il n'existe dans **aucune** table DVF au 974 (ni colonne,
  ni `raw` : `raw` VEFA = `{vefa, source, id_mutation}`). → la **médiane par taille T2/T3/T4 est
  impossible** (absence honnête, jamais extrapolée). Garde de test `test_pieces_absentes_de_dvf_au_974`.
- **ECLN** (SDES) = métropole seule, N/A DOM → aucun **stock**/écoulement servi.
- **Sitadel en face** = l'**offre engagée** (logements collectifs autorisés) = ce qui arrive.

**Tableau — VEFA acté (36 mois, prix calculable) vs offre Sitadel (24 mois), par commune :**

| Commune | n VEFA (prix) | médiane €/m² | couche | Sitadel lgt collectifs (permis) |
|---|---:|---:|:--|---:|
| Saint-Denis | 112 | 5 850 | **peinte** | 440 (57) |
| Saint-Paul | 82 | 5 003 | **peinte** | 658 (74) |
| Le Tampon | 24 | 5 017 | **peinte** | 455 (70) |
| Saint-Pierre | 23 | 5 524 | **peinte** | 615 (98) |
| Saint-Leu | 22 | 5 146 | **peinte** | 50 (19) |
| La Possession | 18 | 4 169 | **peinte** | 148 (26) |
| L'Étang-Salé | 11 | 4 796 | **peinte** | 274 (31) |
| Petite-Île | 9 | (5 353) | hachurée | 91 (22) |
| Sainte-Marie | 5 | — | hachurée | 530 (30) |
| Saint-Benoît | 0 | — | hachurée | 499 (45) |
| Saint-Louis | 0 | — | hachurée | 365 (68) |
| Sainte-Suzanne | 0 | — | hachurée | 238 (20) |
| … (17 communes sous le seuil) | | | hachurées | |

**7 communes peintes** (≥ 10 ventes VEFA avec prix, 36 mois), **17 hachurées**. Le diagnostic révèle des
communes à **gros pipeline mais peu de ventes actées** (Sainte-Marie 530, Saint-Benoît 499, Saint-Louis
365) — d'où l'intérêt de servir l'**offre engagée** à côté du prix acté.

## U1 — La couche : creuser, pas seulement peindre

`ingestion/vefa_neuf.py` réécrit + `api/vefa.py` + `MapView`/`Legend`/`VefaDetail` :

- **Fenêtre 36 mois** (constante `FENETRE_MOIS = 36`, dans le « i »). Recompte : **7 peintes / 24**.
- **Couleurs** : rampe séquentielle **distincte jaune → orange → magenta** (fini le camaïeu de vert sur
  la carte verte), 5 tranches €/m² avec **légende chiffrée** ; **hors du vert des statuts**. Communes
  **sous le seuil de 10 ventes** : aplat gris muet + **hachure grise** (`ov-vefa_neuf-trame`) + « moins de
  10 ventes » dans le « i » — **jamais vides**. Le seuil ne bouge pas.
- **Clic sur une commune → panneau de détail** (`VefaDetail`, `GET /outils/vefa-neuf/{ref}`), tout depuis
  les moteurs existants, **chaque chiffre avec son n** : médiane €/m² VEFA (36 mois) + n, **tendance 12
  mois** (pivot sur la dernière vente, honnête sur un millésime en retard ; absente si n < 5), répartition
  **appartements/maisons**, **offre engagée Sitadel** (24 mois), lien « fiche commune → ».
- **Médiane par taille (T2/T3/T4)** : **absente** — le nombre de pièces n'est pas porté par DVF au 974
  (dit dans le panneau, jamais extrapolé). Sous le seuil par segment : le chiffre est absent.

Captures `01` (rampe + légende + hachures), `02` (panneau de détail — Sainte-Suzanne, hachurée : « moins
de 10 ventes », pièces absentes dites, **offre engagée 238 logements**, lien fiche commune).

## U2 — Publier une annonce : côté client (dans l'app)

Le parcours de dépôt (4 étapes de RADAR-VEILLE-1, composant `components/radar/DepotAgence.tsx`) **vit
désormais dans l'écran Radar de l'APP**, plus dans la Tour de contrôle (retiré de `admin/Radar.tsx`).

- **Drapeau fermé** → bouton « **+ Publier une annonce** » visible **admin seulement** dans l'en-tête du
  Radar, mention « **drapeau fermé — invisible des clients** » ; le parcours se **déroule là, dans l'app**.
- **Drapeau ouvert** → le **même bouton apparaît pour les clients** (état PUBLIC `GET /radar/depot-agence/
  ouvert`), même parcours. Le backend : `_depot_admin_ou_ouvert` = admin (toujours) OU drapeau ouvert ;
  drapeau fermé + non-admin → 404 (le client ne voit ni n'atteint rien). Rien d'autre à changer.
- Visibilité front : `boutonVisible = estAdmin || ouvert` ; mention `drapeauFerme = estAdmin && !ouvert`.

**Recette** : parcours complet **depuis l'app en admin**, les 4 étapes — `03` étape 1 (coller le HTML +
mention drapeau fermé), `04` étape 2 (annonce reconstruite, 35 records de l'échantillon), `05` étape 3
(adresse + parcelle rattachée + agence), `06` étape 4 (**publiée — bien #… parcelle 97411000AW0735**).
**Absence du bouton côté client, drapeau fermé** : `ouvert = false` (endpoint public) → pour un client
(`estAdmin=false`) le bouton est masqué ; en dev l'auth est bypassée (tout le monde = admin), la garde
réelle est le rideau de production (`exiger_admin`) + le drapeau.

---

## Vérifications

- **tsc** 0 · **vitest** 108/108 · **vite build** OK.
- **pytest** : **2033 passed, 0 failed** (+5 `test_vefa_neuf.py` : fenêtre 36 mois, toutes communes
  peintes/hachurées jamais vides, pièces absentes jamais extrapolées). Les skips (45) sont les tests
  « base applicative » qui exigent l'API up pendant la suite — inchangé, non lié à ce mandat.
- **Golden** : **119/119 PASS**, GARDE-RUN OK (431 663/431 663, `q_v11_m137`). **Intact** — 0 fichier de
  scoring touché.
- **API + front redémarrés** (uvicorn :8000, build sous `/socle/`) ; 6 captures, **0 erreur JS**.

## Fichiers

Nouveaux : `src/labuse/api/vefa.py`, `frontend/src/components/map/VefaDetail.tsx`,
`frontend/src/components/radar/DepotAgence.tsx`, `tests/test_vefa_neuf.py`,
`frontend/qa/secteur2b_captures.mjs`.
Modifiés : `ingestion/vefa_neuf.py` (36 mois + toutes communes + `detail_commune`), `pige/api.py`
(endpoint public `ouvert` + gate `admin OU ouvert`), `api/app.py` (montage routeur vefa),
`frontend/src/lib/api.ts`, `.../map/MapView.tsx` (rampe + hachure + clic), `.../map/Legend.tsx`,
`.../lib/layers.ts`, `.../store/useApp.ts`, `.../outils/RadarView.tsx` (dépôt dans l'app),
`.../admin/Radar.tsx` (dépôt retiré de la Tour de contrôle).
