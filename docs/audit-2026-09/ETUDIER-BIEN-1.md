# ETUDIER-BIEN-1 — L'outil « Étudier un bien » fait-il doublon avec la fiche parcelle ?

**Mandat.** Vic : l'outil « Étudier un bien » semble redire la fiche parcelle. S'il ne porte rien
d'unique → on le supprime. S'il porte quelque chose d'unique → on le déplace dans la fiche et on le
supprime quand même. Ce rapport **établit le fait, il ne décide pas.**

**Cadre.** Lecture seule. Aucune modification de code, aucun merge. Branche `audit/etudier-bien-1`
depuis `main` (`a5c905a0`), worktree `~/Desktop/labuse-etudier`.

---

## 0. Étape 0 — état

- `pwd` = `~/Desktop/labuse-etudier`, branche `audit/etudier-bien-1`, base `a5c905a0` (= `main`), arbre propre. ✅

---

## Ce qu'est l'outil (rappel de plomberie)

« Étudier un bien » (`EtudierBien.tsx`, clé module `scoreur-adresse`) est **une fusion** de trois
briques préexistantes, pas un moteur neuf :

1. **Écran « Prix du secteur »** = le composant `SecteurResultats` (de `MonSecteur.tsx`, l'outil
   « Mon secteur », retiré du menu mais résolvant). Endpoint `GET /outils/mon-secteur`.
2. **Écran « Ce que porte la parcelle »** = l'endpoint `POST /scoreur-adresse` (constat servi).
3. **Analyse d'opération** (2ᵉ niveau, sur clic) = le composant `<Calculette>` **importé de
   `Fiche.tsx`** + `compute_bilan_servi` — strictement le moteur de la fiche.

Fait structurant : l'outil **appelle `getFiche` lui-même** (`EtudierBien.tsx:80`) pour son alerte de
cohérence, et **rouvre la fiche / la faisabilité / l'assemblage** par des portes. Il vit sur les
mêmes tables et les mêmes fonctions que la fiche.

---

## 1. Comparaison champ par champ

Colonnes : information affichée · présente dans la fiche ? (section) · même source & même calcul ?

### Écran 1 — « Prix du secteur » (`SecteurResultats` → `/outils/mon-secteur`)

| Information (outil) | Dans la fiche ? | Même source / même calcul ? |
|---|---|---|
| **Prix du secteur — bâti** (médiane €/m²) | **Oui** — §Marché « Prix de sortie — bâti secteur » | **Identique.** `mon_secteur.py:79` appelle `sector_price(...)`. La fiche passe par `marche_service.marche_dvf(profil=DVF_BANQUIER_ADAPTATIF)` qui, à `marche_service.py:132-135`, **appelle littéralement la même fonction `sector_price`**. Même médiane, mêmes q1/q3, même dédoublonnage par `mutation_id`. |
| **Rayon** (adaptatif 500→1500 m / repli commune) | **Oui** — même FactNote (« … ≤ X m (rayon adaptatif) ») | Identique (champ `radius_m` du même `sector_price`). |
| **Ventes (n)** + **période** | **Oui** (n dans la FactNote) | Identique (n de `sector_price`). La *période* [min–max] est affichée en clair dans l'outil, seulement implicite dans la fiche. |
| **Tendance 12 m** (`%` + mot) | **Oui** — FactNote « … · tendance X » (conditionnel) | Identique (`tendance_pct`/`tendance` du même `sector_price`). L'outil la met en case dédiée, la fiche en fin de note. |
| **Écart avec la commune entière** (« sous / au-dessus de la commune », `%`) | **Non** | Calcul propre à l'outil : `_dvf_bati(db, commune)` (médiane bâti commune) confrontée à la médiane secteur (`mon_secteur.py:84-95`). La fiche ne porte qu'une **porte** « Voir le marché de la commune », aucun écart chiffré secteur↔commune. |
| **Détail par type — Maison / Appartement** (médiane mono-type au rayon) | **Non** | `_ref_local(db, idu, 'maison'/'appartement')` (`mon_secteur.py:108-109`), rayon adaptatif, toutes années. La fiche ne montre jamais un split maison-vs-appartement du secteur (elle sert du bâti multi-type + du terrain). |
| **Détail par type — Terrain nu** (médiane €/m²) | **Oui, mais** — §Marché sert un « terrain nu secteur » (valeur d'en-tête + « Valeur au prix du secteur ») | **DIFFÉRENT.** Outil = `_terrain_local` : rayon **géographique** adaptatif 500→1500 m, trim 5 % (`mon_secteur.py:25-50`). Fiche = table pré-calculée `dvf_secteur_medianes` clé **`substring(idu,1,10)` = SECTION CADASTRALE** (unité administrative fixe, fenêtre « ventes 2021-2025 ») (`app.py:3811-3812`). Deux méthodes, deux chiffres possibles. |
| **Annonces Radar dans le rayon** (liste, distance, écart) | **Oui, mais** — §Marché « Annonces Radar » | **DIFFÉRENT (portée).** Outil = toutes les annonces actives **dans 1500 m** (`ST_DWithin … 1500`, LIMIT 30, `mon_secteur.py:119-129`). Fiche = seulement les annonces **rattachées à CETTE parcelle** (`b.idu = :idu`). Même libellé « Annonces Radar », population différente. |
| **Note de méthode / distribution** (« N ventes → N retenues · extrêmes exclus · plage ») | **Non** (donnée présente dans le payload fiche, jamais rendue) | Même donnée (`distribution` de `sector_price`) ; seul l'outil la dessine. |

### Écran 2 — « Ce que porte la parcelle » (`POST /scoreur-adresse`, `_constat_servi`)

| Information (outil) | Dans la fiche ? | Même source / même calcul ? |
|---|---|---|
| **Surface habitable constructible** (SHAB vendable, « Estimé ») | **Oui** — §Constructibilité + `potentiel_transformation` | Même moteur : `parcel_faisabilite(...).fourchette` (`scoreur.py:203`). C'est la capacité de la fiche. |
| **Terrain m²** (« Sourcé ») | **Oui** — §Identité | Identique (`parcels.surface_m2`). |
| **Prix de sortie du neuf dans le secteur** (« Estimé ») | **Oui, mais** — §Marché « Neuf (VEFA) — commune » | **DIFFÉRENT (grain).** Outil = `resolve_prix_sortie_servi` (cascade override_bassin → secteur → commune → île, `scoreur.py:211`). Fiche = VEFA au grain **commune**. Même concept « prix du neuf », résolution différente. |
| **Terrain nu dans la zone** (€/m², DVF terrains, fiabilité) | **Oui** — §Foncier `prix_terrain_nu.par_zone` | **Identique** (point de calcul unique `prix_terrain_nu_zone` / `ligne2_terrain_zone`, segmenté par famille de zone U/AU). `scoreur.py:202`. |
| **Dernières ventes de cette parcelle** (jusqu'à 6, date/prix/surface) | **Oui, partiellement** — §Identité `DerniereVenteBlock` (la **dernière** mutation) | Même table `dvf_mutations_parcelle` (`scoreur.py:181-192`). L'outil sert l'historique (6 lignes) là où la fiche ne montre que la dernière vente. Même donnée, profondeur d'affichage différente. |
| **Alerte de cohérence** (résiduel bâti < SHAB vendable) | **Dérivée de la fiche** | Aucune source neuve : lit `getFiche().potentiel_transformation.sdp_residuelle_m2` (le même « Un lot » de Pièges & risques) et le compare à la SHAB. Cadrage propre à l'outil, données 100 % fiche. |

### Écran 2 bis — « Analyse d'une opération » (2ᵉ niveau)

| Information (outil) | Dans la fiche ? | Même source / même calcul ? |
|---|---|---|
| **Charge foncière** (calibrée LABUSE / vos hypothèses), **CA visé**, **écart au prix demandé** | **Oui** — le composant `<Calculette>` est **importé de `Fiche.tsx`** | Identique (`compute_bilan_servi`). L'unique apport propre = la saisie manuelle « prix demandé » + l'écart affiché — cadrage, pas moteur. |

### Boutons / portes

| Bouton (outil) | Équivalent fiche ? |
|---|---|
| Ouvrir la fiche complète → | pointeur vers la fiche |
| Faisabilité détaillée → (M22) | la fiche offre la même porte |
| Assembler avec les voisines → | la fiche §Marché offre « Comparer » (assemblage : porte propre à l'outil, mineur) |

### L'entrée par adresse (candidat explicite du mandat)

**Existe déjà.** La **barre de recherche globale de l'en-tête** (`Header.tsx:108`) accepte une adresse,
la résout via BAN → IDU (`ST_Contains`), puis `select(idu)` → **ouvre la fiche directement**. Le
`ParcelInput` de l'outil est le même patron omnibox, réutilisé partout (Rail, Taxe, Veille…). L'entrée
par adresse → fiche **n'est pas unique à l'outil**.

---

## 2. Verdict factuel

### (a) En DOUBLE avec la fiche (même source, même calcul)

- **Bâti secteur** : médiane €/m² + rayon adaptatif + n + tendance 12 m — **la même fonction
  `sector_price`** des deux côtés (prouvé : `marche_service.py:132-135`).
- **Terrain nu de la zone** — même point de calcul unique `prix_terrain_nu_zone`.
- **SHAB constructible / potentiel** — même `parcel_faisabilite`.
- **Terrain m²** — cadastre.
- **Dernières ventes de la parcelle** — même table (l'outil en montre 6, la fiche 1).
- **Charge / bilan / calculette** — le composant `<Calculette>` **est** celui de la fiche.
- **Portes** faisabilité / fiche.

### (b) UNIQUE à l'outil

1. **Écart secteur ↔ commune entière** (« sous / au-dessus de la commune », en %). N'existe nulle
   part dans la fiche. Endpoint `mon-secteur` le sert déjà (`ecart_commune`).
2. **Détail par type Maison / Appartement au rayon adaptatif** (`_ref_local` mono-type). La fiche
   ne fait jamais ce découpage. Déjà servi par `mon-secteur` (`par_type`).
3. **Annonces Radar dans un rayon de 1500 m** (jeu plus large que le rattachement parcellaire,
   avec distance + écart à la médiane locale). Déjà servi par `mon-secteur` (`annonces_radar`).
4. *(mineurs, aucune donnée neuve)* la **note de distribution** du secteur bâti ; l'**alerte de
   cohérence** résiduel↔SHAB ; le cadrage « prix demandé → écart » de l'analyse d'opération.

### (c) Présent des deux côtés mais CALCULÉ DIFFÉREMMENT (un même chiffre servi de deux façons = un problème en soi)

1. **Prix du terrain nu du secteur** — outil = rayon **géographique** adaptatif 500→1500 m
   (`_terrain_local`, trim 5 %) ; fiche = table `dvf_secteur_medianes` par **section cadastrale**
   (unité administrative fixe, fenêtre 2021-2025). Deux « terrain nu secteur » qui peuvent différer.
2. **Annonces Radar** — outil = **rayon 1500 m** ; fiche = **rattachées à la parcelle** seule.
   Même libellé, deux populations.
3. **Prix de sortie du neuf** — outil = cascade `resolve_prix_sortie_servi` (bassin/secteur/commune/île) ;
   fiche = **VEFA commune**. Même concept, deux grains.

*(À noter : à l'intérieur même de l'outil il y a déjà deux « terrain nu » de méthodes différentes —
`par_type.terrain_nu` au rayon, et `terrain_zone` par zone PLU. L'incohérence terrain-nu préexiste
donc à la comparaison avec la fiche.)*

---

## Recommandation (3 lignes)

1. **L'outil est à ~85 % une re-présentation de la fiche** : son cœur (bâti secteur) est
   *littéralement* la même fonction, et calculette / terrain-zone / potentiel / dernières ventes /
   portes sont partagés. Le supprimer ne détruit aucun moteur.
2. **Déplacer les 3 éléments (b1–b3) dans la §Marché de la fiche, puis supprimer l'outil** :
   l'endpoint `/outils/mon-secteur` renvoie déjà `ecart_commune`, `par_type` et `annonces_radar` —
   c'est un travail de **rendu**, pas de calcul. Estimation **~0,5–1 j** (3 blocs à câbler dans
   `marche.tsx`, un `useQuery(['mon-secteur', idu])` déjà existant).
3. **Profiter du déplacement pour trancher les divergences (c)** — une seule méthode « terrain nu
   secteur », une seule portée « Annonces Radar », un seul grain « neuf ». Ces doublons de calcul
   sont un défaut **indépendamment du sort de l'outil** ; les résoudre est la vraie part soignée du
   chantier (sinon la fiche afficherait, après import, deux chiffres pour la même chose).

---

## 3. Hors mandat (non fait)

Modifier l'outil ou la fiche ; retravailler la lisibilité ; auditer les autres outils ; merger.

---

### Références de code (preuves)

- Outil : `frontend/src/components/outils/EtudierBien.tsx`, `…/MonSecteur.tsx` (`SecteurResultats`).
- Écran secteur back : `src/labuse/api/mon_secteur.py` (`sector_price` :79, `_dvf_bati`/`ecart_commune` :84-95, `_ref_local` :106-110, `_terrain_local` :25-50, Radar 1500 m :119-129).
- Écran « ce que porte » : `src/labuse/api/scoreur.py` (`_constat_servi` :157-223).
- Moteur secteur partagé : `src/labuse/faisabilite/bilan.py::sector_price` :200 ; `src/labuse/marche_service.py:122-135` (marche_dvf → sector_price).
- Fiche marché : `frontend/src/components/fiche/marche.tsx` ; source terrain nu secteur `src/labuse/api/app.py:3811-3812` (`dvf_secteur_medianes`).
- Entrée adresse → fiche : `frontend/src/components/header/Header.tsx:108`.
</content>
</invoke>
