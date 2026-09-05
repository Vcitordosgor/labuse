# RETOURS-15 — COMPTE-RENDU

Branche `fix/retours-12`, trois commits (carte U1 · permis U2-U4 · outils U5-U8) + captures.
Captures avant/après : `docs/audit-2026-09/RETOURS-15/captures/` (suffixes `-avant` / `-apres`).

## Vérification préalable — les données S5 sont-elles dans la base servie localement ?

**OUI, les trois marqueurs sont là.** Mesuré sur `postgresql://openclaw@localhost:5432/labuse` :
- `sitadel_permits` avec `raw->>'geoloc'` = « parcelle d'origine… » : **7 325** (attendu ~7 325 ✓) ;
- PC `97441816A0077` → `geom` = `POINT(55.512 -20.894)`, `parcelles_actuelles` = `["97418000BC0331"]` ✓ ;
- points d'adresse démis (`geom_approx` non nul, `geom` nul) : **580** ✓ ; `cadastre_historique` : 5 233 lignes.

Le backfill S5 EST dans la base locale. **La vraie cause de U2 était ailleurs** (plafond carte, voir U2)
et **celle de U5 aussi** (dépendance manquante dans le service `.venv`, voir U5). Note importante
découverte au passage : le service que Vic lance sur ce Mac est **`.venv/bin/labuse api`** (Python 3.12),
PAS l'environnement conda `labusedb` — c'est ce `.venv` qui manquait `rasterio` (U5).

## Une ligne par travail

- **U1 — ortho entière, mer comprise, sans masque** : FAIT. Retiré le masque de mer (R1) et TOUS les
  `bounds` (C6) qui découpaient jetées/ports en biseau. Deux sources par zoom (mesurées au GetTile) :
  sous-couche monde `ORTHOIMAGERY.ORTHOPHOTOS` (mer photographiée ≤ z12, overzoom au-delà) sous
  l'Ortho Express (terre + mer côtière, minzoom 12). L'IGN servant des tuiles BLANC PUR sur une bande
  de mer côtière que MapLibre ne peut pas écarter, un **proxy backend** `/map/tiles/ortho-express`
  les transforme : tuile toute blanche → 404 ; tuile mixte (l'emprise finit en plein milieu) → le
  blanc connecté au bord passe transparent pixel par pixel (une tache blanche isolée au centre n'est
  jamais touchée). Sous tout : le canvas sombre, jamais de blanc. Même règle sur le Plan IGN (il
  dessinait déjà sa mer). Captures 3 cadrages × 2 fonds + couture z12/z13.
- **U2 — le permis de l'hôtel, pour de vrai** : FAIT. La donnée était bonne (fiche BC0331 → « Autour »
  → PC 97441816A0077 à 0 m, tiroir « parcelle d'origine » — vérifié) ; le défaut était la CARTE : la
  couche permis plafonnait à `LIMIT 8000` triés par date DESC → en « Tous » (240 mois), elle ne gardait
  que les 8 000 plus récents et **jetait tous les PC anciens rattachés par la géométrie**. Plafond levé
  à 60 000 (borne de payload, 41 ms mesurés pour la fenêtre pleine) : le compteur « sur la carte » passe
  de **8 200 à 47 270**, l'hôtel et son secteur apparaissent (capture ortho chantier). Le rond vert de
  la parcelle boisée au sud = **PC 2025 légitime sur AX0495** (identifié) — il reste, c'est un vrai permis.
  Chemin en 3 clics pour Vic : *(1)* ouvrir la fiche de `97418000BC0331` ; *(2)* dérouler « Autour de
  cette parcelle » ; *(3)* cliquer la ligne « PC 2016-11-18 » du bloc « Permis à proximité » → le tiroir
  montre `97441816A0077` avec la provenance « parcelle d'origine (cadastre 2017-02-13) ».
- **U3 — libellés et ordre des filtres** : FAIT. « Chantier récent » → **« Récent »**, « Point mort » →
  **« Au point mort »** (tient sur une ligne). Règle « Tout »/« Tous » **toujours en dernier à droite**
  appliquée aux natures (PC·DP·PA·PD·Tout), au géocodage (Sur la carte·Non géocodés·Tous) et aux 3
  segments du Radar client (Rattachés·Tous ; Particulier·Pro·Tous ; Sous le marché·Tous les prix).
  Autres groupes de chips inspectés : **Admin › Sources** (« Toutes » en tête) — laissé tel quel car
  c'est un écran ADMIN avec un ordre mandaté (Q2.1 : à jour · nouvelle version · à rafraîchir…), hors
  périmètre client. La phrase d'explication sous les compteurs est conservée.
- **U4 — plus de défilement horizontal** : FAIT. `overflow-x-hidden` sur le conteneur de la liste
  permis + badge raccourci « approx. (adresse) » (libellé complet au survol). Scan automatique
  (conteneurs en `overflow-x:auto/scroll` qui débordent) à **1280 ET 1440 px** sur permis, communes,
  évolution, fiche : **0 barre horizontale après** (l'avant à 1440 en montrait une sur la liste permis).
- **U5 — nature et pente du toit** : FAIT, **cause trouvée**. Le service `.venv/bin/labuse api` n'avait
  pas `rasterio`/`scipy` (l'extra optionnel `[lidar]` de R31 que **rien n'installait**) → l'import
  paresseux échouait, avalé, la fiche montrait « — ». Preuve par traçage : le module calcule bien
  (`~/miniforge3/envs/labusedb` → 4/10 servies sur 10 parcelles Uh à Saint-Denis) mais l'endpoint
  `.venv` rendait `null` partout. Corrigé : **rasterio+scipy promus en dépendances de série** (extra
  `lidar` supprimé). **Trois états distincts à l'écran** (jamais confondus, doctrine U5) : servi
  (« simple pente ») · sous le seuil (« non déterminée — pans non nets ») · échec technique (« non
  calculée — LiDAR indisponible », cause au journal serveur, rien mis en cache). **Recette sur 10
  parcelles Uh Saint-Denis** (service réparé) :

  | IDU | verdict | confiance | pente | état à l'écran |
  |---|---|---|---|---|
  | 97411000AV0056 | monopente | 0,913 | 25,9° | **servi** : simple pente · 25,9° |
  | 97411000BZ0013 | monopente | 0,853 | 13,0° | **servi** : simple pente · 13,0° |
  | 97411000BX0009 | double_pente | 0,829 | 19,1° | **servi** : double pente · 19,1° |
  | 97411000CD0001 | double_pente | 0,802 | 18,0° | **servi** : double pente · 18,0° |
  | 97411000CL0028 | non_determine | 0,616 | — | non déterminée — pans non nets |
  | 97411000CM0007 | non_determine | 0,579 | — | non déterminée — pans non nets |
  | 97411000CE0134 | non_determine | 0,574 | — | non déterminée — pans non nets |
  | 97411000CP0022 | non_determine | 0,529 | — | non déterminée — pans non nets |
  | 97411000CH0033 | non_determine | 0,338 | — | non déterminée — pans non nets |
  | 97411000CI0003 | non_determine | 0,000 | — | non déterminée — pans non nets |

  **4 servies sur 10** (au-dessus du seuil 0,70), l'état affiché correspond au tableau. (Le premier
  tirage de 10 parcelles tombait sur des sections « AB/AC… » sans bâtiment cadastré intersectant →
  `null` légitime « pas de bâtiment » ; le second tirage, bâti confirmé, donne le tableau ci-dessus.)
- **U6 — provenance et libellé du pré-remplissage taxe** : FAIT. Le « 26 m² » vient de la **VUE
  `parcel_residuel`** (run servi `m135-run2-ile`, `is_served`), **PAS de la table morte
  `parcel_residuel_bati`** (vérifié : `pg_get_viewdef` → `parcel_residuel_runs WHERE is_served`).
  L'API sert `deja_batie` (emprise > 0) → libellé « **SDP restante au gabarit (parcelle déjà bâtie) :
  26 m²** » quand il y a du bâti, « SDP au gabarit » sur une parcelle nue. Ligne d'assiette reformulée :
  « **taux non renseigné, saisissez-le ci-dessus** » (plus « en attente du taux communal »). Le
  pré-remplissage garde « pré-rempli par LABUSE, modifiable — la surface taxable est celle de votre projet ».
- **U7 — adresse sur une seule ligne** : FAIT. Le bloc adresse quitte la colonne partagée avec les
  logos+cloche (qui la rétrécissaient → coupure « à la moitié ») pour une rangée `.addr-row` **pleine
  largeur** sous l'en-tête : une ligne tant que ça tient, ellipse + adresse complète au survol sinon.
  Mesuré après : « 50 Rue Hélène Boucher, 97438 Sainte-Marie » sur **1 ligne** (avant : 2).
- **U8 — zip du PLU en vigueur même en révision** : FAIT. Nouvel endpoint `/plu-annuaire/pack/{insee}`
  qui résout **en direct sur le GPU** le pack `.zip` du PLU en vigueur (document EN_VIGUEUR, sinon le
  plus récent), avec mention « révision en cours — ce document reste applicable jusqu'à l'approbation
  du nouveau ». Trois issues distinctes. **Constat mesuré le 05/09** : le GPU renvoie `[]` (aucun
  document) pour **Saint-André (97409) ET Saint-Leu (97413)** — l'écran le dit honnêtement et sert les
  coordonnées de la mairie (source K2) plutôt qu'un bouton mort. Contrôle : une commune servable
  (Cilaos 97416 EN_VIGUEUR 25/06/2024, ou les 23 à PLU) rend bien son zip. La commune RNU (Saint-Philippe)
  garde le lien vers le règlement national (S3). Vérifié : 23 communes à PLU ont un zip résolvable ; les
  2 en révision non publiée au GPU (St-André, St-Leu) affichent la mairie, faute mieux côté source.

## Recette

- Suite pytest : **2 315 passed, 2 failed**. Les deux échecs : `test_r5_etudier_deux_marges`
  (PRÉ-EXISTANT, chaîne absente dès la base, hors périmètre) et `test_fond_actuelle_est_ortho_express_2025`
  (conséquence directe de U1 — l'ID de couche Express a migré vers app.py côté proxy — **corrigé** dans
  le lot outils, repasse). 1 erreur `test_cascade` = flakiness d'ordre (verte en isolation). Nouveaux/mis
  à jour : `test_retours14_outils` (3 états toiture U5).
- vitest : **170 passed** (dont le test basemaps U1 réécrit : aucun fond borné, sous-couche monde porte
  la mer). `tsc` : 0 erreur. Build : OK.
- Environnement : **rasterio installé dans `.venv`** (wheel binaire autonome) ; le `pyproject.toml`
  promeut maintenant rasterio+scipy en dépendances de série, donc un `pip install -e .` futur les portera.

## Note d'exploitation

- Le service local servi à Vic est `.venv/bin/labuse api` (Python 3.12), distinct de l'env conda
  `labusedb` utilisé pour les tests/CLI. Toute dépendance de RUNTIME doit être installée dans le `.venv`.
- Le proxy `/map/tiles/ortho-express` mémorise les tuiles blanches (verdict immuable par tuile) et
  cache 24 h côté HTTP ; il relaie tel quel au-dessus de z16 (pas de bande blanche à ces zooms).
