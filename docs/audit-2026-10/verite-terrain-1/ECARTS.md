# VERITE-TERRAIN-1 — ÉCARTS (revue manuelle)

Sur **500 parcelles × 8 sources** (10 024 comparaisons, dont 6 340 réellement comparables) **+ 336
règles chiffrées de PLU** relues au règlement officiel, le comparateur a d'abord levé une série de
candidats « LABUSE FAUX ». Comme l'exige le mandat, **chacun a été revérifié à la main** (appel
officiel rejoué, valeur servie retrouvée dans le code/la base, couche brute inspectée).

**Verdict : aucun écart « LABUSE FAUX » confirmé sur une valeur servie.** Un seul écart résiduel
est une **citation de page** à corriger (la valeur n'est pas infirmée). Tous les autres candidats
étaient des **artefacts du comparateur ou de la source**, pas des erreurs de LABUSE — et leur
correction a rendu l'audit honnête. Le détail de chaque disposition suit.

---

## 1. Écart résiduel à traiter (1)

### PLU — emprise zone Up, Saint-Pierre (`97416000EM0018`)
- **Servi** : emprise au sol max **60 %**, cité « Art. … · p.3 » du règlement
  `97416_reglement_20240625.pdf`.
- **Officiel** : la **page 3 est le préambule** du règlement ; la valeur « 60 % » n'y figure pas, et
  la recherche automatique ne l'a pas retrouvée pour la zone Up dans les 228 pages du PDF.
- **Nature** : **citation de page erronée** (le renvoi pointe le préambule, pas l'article d'emprise).
  La valeur 60 % n'est **ni confirmée ni infirmée** — elle est peut-être correcte mais mal citée.
- **À faire (hors mandat, lecture seule)** : revoir côté calibrage PLU la page citée pour l'emprise
  Up de Saint-Pierre ; confirmer la valeur 60 % sur la bonne page.
- **Trace** : `reglement_plu.zones[].regles_valeurs` (cle=`emprise`), fiche servie ; preuve
  `comparaisons_plu_regles.csv`.

---

## 2. Candidats levés puis REFUTÉS à la main (LABUSE correct)

Ces écarts venaient du **comparateur ou de la source**, pas de LABUSE. Chaque correction est dans le
code du comparateur (un commit par source).

| Candidat initial | Nb | Cause réelle (vérifiée) | Verdict final |
|---|---|---|---|
| `catnat_total` — LABUSE 20 vs GASPAR 21 (Saint-Joseph) | 25 | **GASPAR liste deux fois** le même arrêté `INTE1401216A` (2014-01-17). LABUSE a le bon compte distinct. | LABUSE correct ; ±2 au grain commune = méthode |
| `plu_zone` — « UC » vs « A », « N » vs « U4b », « A » vs « UB » | 4 | **Requête GPU au POINT** : sur une parcelle de lisière, le point tombe dans la zone minoritaire. En **surface**, LABUSE sert bien la zone **dominante** (UC 536 m² vs A 2,7 ; N 263 vs U4b 158 ; A 572 vs UB 538). | LABUSE correct (comparaison passée en aire-dominante) |
| `plu_zone` — « An » vs « N » | 1 | Parcelle **bizone** : LABUSE sert *toutes* ses zones (An **et** N) ; la dominante GPU en fait partie. | LABUSE correct |
| PLU règles — hauteur/recul « 4.5 », « 1.9 »… absents | 7 | **Virgule décimale** : le règlement écrit « 4,5 m », la fiche « 4.5 m ». Le nombre EST au règlement. | LABUSE correct (match virgule/point) |
| PLU reculs — « 1.9 m », « 3.5 m » non littéraux | 5 | Reculs **dérivés d'une règle de prospect** (H/2…) : valeur calculée, pas un nombre littéral du règlement. | Non comparable (dérivé), pas un faux |
| `aleas_presence` — LABUSE 1 aléa, Géorisques « aucun » au point | 1 | Le **rapport Géorisques au point** rate un aléa mouvement-de-terrain faible ; la **couche d'aléa brute** (DEAL) intersecte bien la parcelle. | LABUSE correct (corroboré par la couche brute) |
| `batiments_nb` — LABUSE > RNB | ~47 | **RNB est un registre en cours de complétude** : moins de bâtiments que BD TOPO = lacune RNB, pas sur-compte LABUSE. | Non comparable, pas un faux |
| `dvf_secteur_n_ventes` — recompte brut ≠ agrégat servi | ~30 | Le compte secteur est un **agrégat dérivé** (dédup, filtre qualité, appariement de type) ; un recompte brut diffère légitimement. | Non comparable (méthode), pas un faux |
| `adresse` — libellé BAN ≠ adresse servie | ~180 | Le **reverse au centroïde** ne peut pas réfuter une adresse rattachée (grande parcelle, voie voisine). | Non comparable, pas un faux |
| `proprietaire_denomination` — libellé DGFiP ≠ raison sociale INSEE | ~5 | **SIREN confirmé** ; la différence est de forme (SCI/SARL, trait d'union, renommage INSEE). | Non comparable, pas un faux |
| `surface_geometrie_m2` — 25 vs 26 m² | 1 | **Arrondi** sur une parcelle minuscule (plancher 3 m²). | LABUSE correct |

---

## Méthode de revue

Pour chaque candidat : (1) rejouer l'appel officiel en direct ou relire la couche brute ;
(2) retrouver la valeur servie et sa source (fiche `/parcels/{idu}`, table d'ingestion, couche
spatiale) ; (3) trancher **FAUX confirmé** / **fraîcheur** / **artefact de méthode ou de source**.
Les corrections de comparateur sont tracées dans les commits « Source N ». Rien n'a été écrit en
base ni sur le VPS.
