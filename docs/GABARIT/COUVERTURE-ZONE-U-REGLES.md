# Zones U — règles chiffrées validées, par commune

Suite de [COUVERTURE-ILE.md](COUVERTURE-ILE.md). Lecture seule, aucune écriture. Branche
`audit/gabarit-couverture` (main `297b2dbd`). Script : `scripts/gabcouv_zoneU_regles.py`.

## Méthode

Pour chaque commune, énumération des **codes de zone U réellement portés par des parcelles**
(`parcel_zone_plu.zone_fam='U'`, la dominante par surface = celle de l'écran) avec le nombre de
parcelles. Pour chaque code, les 4 familles réglementaires sont lues via `regles_zone` (config validée
`config/plu_destinations/*.yaml`) + `resolve_zone` (le moteur du builder) et classées :

- **chiffrée** = statut `valide` **avec** une valeur numérique (ou alignement = 0, ou CES « silence
  prouvé ») → servie ;
- **val.✎** = statut `valide` **sans** nombre (ex. hauteur en prospect, formule non transcrite) ;
- **—** = absente / non validée.

`calibree` = le portillon du builder : une zone `calibree=False` est **toujours bloquée** (« PLU non
calibré »), quelles que soient les feuilles présentes.

⚠ **CES = —** sur une zone **calibrée** ne bloque PAS : le builder la sert en « silence prouvé du
règlement » (« emprise non réglementée »). Vérifié sur La Possession UB (CES=— → **servie**). Les vrais
bloqueurs parmi les zones calibrées sont : recul voie/sep absent, ou **hauteur validée sans valeur
exploitable** (cas Salazie, motif builder « hauteur réglementaire non validée »).

## Synthèse — 306 630 parcelles zone U, 254 codes de zone, 23 communes

| Mesure | Zones | Parcelles | % des parc. U |
|---|---|---|---|
| **Zones U sans AUCUNE règle** (0/4 familles) | **20** | **7 407** | 2,4 % |
| **Zones U non calibrées** (`calibree=False` → bloc systématique) | **21** | **20 994** | **6,8 %** |

Les deux ensembles se recoupent partiellement. Le blocage « PLU » de la couverture (≈ 32 % des
bloquées de l'échantillon) vient de ces zones **plus** des zones calibrées à qui il manque une famille
(CES ou hauteur non chiffrée, ni « silence prouvé » → bloc), dont **Salazie** est l'exemple type.

### Par commune (les 23)

| Commune | parc U | zones U | sans règle (z/p) | non calibrée (z/p) |
|---|---|---|---|---|
| Saint-Benoît | 14 528 | 6 | 1 / 301 | **6 / 14 528** |
| Saint-Denis | 34 440 | 22 | 2 / 3 607 | 4 / 3 652 |
| Sainte-Rose | 3 170 | 5 | 1 / 1 565 | **1 / 1 565** |
| Saint-Leu | 14 931 | 13 | 7 / 965 | 7 / 965 |
| Le Port | 9 984 | 13 | 5 / 876 | 1 / 111 |
| La Possession | 10 386 | 16 | 1 / 1 | 2 / 173 |
| Petite-Île | 6 452 | 11 | 2 / 89 | 0 |
| Les Avirons | 5 194 | 15 | 1 / 3 | 0 |
| Salazie | 2 584 | 5 | 0 | 0 *(mais hauteur validée sans valeur → bloc, cf. focus)* |
| Bras-Panon, Cilaos, Entre-Deux, L'Étang-Salé, La Plaine-des-Palmistes, Le Tampon, Les Trois-Bassins, Saint-André, Saint-Joseph, Saint-Louis, Saint-Paul, Saint-Pierre, Sainte-Marie, Sainte-Suzanne | — | — | **0** | **0** |

14 communes sur 23 n'ont **aucune** zone U sans règle ni non calibrée. Saint-Philippe est absente
(RNU, pas de zone U).

## Détail des communes à trous (zones U et 4 familles)

Légende : valeur = mètres (voie/sep), mètres faîtage (haut), % (CES) ; `val.✎` = validée non chiffrée ; `—` = absente.

### Saint-Benoît (97410) — 14 528 parc U, 6 zones — **0 % servie**

| Zone | parc | voie | sep | haut | CES | |
|---|---|---|---|---|---|---|
| Ub | 10 143 | — | — | — | 80 | NON CALIBRÉE |
| Ua | 3 762 | — | — | — | 80 | NON CALIBRÉE |
| Uap | 301 | — | — | — | — | AUCUNE RÈGLE |
| Ue | 301 | — | — | — | 80 | NON CALIBRÉE |
| Up | 19 | — | — | — | 80 | NON CALIBRÉE |
| Ut | 2 | — | — | — | 80 | NON CALIBRÉE |

**Toutes les zones U sont non calibrées** : seule la CES (80 %) est présente, aucun recul ni hauteur.

### Sainte-Rose (97419) — 3 170 parc U, 5 zones — 21 % servie

| Zone | parc | voie | sep | haut | CES | |
|---|---|---|---|---|---|---|
| Uc | 1 565 | — | — | — | — | AUCUNE RÈGLE (dominante !) |
| Ua | 975 | 4 | 3 | 12 | 70 | complète |
| Ub | 595 | 4 | 3 | 12 | 60 | complète |
| Ud | 32 | 4 | 3 | 7 | 50 | complète |
| Ue | 3 | 4 | 5 | 14 | 70 | complète |

Ua/Ub/Ud/Ue sont **entièrement calibrées** ; c'est **Uc**, la zone dominante (1 565 parc.), qui n'a
aucune règle → les 79 % de bloquées de la commune.

### Salazie (97421) — 2 584 parc U, 5 zones — 0 % servie MALGRÉ des règles

| Zone | parc | voie | sep | haut | CES | |
|---|---|---|---|---|---|---|
| UB | 1 558 | 3 | 3 | val.✎ | — | bloc : hauteur |
| UC | 461 | 3 | 3 | val.✎ | — | |
| UA1 | 330 | 3 | 3 | val.✎ | — | |
| UA | 234 | 3 | 3 | val.✎ | — | |
| UT | 1 | 3 | 3 | val.✎ | — | |

Salazie a **voie 3 m + séparatives 3 m** partout et la CES servie en silence, mais la **hauteur est
validée sans valeur exploitable** (transcrite `statut=valide` sans nombre ni forme prospect reconnue).
Motif builder vérifié sur 6 parcelles UB : **« hauteur réglementaire non validée »** (6/6). D'où 0 %
servie sans qu'aucune zone ne soit « non calibrée » — c'est la hauteur, pas la CES.

### Saint-Denis (97411) — 34 440 parc U, 22 zones (extrait des trous)

`Uavap` (3 507 p) et `Uip` (100 p) = aucune règle ; `Uma` (37 p), `Udo` (8 p) = non calibrées ;
plusieurs zones `Uva/Uvl/Uvac/Udp/Upr` sans recul voie/sep mais avec hauteur/CES. Les 3 grandes zones
(`Um` 11 658, `Ui` 6 096, `Uh` 5 550) sont complètes → Saint-Denis reste à 72 %.

### Saint-Leu (97413) — 7 zones sans règle (965 p)

`UCA` (842), `UAA` (57), `UCC` (27), `UDP` (20), `UAT` (8), `UDB` (7), `UFe` (4) = aucune règle ; les
grandes zones UC/UD/UB/UA sont complètes.

### Le Port (97407) — 5 zones sans règle (876 p) · La Possession, Petite-Île, Les Avirons

Le Port : `Ue`(440), `Uv`(177), `Uoap`(111), `Up`(96), `Uppp`(52) = aucune règle. La Possession : ses
zones sont **servies** malgré CES=— (silence prouvé — vérifié : La Possession UB servie) ; seules
`UAv`(172, non calibrée) et `Up`(1, aucune règle) bloquent → 70 % servie. Petite-Île : `UF`(81),
`UFcim`(8) sans règle. Les Avirons : `Ub5`(3) seul sans règle, sinon complètes (séparatives 1,9 m).

## Les 3 communes visées — règlement PDF en base ?

Toutes trois ont bien leur **règlement PDF en base** (`plu_reglement_extrait`), mais la **calibration**
(`config/plu_destinations`) est indépendante de cette table — Saint-André, servie à 95 %, a d'ailleurs
**0 extrait** : la calibration est une transcription manuelle du texte, pas une lecture de cette table.

| Commune | PDF en base | doc | extraits | qualité |
|---|---|---|---|---|
| Saint-Benoît | oui | `97410_reglement_20200206.pdf` | **8** | **extraction ratée** — tous `zone=None`, articles « Section 1/2 » : **aucun article de recul par zone** capté |
| Salazie | oui | `97421_reglement_20220524.pdf` | 93 | articles par zone présents (U 6/7/10…) |
| Sainte-Rose | oui | `97419_reglement_20190504.pdf` | 141 | articles par zone présents (UA/Ub… 6/7/10…) |

### À quoi ressemble le texte des articles de recul

- **Salazie — `ARTICLE U 6`** (p. 12) : « IMPLANTATION DES CONSTRUCTIONS PAR RAPPORT AUX VOIES ET
  EMPRISES PUBLIQUES — 6.1 Champ d'application et définition : Les dispositions du présent article
  s'appliquent aux voies et emprises publiques ou privées ouvertes à la circulation générale
  (automobile, piéton, cycle)… L'alignement désigne la limite… » (+ `ARTICLE U 7` séparatives,
  `ARTICLE U 10` hauteur). **Le texte de recul/hauteur EXISTE et est chiffrable** — il n'est simplement
  pas transcrit en `config/plu_destinations` : c'est la **hauteur restée `val.✎`** (sans nombre) qui
  bloque Salazie ; la CES non renseignée, elle, est servie en silence prouvé.
- **Sainte-Rose — `ARTICLE UA 6`** (p. 12) : même structure « IMPLANTATION … VOIES ET EMPRISES
  PUBLIQUES » ; `ARTICLE A7` (p. 69, zones A) : « Les constructions doivent être implantées **en
  retrait des limites séparatives**. Le retrait … compté horizontalement de tout point de la façade au
  point le plus proche… ». Les zones Ua/Ub/Ud/Ue sont déjà transcrites ; **Uc** (dominante) ne l'est
  pas alors que son article existe dans le PDF.
- **Saint-Benoît** : le PDF est en base mais l'**extraction n'a produit que 8 fragments de niveau
  « Section »**, sans article de recul par zone — il n'y a donc **rien à montrer** côté extraits, et la
  config U est vide. La règle existe dans le PDF source mais n'a été ni extraite ni transcrite.

## Conclusion (rien corrigé)

Le mur de couverture en zone U n'est **pas** géométrique mais **PLU** : ~21 000 parcelles U (6,8 %) en
zones non calibrées (Saint-Benoît 14 528, Saint-Denis 3 652, Sainte-Rose Uc 1 565, Saint-Leu 965…),
plus quelques zones calibrées à **hauteur validée sans valeur** (Salazie, 2 584). La CES manquante ne
bloque pas (silence prouvé servi). Trois gestes possibles (hors mandat) : (1) **transcrire** hauteur
(Salazie) et les articles de Sainte-Rose Uc (texte en base) ; (2) **relancer l'extraction** du PDF de
Saint-Benoît (ratée, 8 fragments) puis transcrire ses 6 zones ; (3) transcrire les zones « aucune
règle » des grandes communes (Saint-Denis `Uavap` 3 507, Saint-Leu `UCA` 842).
