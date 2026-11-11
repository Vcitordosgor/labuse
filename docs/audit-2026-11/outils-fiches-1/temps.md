# Remonter le temps

Clé interne : `temps` (num M08) · composant : `frontend/src/components/outils/ModulePanel.tsx` (bandeau gauche `M08`, l.1258) + `frontend/src/components/outils/TimeMachine.tsx` (vue carte) · endpoint(s) : `/moteurs/histoire/{idu}`, `/moteurs/parcellaire-epoque/{idu}`, tuiles `/map/tiles/ortho/{couche}/{z}/{x}/{y}`, `/map/tiles/carte-ancienne/{couche}/{z}/{x}/{y}`, `/map/tiles/ortho-express/{z}/{x}/{y}` (legacy).

L'outil a DEUX chemins. Une remarque essentielle d'entrée : seul le chemin (B) est réellement branché dans l'application servie aujourd'hui. Le chemin (A) existe en code et son endpoint répond, mais aucun composant vivant ne l'affiche (voir rubrique 6 et 10).

---

## 1. À quoi il sert, et pour qui

Pour un prospecteur foncier ou un conseiller, l'outil montre comment une parcelle a évolué dans le temps : (A) la liste des faits datés qui l'ont touchée (ventes, permis, changement de propriétaire, découpe cadastrale) et (B) la comparaison de deux photos aériennes IGN — une année ancienne à gauche, aujourd'hui à droite — avec une poignée de glissement. C'est un outil de lecture (aucune écriture, aucun score), qui sert la même donnée que le reste de l'application sans la recalculer.

## 2. Le parcours

Commun aux deux chemins : dans le bandeau gauche (`M08`, `ModulePanel.tsx:1258`), l'utilisateur désigne UNE parcelle (saisie IDU/adresse via `EntreeParcelle`, ou clic sur la carte ; `designer()` l.1269). Cela épingle la parcelle (`setTempsPinIdu`, l.1272) et ouvre sa fiche. L'« après » du comparateur est TOUJOURS verrouillé sur aujourd'hui (`setCmpRight('bm-ortho-now')`, l.1266) ; seule l'année « avant » se choisit.

### Chemin A — la frise des faits datés
Composant : `HistoireFrise.tsx`. Sous le comparateur, une frise horizontale pose un repère par fait daté sur un axe 1950→aujourd'hui (échelle non linéaire : 1950-2000 = 20 % de la largeur, 2000-2015 = 30 %, 2015-auj = 50 %, `SEGMENTS` l.31). Marqueur par famille (vente ambre, permis vert, propriétaire gris, découpe violet, `FAM` l.46) ; la précision SE VOIT (point plein = jour, anneau = année seule, tirets = écart entre deux millésimes). Clic sur un repère → encart détail (`FaitDetail` l.62) avec libellé, chiffres, source, date à sa maille, et ponts vers Permis / fiche-ventes / Scan patrimoine.
**ATTENTION** : dans l'application servie, cette frise n'est rendue nulle part (voir rubrique 6).

### Chemin B — le comparateur d'orthophotos
Composant : `TimeMachine.tsx`. Deux cartes MapLibre superposées (`mkMap` l.17), celle de droite rognée par la poignée (`clipPath`, l.268). L'utilisateur choisit l'année ancienne via une rangée de puces (`Chip`) listée depuis `TEMPS_MILLESIMES` (`ModulePanel.tsx:1316`). Le contour BLANC de la parcelle désignée est tracé sur les deux fonds (`cible`, l.143-147), avec une étiquette IDU posée au-dessus du contour (`Marker` l.224). Option « Parcellaire de l'époque » (puce ambre, off par défaut, `cadastreOn` l.82) : disponible seulement si l'année choisie ≥ 2016 (`cadastreDispo`, l.86), superpose le contour ambre en tirets de la/les parcelle(s) MÈRE d'origine (`/moteurs/parcellaire-epoque`). Les deux caméras sont synchronisées (`sync` l.110). Clic carte = désigne une nouvelle parcelle (`onPick` l.120).

## 3. Les données lues

### Chemin A (frise des faits) — `/moteurs/histoire/{idu}`, `moteurs.py:434`

| Source (catalogue `data_sources.name`) | Table SQL réellement lue | Millésime servi | Cadence |
|---|---|---|---|
| DVF / valeurs foncières | `dvf_mutations_parcelle` (2021→) + `dvf_mutations_histo` (2014→2020) (`moteurs.py:458-467`) | géo-DVF Etalab 2026-S1 ; max `date_mutation` = **2025-12-31** (rejoué) | semestriel |
| DVF Réunion (Région) | (incluse dans `dvf_mutations_histo`, archives 2014→2020) | jeu figé 2014→mi-2021 | — (alias) |
| SITADEL (autorisations d'urbanisme) | `sitadel_permits` (`moteurs.py:492-497`) | `2026-08` ; max `date` = **2026-08-31** (rejoué) | mensuelle |
| DGFiP — parcelles des personnes morales | `pm_proprietaires_millesimes` (timeline, via `proprietaire_historique.historique`) + `parcelle_personne_morale` (snapshot courant) (`moteurs.py:522-523`, `586-589`) | millésimes 2019→**2025** (rejoué) | annuelle |
| DFI — documents de filiation (DGFiP) | `dfi_filiation` (`moteurs.py:554-562`) | situation 19/06/2026 ; max `date_validation` = **2025-12-29** (rejoué) | — (connecté) |

### Chemin B (comparateur d'orthos)

Fonds photo/carte servis en direct depuis l'IGN Géoplateforme via le proxy backend (`ortho_proxy.py:69` pour les orthos ; `:352` pour les cartes anciennes). Ils n'ont pas de ligne `data_sources` individuelle : ils relèvent du HUB `Géoplateforme IGN` (`data_sources` id 14, `ortho_proxy.py:45-51`). Chaque millésime offert est dans `TEMPS_MILLESIMES` (`basemaps.ts:85`).

| Libellé frise (`TEMPS_MILLESIMES`) | Couche WMTS IGN (`ortho_proxy._COUCHES`) | Source catalogue | Tuile rejouée (St-Denis z15) |
|---|---|---|---|
| Carte SCAN 50 (1950) `bm-scan50-1950` | `GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN50.1950` (`:352`) | SCAN 50 historique 1950 (IGN) | 200, 24 728 o |
| 1950-1965 `bm-ortho-1950` | `ORTHOIMAGERY.ORTHOPHOTOS.1950-1965` (`:72`) | Géoplateforme IGN (hub) | 200, 59 380 o |
| 2000-2005 `bm-ortho-2000` | `ORTHOIMAGERY.ORTHOPHOTOS2000-2005` (`:73`) | Géoplateforme IGN (hub) | 200, 26 416 o |
| 2006-2010 `bm-ortho-2006` | `ORTHOIMAGERY.ORTHOPHOTOS2006-2010` (`:74`) | Géoplateforme IGN (hub) | 200, 171 798 o |
| 2011-2015 `bm-ortho-2011` | `ORTHOIMAGERY.ORTHOPHOTOS2011-2015` (`:75`) | Géoplateforme IGN (hub) | 200, 26 026 o |
| 2016-2020 `bm-ortho-2016` | `ORTHOIMAGERY.ORTHOPHOTOS2016-2020` (`:76`) | Géoplateforme IGN (hub) | 200, 175 710 o |
| 2021-2023 `bm-ortho-2021` | `ORTHOIMAGERY.ORTHOPHOTOS2021-2023` (`:77`) | Géoplateforme IGN (hub) | 200, 29 101 o |
| « Aujourd'hui » (après, verrouillé) `bm-ortho-now` | `ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2025` (`:58-59`, overridable via env `LABUSE_ORTHO_EXPRESS`) | BD ORTHO 20 cm (IGN) / hub | 200, 23 142 o (express) |

Hors frise mais présent en base : `bm-edugeo-1980` (EduGéo Réunion 1980, `GEOGRAPHICALGRIDSYSTEMS.EDUGEO.LA-REUNION1980`, `:353`) — **retiré des choix offerts** (`basemaps.ts:89-92`, « RECETTE-PROD-1 (15) ») car couverture partielle (St-Denis/Cilaos vides). Rejoué à St-Denis z15 : 200 mais seulement **852 octets** (tuile quasi vide), ce qui confirme le motif du retrait. La couche `monde` (`ORTHOIMAGERY.ORTHOPHOTOS`, `:70`) est la sous-couche « terre aux petits zooms », pas un millésime.

« Parcellaire de l'époque » : `cadastre_historique` (6 526 lignes en base, parcelles d'origine disparues) jointe à `dfi_filiation` (`moteurs.py:623-627`). Source affichée : « Cadastre d'époque (Etalab/PCI) — parcelle d'origine (DGFiP) ».

## 4. Les calculs

Il n'y a quasiment AUCUN calcul métier dans cet outil — c'est délibéré (`HistoireFrise.tsx:9` : « Aucun calcul métier ici : /moteurs/histoire sert tout »). Ce qui ressemble à un calcul :

- **Maille d'une date** (`_histoire_date`, `moteurs.py:424`) : une date `01/01` d'un fait « année seule » (dépôt de permis) est rendue « 2024 » maille `annee`, jamais « 01/01/2024 » (convention Sit@del : la source ne publie que l'année). Sinon maille `jour`. Aucune valeur inventée.
- **Déduplication des ventes** (`moteurs.py:462-468`) : `DISTINCT ON (id_mutation)` garde le local le plus bâti d'une mutation — sinon une vente « Maison + Dépendance » s'afficherait deux fois. Le prix affiché est celui de la MUTATION ENTIÈRE (elle peut couvrir plusieurs parcelles), dit tel quel (`:478`, `HistoireFrise.tsx:91` « (mutation entière) »).
- **Fait « sur la parcelle mère »** (`moteurs.py:472`) : une vente datée AVANT la naissance DFI de la parcelle (`min(date_validation)` où `idu_fille = idu`, `:452`) est signalée comme portant sur la parcelle mère (date vraie conservée, mention ajoutée).
- **Arrondis** : surfaces bâti/terrain `round()` (`:480-481`) ; nb logements `int(float())` (`:500`) ; surface habitable `round(float())` (`:501`). Pas de division ni de barème.
- **Position sur la frise** (`HistoireFrise.pct`, l.39) : projection non linéaire 3-segments, purement graphique.
- **Échelle des couches ortho** : `maxzoom` par couche (`basemaps.ts:64-79`) = un cran sous le dernier zoom servi par l'IGN → overzoom plutôt que tuiles noires. Codé en dur, vérifié par GetTile réel (commentaire `basemaps.ts:72-75`).

Constantes notables :
- `_HISTOIRE_CAP_FILIATION = 12` (`moteurs.py:421`) : plafond de la liste de parcelles liées affichées pour une découpe ; le TOTAL `n_parcelles_liees` est toujours servi. Codée en dur.
- `AXE_MIN = 1950` / `AXE_MAX = année courante +1` (`HistoireFrise.tsx:27-28`) : bornes de la frise. Codées en dur.
- `cadastreDispo` seuil `periodAn >= 2016` (`TimeMachine.tsx:86`) : le parcellaire d'époque n'est offert que si l'année « avant » ≥ 2016, car 2016-2020 recouvre 2017 (1er millésime cadastre ingéré). Codé en dur.
- `ORTHO_EXPRESS_SERVIE` (`ortho_proxy.py:58`) : identifiant de la couche « Aujourd'hui », config overridable (env), pas codé en dur.

## 5. Chaque chiffre affiché

### Chemin A (frise / détail d'un fait)

| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| Date du fait (jour / « année » / « entre deux 1ᵉʳ janv. ») | `moteurs.py:424` depuis la date de la table source, à sa maille | Sourcé |
| Prix « X € (mutation entière) » | `dvf_mutations_*.valeur_fonciere` (`:479`) | Sourcé |
| « N m² bâti » / « N m² terrain » | `surface_reelle_bati` / `surface_terrain` DVF (`:480-481`), arrondis | Sourcé |
| « N logement(s) » / « N m² hab. » | `sitadel_permits.raw->>'nb_lgt'` / `'surf_hab'` (`:500-501`) | Sourcé |
| « Propriétaire PM avant → après » (dénomination, SIREN) | `proprietaire_historique.historique` → `pm_proprietaires_millesimes` (`:545-546`) | Sourcé |
| « N parcelle(s) liée(s) » + liste IDU | `dfi_filiation` `count(*)` + `array_agg` (`:557-570`) | Sourcé |
| Puce « Sourcé » sur chaque fait | Codée en dur `"statut": "Sourcé"` (`:482`, `:502`, etc.) | — (libellé fixe, l'outil ne sert que du sourcé) |
| Bandeau « Faits datés — DVF : … · Sit@del : … » | `max()` des dates de chaque table (`:580-590`) | Sourcé |

### Chemin B (comparateur)

| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| Nom du fond gauche/droite (ex. « 2016-2020 », « Actuelle · Ortho Express 2025 ») | `basemapLabel` → `TEMPS_MILLESIMES`/`ORTHO_YEARS` (`basemaps.ts:120`) | Sourcé (libellé du millésime IGN) |
| Image aérienne | tuile WMTS IGN relayée par le proxy | Sourcé (photo IGN) |
| Étiquette IDU sur le contour | `pinIdu` (la parcelle désignée) | Sourcé |
| « Cadastre d'époque {millésime} » | `parcellaire-epoque.millesime` (dernier de `cadastre_historique`, `moteurs.py:633-635`) | Sourcé |
| Contour blanc de la parcelle | géométrie `getParcelGeojson(idu)` (`TimeMachine.tsx:99`) | Sourcé |

Aucun chiffre estimé n'est produit par cet outil : il n'y a ni barème ni calcul de valeur.

## 6. Les limites

- **Le chemin A n'est pas affiché dans l'application servie.** `HistoireFrise` n'est importée/rendue par AUCUN composant vivant : `grep` ne trouve qu'une mention en commentaire (`TimeMachine.tsx:9` : « la frise du bas … est retirée : HistoireFrise n'est plus rendue par le comparateur »). Quand `module === 'temps'`, `App.tsx:506` rend uniquement `TimeMachine` (le comparateur). La carte du menu décrit pourtant toujours « la frise des faits datés + le comparateur d'orthos » (`registry.ts:117`, commentaire) et l'endpoint `/moteurs/histoire` fonctionne. Résultat : l'utilisateur ne voit JAMAIS la frise des faits — seulement le comparateur de photos. (Le composant et son endpoint restent testés, d'où une fiabilité qui masque l'absence d'affichage.)
- **Les fonds ortho dépendent de l'IGN en direct** : une tuile au large, hors couverture ou hors zoom de mission renvoie 404 (proxy muet, `ortho_proxy.py:265-267`) ; aucun cache local. Si l'IGN change le nommage des couches, les fonds anciens cassent silencieusement (le comparateur affiche l'aplat du dessous).
- **EduGéo 1980** est retiré de la frise (couverture partielle, tuile St-Denis ~852 o) ; aucune carte d'avant 1950 ni d'ortho entre 1965 et 2000 n'est servie — la frise a un trou 1965-2000 (hors SCAN 50).
- **Prix DVF = mutation entière** : une vente couvrant plusieurs parcelles affiche le prix total, pas la quote-part de la parcelle. Dit à l'écran mais facile à mal lire.
- **« Parcellaire de l'époque » ne couvre que les mères DISPARUES** captées dans `cadastre_historique` (6 526 lignes) : pour les 3 parcelles témoins, `features` = 0 (le message « pas de parcellaire d'époque » s'affiche). Cadastre plein écran d'époque non servi (choix minimal, `TimeMachine.tsx:80-81`).
- **Recouvrement DVF non borné** : l'union `dvf_mutations_parcelle` (2021→2025) + `dvf_mutations_histo` (2014→2020) n'a « 0 recouvrement vérifié » (`moteurs.py:455`). Rejoué en base : histo s'arrête au 2020-12-31, vivante démarre au 2021-01-01 → pas de doublon ici, mais rien ne le garantit en dur.

## 7. Les tests

- `frontend/src/components/outils/TempsMillesimes.test.tsx` : garantit que la frise expose 1950-65 + ≥ 2 autres millésimes, que chaque millésime a un fond réel et un libellé résolu, et que désigner une parcelle pose l'épingle dans le store (`tempsPinIdu`) et met à jour `cmpLeft`. Ne teste PAS le rendu carte (maplibre stubé).
- `frontend/src/components/map/basemaps.test.ts` : `ORTHO_YEARS` = Actuelle + les millésimes de `TEMPS_MILLESIMES` (source unique), `activeBasemapKey` rend chaque millésime sélectionnable, attributions portent le millésime, toutes les sources passent par le proxy.
- `frontend/src/components/outils/HistoireFrise.test.tsx` : un repère par fait, marqueur par famille, bandeau des millésimes, détail au clic à la bonne maille (« 2021 année seule » ≠ « 01/01/2021 »), pont Permis, PM avant→après, écart de millésimes, état vide honnête. **Teste un composant qui n'est pas affiché** (voir rubrique 6).
- `tests/test_outils_muscler2.py` : gardes de `/moteurs/histoire` — 4 familles à leurs mailles, tri du plus récent, dédup mutation multi-lignes, découpe groupée + cap, 404 parcelle inconnue, pseudo-SIREN → aucun changement affirmé, E2 vente avant découpe → mention mère.
- `parcellaire-epoque` : testé indirectement dans `tests/test_retours21_lotB.py` et `tests/test_retours14_carte.py`.

**Ce qu'aucun test ne vérifie** : (1) que la frise des faits est réellement RENDUE dans l'application (elle ne l'est pas, et aucun test ne le détecte) ; (2) que les tuiles ortho IGN répondent réellement (couches servies au 974) — testé seulement à la main ici ; (3) l'absence de recouvrement entre DVF vivante et histo.

## 8. Les documents liés (PDF, exports)

Aucun. L'outil « Remonter le temps » n'a ni PDF ni export : c'est une vue interactive (comparateur d'images + frise). Les ponts de la frise (chemin A) renvoient vers d'autres outils (Permis, fiche-ventes, Scan patrimoine) qui ont leurs propres documents, mais l'outil lui-même ne génère rien à imprimer. Donc pas de question « le PDF lit-il les mêmes valeurs que l'écran ».

## 9. Trois cas rejoués

Serveur relancé localement sur `:7300` (il ne tournait pas au départ : HTTP 000 ; relancé avec le venv parent + DB `openclaw@labuse`, `health` 200). `/moteurs/histoire/{idu}` et `/moteurs/parcellaire-epoque/{idu}` rejoués sur les 3 témoins.

- **97411000BZ1065 (Saint-Denis)** — `histoire` : `n=1`. Un seul fait, famille `decoupe`, maille `jour`, **1994-07-05**, « Parcelle issue d'un document d'arpentage ». Confirmé en base : `dfi_filiation` idu_fille=97411000BZ1065, idu_mere=97411000BZ0811, date 1994-07-05. Conforme à l'attendu du briefing (« 1 fait daté 1994 »). `parcellaire-epoque` : `features=0` (pas de mère captée dans `cadastre_historique`).
- **97409000AK0804 (Saint-André)** — `histoire` : `n=3`. (1) `proprietaire` millésime, année 2025, « Changement de propriétaire (personne morale) ». (2) `vente` jour 2024-12-26, « Local industriel. commercial ou assimilé », prix **1,0 €**, surface terrain 27 862 m² (prix symbolique 1 € = mutation particulière, servie telle quelle). (3) `decoupe` jour 2005-10-25, document d'arpentage. `parcellaire-epoque` : `features=0`.
- **97415000DH0076 (Saint-Pierre/-Joseph sud)** — `histoire` : `n=14`, toutes des ventes DVF de 2014 à 2024 (ex. 2024-12-19 Appartement 370 000 € 61 m² ; 2023-04-21 Maison 820 000 € 80 m² ; 2014-05-19 Appartement 230 000 € 40 m²). Démontre l'union vivante+histo (2014→2020 vient de `dvf_mutations_histo`). `parcellaire-epoque` : `features=0`.

Bandeau sources (identique pour les 3) : DVF (DGFiP) → **2025-12-31** · Sit@del (SDES) → **2026-08-31** · Fichiers fonciers PM (DGFiP) → **millésimes 2019→2025** · DFI (DGFiP) → **2025-12-29**.

Tuiles ortho (chemin B) rejouées sur St-Denis z15 (21431/18328) : les 7 millésimes de la frise + express répondent 200 avec des images non vides (23 à 176 ko) ; SCAN 50 1950 = 200/24 728 o ; EduGéo 1980 (hors frise) = 200 mais 852 o (quasi vide).

## 10. Tes doutes

1. **(GRAVE) Le chemin A — la frise des faits datés — n'est affiché nulle part dans l'application servie.** `HistoireFrise` n'a aucun consommateur vivant (seul un commentaire dans `TimeMachine.tsx:9` en parle, au passé) ; `App.tsx:506` ne rend que le comparateur. Pourtant l'endpoint fonctionne, le composant est pleinement testé, et la carte du menu annonce toujours « la frise des faits datés + le comparateur d'orthos » (`registry.ts:117`). L'utilisateur ne voit donc JAMAIS les ventes/permis/découpes datés dans cet outil, alors que la moitié du mandat porte là-dessus. À confirmer avec un essai navigateur (non fait ici), mais le code est sans ambiguïté.
2. **(MOYEN) Fonds ortho = flux IGN en direct sans cache ni garantie.** Un changement de nommage de couche côté IGN (le code anticipe `RVB-EXPRESS.*` dès 2026, `ortho_proxy.py:54`) ou une panne casse les fonds anciens silencieusement (proxy muet → aplat), sans alerte à l'utilisateur. Aucun test automatique ne vérifie que les couches historiques répondent réellement au 974.
3. **(MOYEN) Prix DVF = mutation entière, pas la part de la parcelle.** La mention « (mutation entière) » est présente, mais pour une vente multi-parcelles (fréquent sur du terrain), un prix affiché peut être très au-dessus de la valeur de la seule parcelle regardée — risque de lecture faussée.
4. **(FAIBLE) Trous de couverture temporelle.** Rien entre 1965 et 2000 en ortho (hors SCAN 50 de 1950) ; EduGéo 1980 retiré ; cadastre d'époque seulement ≥ 2016 et seulement pour les mères disparues (0 feature sur les 3 témoins). La frise suggère une continuité qu'elle n'a pas.
5. **(FAIBLE) Recouvrement DVF vivante/histo non borné en dur.** Le code note « 0 recouvrement vérifié » ; rejoué, les plages ne se chevauchent pas (histo ≤ 2020-12-31, vivante ≥ 2021-01-01), mais aucune contrainte ni test ne l'empêche — un futur ré-ingest pourrait produire des ventes en double.
