# M132 — Audit de l'outil Faisabilité (lecture seule, aucun correctif)

Branche `audit/faisabilite` @ `5b8509f6`. **Aucune ligne de code n'a été modifiée.**
Constat sourcé fichier:ligne. Gravités : **faux positif** (cardinal) · **faux
négatif** · **décoratif** · **dette** · **cosmétique**.

L'outil = panneau Outils → « Faisabilité », composant front
`frontend/src/components/outils/M22Programme.tsx`. Deux onglets :
- **Par critères** : `POST /modules/programme` = `faisabilite_sens2`
  (`src/labuse/api/modules.py:1113`) — programme → liste de parcelles.
- **Par parcelle** : `GET /modules/faisabilite/{idu}` = `faisabilite_sens1`
  (`modules.py:858`) — parcelle → capacité + bilan.

Les deux onglets sont **de nature différente** : `sens1` est un calcul **live,
géométrique** (moteur `estimate_capacity` sur la vraie emprise) ; `sens2` est une
**lecture de caches** (SDP pré-calculée + scoring servi) avec un filtre SQL inline.
Tout le poids de l'audit porte sur **Par critères** (`sens2`).

---

## A — Chaîne de données : d'où vient chaque chiffre

Le SQL de `sens2` (`modules.py:1128-1142`) joint trois sources et impose un filtre
de tier :

| Champ / valeur | Source exacte | fichier:ligne |
|---|---|---|
| SDP résiduelle (le filtre + la valeur affichée) | cache `parcel_residuel.sdp_residuelle_m2` | `modules.py:1129,1134` |
| statut « étage 0 » | `dryrun_parcel_evaluations.status ∈ {exclue, faux_positif_probable}` (run `q_v10_m129`) | `modules.py:1132,1135` |
| tier / rang / q_score | `parcel_p_score_v2.tier`,`.rang` + `dryrun…q_score` (run v2 servi `_v2run`) | `modules.py:1130-1131,1136` |
| zone PLU (pour la hauteur) | `dryrun_cascade_results.detail` (`Zone PLU … « X »`) parsé au regex | `modules.py:1137-1138,1147-1148` |
| hauteur PLU | **live** `resolve_zone(zone, commune)` | `modules.py:1152-1155` |
| surface parcelle | `parcels.surface_m2` | `modules.py:1129` |
| besoin SDP / parking / hauteur min | calculés dans la vue (voir §B) | `modules.py:1119-1122` |

Champs du formulaire → `ProgrammeIn` (`modules.py:1103-1110`), câblés 1:1 depuis
`M22Programme.tsx:22-23` (`{...form, commune}`) : TYPE→`type`, BÂTIMENTS→`batiments`,
R+N→`niveaux`, UNITÉS/BÂT→`logements_par_batiment`, M²/UNITÉ→`surface_unite_m2`,
PARKING→`parking`, Périmètre→`commune`.

### A.1 — Vivier réel ou 431 663 ? — **dette**

`sens2` NE porte PAS sur les 431 663 parcelles. Le filtre effectif est
`s2.tier IN ('brulante','chaude','reserve_fonciere','a_creuser')`
(`modules.py:1140`). Mesuré (run v2 servi) : **34 006 parcelles** dans ces 4 tiers,
sur 24 communes. Le join `parcel_residuel r … r.sdp_residuelle_m2 >= :sdp`
(`modules.py:1134`) et `p.surface_m2 >= :smin` (`modules.py:1139`) restreignent
encore.

Le flag `etage0` (`modules.py:1132,1165`) est **redondant** : sur les 34 006
parcelles à tier admis, **0** est étage-0 (les 145 882 étage-0 du run sont tous
hors des 4 tiers). L'outil n'inclut donc jamais d'étage-0 — mais il transporte et
affiche quand même le flag. *Ce qui devrait être* : soit le retirer (mort), soit
documenter qu'il ne peut jamais être vrai ici. **Gravité : dette.** (Note : le
« vivier ~90 911 » de l'énoncé ne correspond à aucun compte servi ; l'univers
proposable réel de l'outil ≈ 34 006 avant filtres SDP/hauteur.)

### A.2 — SDP : cache, pas bascule ni direct — **dette**

La SDP consommée vient du **cache `parcel_residuel`** (`modules.py:1134`), pas
d'une table de bascule ni d'un calcul en direct. Peuplement : commande CLI
`compute-residuel` → `compute_residuel_batch` (`residuel.py:163`, upsert
`residuel.py:152-160`), **sans `run_label`** — seulement un `computed_at`.

Fraîcheur mesurée : 431 663 lignes, `computed_at` du **2026-07-29 au 2026-08-19**
(étalé sur 3 semaines, non atomique), 24 communes. Le cache **précède le merge
M131** (origin/main @ 5b8509f6, 2026-08-22). Preuve de **dérive** : pour
Saint-André, seules **143 / 1 711** parcelles proposables portent
`capacite_estimee=true` dans le cache, alors que `resolve_zone('U','Saint-André')`
renvoie aujourd'hui `calibree=False` (donc estimée) pour **toutes**. Le cache ne
reflète plus l'état PLU courant. *Ce qui devrait être* : recalcul lié au run servi
(ou horodatage + garde de péremption exposée). **Gravité : dette.**

### A.3 — Hauteurs post-M131 : vues en direct, mais SDP en cache — **dette**

Le filtre hauteur appelle `resolve_zone` **en direct** (`modules.py:1152`), donc
**voit les hauteurs gravées en M131**. Contrôle : `resolve_zone('Ua','Le Tampon')`
= hé 21 / hf 25 ; `resolve_zone('2AUc','Le Tampon')` = 9 / 13 ; `resolve_zone('Us',
'Saint-Pierre')` = 6 / 11 — toutes post-M131. **Mais** la SDP vient du cache
antérieur (§A.2) → **asymétrie** : hauteur live, SDP figée. De plus la lecture
`getattr(rules,"hauteur_max_m",None)` (`modules.py:1153`) vise un attribut qui
**n'existe pas** sur `ZoneRules` (c'est une clé YAML) → toujours `None`, puis repli
`hf_m or he_m` (`modules.py:1155`) = **faîtage**. **Gravité : dette** (asymétrie
live/cache ; ligne 1153 morte).

### A.4 — Zones gelées : gel respecté, mais indirectement — **dette (robuste mais fragile)**

`sens2` ne teste **jamais** `constructible_neuf`. Le gel n'est tenu
qu'**indirectement** : une zone gelée a `parcel_residuel.sdp_residuelle_m2 = 0`
(écrit par le batch quand `not f.constructible`, `residuel.py:96-98,198`), donc
`r.sdp_residuelle_m2 >= :sdp` (`:sdp ≥ 1`) l'exclut. Contrôle empirique : Us
(Saint-Pierre) et 2AUc (Le Tampon) → `sdp=0`, cause `zone_non_constructible:*`,
tier `ecartee`/`declasse_zone_fermee` (hors des 4 admis) → **exclues deux fois**.
Une zone gelée qui porte désormais une hauteur (Us 6/11, 2AUc 9/13) **ne devient
pas proposable** : ✔ vérifié. Robuste à M131 (M131 n'a touché aucun
`constructible_neuf`). *Fragilité* : le jour où une zone est nouvellement gelée
mais que le cache résiduel n'est pas rebâti (sdp>0 résiduel), elle **fuiterait** —
aucun garde-fou live sur `constructible_neuf`. **Gravité : dette.**

---

## B — Les calculs

### B.1 — Besoin programme — **cosmétique / dette**

`modules.py:1119-1120` :
```python
unites = max(1, body.batiments) * max(1, body.logements_par_batiment)
sdp_min = round(unites * body.surface_unite_m2 * 1.15)   # +15 % circulations (hypothèse)
```
Pour 1 bâtiment · 8 unités · 60 m²/unité : `unites=8`, `sdp_min = 8 × 60 × 1,15 =
552 m²`. Le `60 m²/unité` est donc traité comme **surface par unité** à laquelle on
ajoute **15 %** de circulations pour obtenir de la **SDP**. Le coefficient existe
(pas d'omission), mais **15 % < 20-25 %** attendus dans le neuf collectif (murs +
circulations + locaux techniques) → le besoin reste **sous-estimé de ~5-10 %** vs
une norme 20-25 %, dans le sens du faux positif. *Ce qui devrait être* : coefficient
paramétrable calé sur la typologie (≈1,20-1,25). Le label front affiche « (hyp.) »
(`M22Programme.tsx:100`). **Gravité : cosmétique/dette** (la sous-estimation
existe mais est bornée et affichée, pas un trou).

### B.2 — Le R+N : décoratif sur la SDP — **FAUX POSITIF (cardinal)**

C'est le point le plus exposé, et la suspicion est **confirmée**.

La SDP comparée est `parcel_residuel.sdp_residuelle_m2` = `sdp_max − sdp_existante`
(`residuel.py:121`), où `sdp_max = surface_plancher_m2` de la fourchette =
`emprise × coef × niveaux_max` avec `niveaux_max = he_m // étage_m`
(`engine.py:282`, `456`→`453`). C'est le **plein gabarit PLU**, tous niveaux.

Le R+N saisi n'entre **QUE** comme grille d'éligibilité hauteur :
```python
hauteur_min = (body.niveaux + 1) * 3.0          # modules.py:1122
...
hauteur_ok = (h is None) or (float(h) >= hauteur_min)   # modules.py:1158
```
`hauteur_ok` est un **booléen d'inclusion** ; il ne **redimensionne jamais** la SDP
comparée ni la `marge_capacite = sdp_residuelle / sdp_min` (`modules.py:1161`).

**Preuve empirique.** Ua Le Tampon (hf 25) `97422000EL0368` : surface **7 108 m²**,
`sdp_residuelle = 16 419 m²` — la SDP **dépasse la surface de la parcelle** → elle
est nécessairement **cumulée sur plusieurs niveaux** (niv_max = 7 = R+6), pas au R+N
demandé. Comme `hf 25 ≥ hauteur_min` pour tout R+1…R+7 ((7+1)×3=24 ≤ 25), **la
liste de candidates et les marges sont identiques** que l'utilisateur demande R+1
ou R+7 : le R+N ne fait que déplacer un seuil hauteur, jamais l'échelle de la SDP.
Une parcelle dont la capacité **au gabarit R+N demandé** est inférieure au besoin,
mais dont le résiduel **plein gabarit** le dépasse, est **retenue à tort**.

*Ce qui devrait être* : dimensionner la SDP au **gabarit demandé** (`min(niveaux+1,
niveaux_max) × emprise × coef`), puis comparer au besoin ; le R+N doit plafonner la
SDP, pas seulement filtrer la hauteur. **Gravité : faux positif (cardinal).**

*Cas test rapporté* : Ua (hé 21 / hf 25), demande R+1 → `hauteur_min = 6 m` ;
`hf 25 ≥ 6` → la parcelle **sort**, sur la base de son résiduel **R+6** (marge
gonflée ~×7 vs un vrai R+1).

*Sous-constat* : le seuil hauteur lit **hf_m (faîtage 25)** alors que le moteur
compte les niveaux sur **he_m (égout 21)** (`engine.py:282`) — grille plus permissive
que le moteur lui-même. **Gravité : cosmétique.**

### B.3 — Emprise au sol : non vérifiée — **FAUX POSITIF**

`sens2` ne contrôle **aucune emprise au sol**. Les seules bornes sont : le cumul
SDP (`r.sdp_residuelle_m2 >= :sdp`, `modules.py:1134`), la hauteur (§B.2), et un
**plancher de surface** grossier `p.surface_m2 >= :smin` avec `:smin = sdp_min*0.4 +
parking_m2` (`modules.py:1142`). Aucune vérification qu'un bâtiment de ~160 m²
d'emprise (pour 480 m² sur R+2) **tient géométriquement** sur la parcelle (largeur,
reculs, forme). Une parcelle étroite/coudée passe si son résiduel SDP ≥ besoin.
*Ce qui devrait être* : confronter le besoin d'emprise (SDP demandée ÷ niveaux) à
l'emprise constructible géométrique (déjà calculée par `parcel_faisabilite`,
`db.py:240`), que `sens2` **n'appelle pas**. **Gravité : faux positif.**

### B.4 — PARKING : quasi décoratif — **décoratif**

`parking_m2 = round(unites * 25) if body.parking else 0` (`modules.py:1121`). Son
**seul** effet est de relever le plancher de surface `:smin = sdp_min*0.4 +
parking_m2` (`modules.py:1142`). Il ne consomme **ni emprise, ni SDP, ni règle de
stationnement du PLU** (aucun `resolve_zone().stat_logement` lu ici). Concrètement,
activer PARKING ajoute `unites × 25 m²` au seuil de surface minimale de la parcelle
— effet marginal, sans lien avec la faisabilité réelle du stationnement (souterrain
vs surface, ratio PLU par typologie). C'est le précédent KelFoncier (couche affichée
non appliquée). *Ce qui devrait être* : consommer l'emprise/SDP de parking selon la
règle PLU, ou l'afficher comme simple rappel non filtrant. **Gravité : décoratif.**

### B.5 — Traçabilité — **dette**

Les hypothèses globales **sont visibles à l'écran** (bloc `criteres` +
`bandeau`, `M22Programme.tsx:112-119` ; « m²/unité × 1,15 circulations »,
« R+n → … × 3 m », « 25 m²/place », « Étude d'architecte requise »). En revanche,
**aucune valeur de résultat par parcelle n'est étiquetée Sourcé/Estimé** : les items
(`modules.py:1162-1168`) ne portent pas le flag `calibree`/`capacite_estimee`. Une
SDP **estimée générique** (commune non calibrée, §D.1) est affichée **exactement
comme** une SDP calibrée. Seule la hauteur porte `hauteur_verifiee` (bool). *Ce qui
devrait être* : propager `capacite_estimee` par item et le rendre (comme la fiche le
fait, `residuel.py:147-148`). **Gravité : dette.**

---

## C — Branchement à la fiche

### C.1 — Par parcelle = la fiche, même moteur — **OK (aucun défaut)**

L'onglet « Par parcelle » rend `FaisabiliteTab` (`M22Programme.tsx:173`), qui appelle
`getFaisabilite` = `GET /modules/faisabilite/{idu}` = `faisabilite_sens1`
(`api.ts:761`). C'est **le même endpoint** que l'onglet Faisabilité de la page
parcelle. Les deux passent par `parcel_faisabilite` (`db.py:182`) → moteur unique
`estimate_capacity` (`db.py:254`), **sans cache**. Le `_build_fiche` **legacy**
(`app.py:3619`) porte encore un bloc `faisabilite` (`app.py:3897`), mais il **n'est
pas consommé** par le front pour le verdict/capacité (le front force `source=q_v*`
→ `_q_v2_fiche`, qui ne contient aucun bloc faisabilité ; la capacité vient de
`getFaisabilite`). **Pas de divergence de moteur, contrairement au défaut trouvé par
`audit/comparer` (qui portait sur la cascade/tier, pas la faisabilité).**

### C.2 — Lien vers la fiche — **OK / cosmétique**

Depuis un résultat **Par critères**, chaque item est un bouton
`onClick={() => select(i.idu)}` (`M22Programme.tsx:134`) → `selectedIdu`
(`useApp.ts:473`) → overlay `<Fiche idu={selectedIdu}/>` (`App.tsx:338`). **Le lien
existe et le chemin de code est complet.** Côté **Par parcelle**, aucun lien
« ouvrir la fiche complète » n'est présent (seul `FaisabiliteTab` est embarqué,
`M22Programme.tsx:158-179`). **Gravité : cosmétique** (Par parcelle sans accès fiche
entière).

### C.3 — Coïncidence des chiffres — **dette (sémantique, pas divergence de moteur)**

Même moteur des deux côtés, mais **métriques affichées différentes** : « Par
critères » montre le **résiduel net** (`sdp_max − bâti existant`), la fiche/« Par
parcelle » montre la **capacité brute** (`surface_plancher_m2`). Tableau (3 parcelles
Ua Le Tampon, `parcel_faisabilite` live vs cache) :

| Parcelle | SDP « Par critères » (résiduel) | SDP fiche (capacité brute, niv_max) | écart |
|---|---|---|---|
| `97422000EL0368` | 16 419 m² | 17 726 m² (R+6) | −7 % |
| `97422000CH0117` | 10 874 m² | 10 893 m² (R+6) | 0 % |
| `97422000ED0179` | 10 761 m² | 11 299 m² (R+6) | −5 % |

Les deux nombres sont **proches** (l'écart = le bâti existant soustrait) et
**cohérents** (même moteur) — mais **tous deux au gabarit maximal R+6**, jamais au
R+N demandé (§B.2). Un promoteur voit deux SDP légèrement différentes pour la même
parcelle, aucune ne correspondant à son programme. **Gravité : dette**
(harmoniser la métrique affichée + l'ancrer au gabarit demandé).

---

## D — Périmètre et cohérence produit

### D.1 — « Toute l'île » = 24 en théorie, 21 calibrées — **faux positif (doux) / dette**

Le référentiel officiel = **24 communes** (`communes.py:28`,
`run_all.py:26-38`). Mais seules **21** ont un `config/plu_<slug>.yaml` (vérifié
`ls config/plu_*.yaml` = 21). **Absentes** : **Saint-André** (pourtant
`etat: gold`, `communes_gold_standard.yaml:105`), **Saint-Leu**, **Saint-Philippe**
(RNU, INSEE **97417** — l'énoncé disait 97442, inexact).

Comportement de `sens2` par cas (suivi du SQL) :
- **RNU (Saint-Philippe)** → `resolve_zone` None / hors PLU → résiduel `hors_plu`,
  `sdp = NULL` (`residuel.py:73-74,91-93`) → `r.sdp_residuelle_m2 >= :sdp` **exclut**
  toute ligne NULL. **Structurellement absent** de l'outil. ✔ cohérent.
- **Non calibrée avec zonage U/AU (Saint-André, Saint-Leu)** → `resolve_zone` retombe
  sur l'**estimation générique** (`plu_rules.py:238,273-277`), `calibree=False`,
  `constructible=True`, SDP > 0. **Ces parcelles remontent** : mesuré Saint-André =
  **1 711 parcelles proposables**. Or l'item `sens2` **n'affiche pas** qu'elles sont
  estimées (§B.5). *Incohérence produit* : une commune « gold » sans PLU outillé
  sert des capacités **estimées, non signalées**. **Gravité : faux positif (doux) /
  dette.**

### D.2 — Deux systèmes de filtre pour « périmètre » — **dette structurelle**

- **Système A — `FiltreCriteres`** (`app.py:1200`) : point d'entrée unifié
  (~50 facettes), `.where()` → `_q_v2_where`. Alimente la carte, la liste,
  `/parcels/export.csv` (`app.py:1322`), le copilote, et **les Projets** (le cadrage
  EST un `FiltreCriteres`, `projets.py:3-8,249-255`).
- **Système B — `faisabilite_sens2`** : **SQL inline** (`modules.py:1128-1142`),
  un seul paramètre `commune`, **n'importe ni n'instancie `FiltreCriteres`**. Pas de
  facette tier/surface/rang/signaux ; le seul recoupement est de lire les **mêmes
  tables** (`parcel_p_score_v2`, run servi).

La doctrine « un critère = un seul endroit » revendiquée pour les Projets
(`projets.py:3`) **ne couvre pas** cet outil : deux mécanismes parallèles pour la
notion « périmètre ». **Gravité : dette structurelle.**

### D.3 — Classement : rang/score dans la charge utile — **dette / cosmétique**

Tri `items.sort(key=lambda x: -x["marge_capacite"])`, troncature `[:200]`
(`modules.py:1169-1170`), `n` = vrai total. Le JSON de chaque item **expose**
`rang_v2`, `tier_v2`, `statut`, `q_score`, `marge_capacite`
(`modules.py:1162-1168`) — donc **rang et score en clair dans la réponse API**.

Nuances mesurées :
- **À l'écran** (`M22Programme.tsx:132-152`) : seuls la marge (`×`) et un
  **`TierBadge`** (label « brûlante / à creuser », pas la valeur brute) sont rendus.
  `rang_v2` et `q_score` **ne sont pas affichés** par ce composant. Le tier
  qualitatif, lui, **fuit à l'écran** sous forme de pastille.
- **Export/partage** : **aucun export propre à l'outil** (grep `/programme` ×
  `export|csv|pdf|share` = 0 ; `postProgramme` sans bouton de téléchargement). Donc
  aucun rang/score ne fuit **par un fichier d'export** de cet outil.

*Ce qui devrait être* : ne pas transporter `rang_v2`/`q_score` dans la charge utile
d'un outil de mise en relation (fuite latente si copie manuelle) ; le tier affiché
reste discutable au regard de la règle « aucun rang ne sort ». **Gravité : dette**
(charge utile) **/ cosmétique** (tier à l'écran).

---

## E — Verdict d'utilité

### 1. À quelle question l'outil répond-il RÉELLEMENT ?

Pas « où mon programme R+N rentre-t-il ? ». Il répond :

> « Parmi les parcelles **déjà bien notées** (tiers chauds) des communes **scorées**,
> lesquelles ont un **potentiel résiduel au plein gabarit PLU** (net du bâti
> existant, cache figé) **supérieur** à mon besoin SDP, et dont la zone **autorise au
> moins la hauteur** R+N — sans vérifier que le bâtiment **tient au sol** ni que la
> capacité **au gabarit demandé** suffit. »

C'est un **pré-tri capacitaire optimiste**, pas une pré-faisabilité.

### 2. Un promoteur peut-il agir sur ce résultat ?

**Pas en l'état.** Il obtient une *shortlist* exploitable comme point de départ (le
gel est respecté, le lien fiche marche, les hypothèses sont affichées), mais **chaque
candidate doit être re-vérifiée** : la marge est gonflée (plein gabarit, §B.2),
l'emprise n'est pas testée (§B.3), le parking est décoratif (§B.4), la SDP peut être
estimée sans le dire (§B.5, §D.1) et vient d'un cache de 3-24 j (§A.2). Maillon
manquant : le **dimensionnement au gabarit demandé + le test d'emprise**.

### 3. Que faudrait-il pour qu'il soit professionnel ? (ordonné valeur/coût)

**Défauts à réparer :**
1. **B.2 (cardinal)** — dimensionner la SDP au **gabarit R+N demandé**
   (`min(niveaux+1, niveaux_max)`), pas au résiduel plein gabarit. *Le plus rentable :
   supprime la classe majeure de faux positifs.*
2. **B.3** — brancher le **test d'emprise géométrique** (déjà calculé par
   `parcel_faisabilite`, `db.py:240`) : le besoin d'emprise doit tenir.
3. **A.2** — garantir la **fraîcheur** du résiduel (recalcul lié au run servi, ou
   péremption exposée) ; supprimer l'asymétrie hauteur-live / SDP-cache (§A.3).
4. **B.5 / D.1** — propager et **afficher `capacite_estimee`** par parcelle ;
   signaler les communes non calibrées (Saint-André, Saint-Leu).

**Manques à construire :**
5. **B.4** — vraie règle de stationnement PLU (emprise/SDP consommée), ou l'assumer
   comme rappel non filtrant.
6. **D.2** — unifier le périmètre sur **`FiltreCriteres`** (un seul système de
   filtre) au lieu du SQL inline parallèle.
7. **D.3** — retirer `rang_v2`/`q_score` de la charge utile de l'outil.

**Cosmétique :** seuil hauteur sur hé plutôt que hf (§B.2) ; flag `etage0` mort
(§A.1) ; lien fiche complète depuis « Par parcelle » (§C.2).

### Franchise

**Ce n'est pas un gadget, mais « Par critères » sur-promet.** Le socle est sain :
gel respecté (§A.4), même moteur que la fiche pour « Par parcelle » (§C.1),
hypothèses affichées (§B.5), lien fiche opérant (§C.2). Mais l'onglet phare répond à
une question **plus lâche** que son libellé (« trouver les parcelles » où le
programme rentre) : le R+N est **décoratif sur la SDP** et l'emprise n'est pas
testée → il **produit des faux positifs par construction**. Utilisable comme
dégrossissage, **pas** comme réponse de faisabilité actionnable tant que B.2 et B.3
ne sont pas traités.

---

*Fin d'audit. Aucune correction appliquée. Branche `audit/faisabilite` — CC ne
merge pas. Vic arbitre le périmètre du mandat de correction.*
