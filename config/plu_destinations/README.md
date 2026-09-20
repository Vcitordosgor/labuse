# Calibration DESTINATIONS par commune (DESTINATIONS-1)

Un YAML par commune : `<insee>_<slug>.yaml` (ex. `97411_saint_denis.yaml`), lu par le
module unique `src/labuse/plu/destinations.py`. Une commune sans fichier ici est
« non calibrée » (les surfaces l'affichent, jamais un silence). `rnu.yaml` porte la
calibration du règlement national d'urbanisme (Saint-Philippe).

Référentiel : art. R151-27 / R151-28 du code de l'urbanisme, version en vigueur depuis
le 01/07/2023 (décret n° 2023-195) — 5 destinations, 23 sous-destinations (slugs dans
`destinations.py`).

## Schéma

```yaml
meta:
  insee: "97411"
  commune: "Saint-Denis"
  document: "97411_reglement_20260805.pdf"      # pièce écrite lue (nom GPU)
  document_gpu: "97411_PLU_20260805"            # idurba du document GPU au calibrage
  gpu_doc_id: "…"                               # id API GPU (retélécharger la pièce)
  url: "https://data.geopf.fr/annexes/gpu/documents/DU_97411/…/97411_reglement_20260805.pdf"
  md5: "…"                                      # empreinte du PDF lu (garde-fou)
  millesime: "2026-08-05"
  pages_total: 154
  lu_le: "2026-09-03"
  structure: "texte court : comment le règlement organise interdits/autorisés"

zones:
  UA:
    silence: autorise            # ce que vaut le SILENCE dans cette zone :
    silence_src: "Art. UA1…"     #   lu dans la STRUCTURE du règlement, cité (jamais déduit)
    sous_destinations:
      industrie:
        statut: interdit                    # autorise | interdit | sous_condition
        article: "UA1"
        page_pdf: 10                        # page du PDF cité (lien vérifiable #page=N)
        citation: "« … » (mot à mot si utile)"
      artisanat_commerce_detail:
        statut: sous_condition
        condition: "surface de vente limitée à 300 m²"
        seuil_m2: 300
        seuil_type: surface_vente           # surface_vente | surface_plancher | emprise_sol
        article: "UA2"
        page_pdf: 11
      regles:                               # PLU-CALIBRAGE-1 — règles CHIFFRÉES (sœur de sous_destinations)
        hauteur:                            # les trois séparément (R151-39/40)
          faitage: { m: 15, article: "UA10", page_pdf: 12, citation: "« … 15 m au faîtage »", statut: propose }
          egout:   { m: 12, article: "UA10", page_pdf: 12, citation: "« … 12 m à l'égout »",  statut: propose }
          niveaux: { r_plus: 3, article: "UA10", page_pdf: 12, citation: "« R+3 maximum »",   statut: propose }
        emprise_sol:
          ces: { pct: 60, article: "UA9", page_pdf: 11, citation: "« emprise au sol … 60 % »", statut: propose }
        retraits:                           # chacune : formule (texte) + min_m
          voie:                { formule: "H/2 min 3 m", min_m: 3, article: "UA6", page_pdf: 10, citation: "« … »", statut: propose }
          limites_separatives: { formule: "H/2 min 3 m", min_m: 3, article: "UA7", page_pdf: 10, citation: "« … »", statut: propose }
        stationnement:
          par_logement: { places: 2, article: "UA12", page_pdf: 13, citation: "« 2 places par logement »", statut: propose }
          par_m2_sdp:   { places: 1, par_m2: 25, article: "UA12", page_pdf: 13, citation: "« 1 place / 25 m² SDP »", statut: propose }
          par_typologie: { detail: [ { typologie: "T1-T2", places: 1 }, { typologie: "T3+", places: 2 } ],
                           article: "UA12", page_pdf: 13, citation: "« … »", statut: propose }
        mixite:                             # feuille PLATE (seuil + quota + portée)
          seuil_logements: 30
          seuil_m2: null
          quota_pct: 15
          portee: zone                      # zone | oap | dispositions_generales
          article: "UA2", page_pdf: 9, citation: "« … 30 logements … 15 % … »", statut: propose
        # silence prouvé (jamais une case vide ambiguë) :
        # emprise_sol: { ces: { absent: true, article: "UA9", page_pdf: 11, citation: "« non réglementé »", statut: propose } }
  1AUa:
    renvoi: UA                              # seulement si le règlement le DIT
    renvoi_src: "caractère de zone, p. 60 : « se reporter au règlement de la zone UA »"
  N:
    etat: non_lu                            # zone identifiée mais pas encore lue
```

### Le bloc `regles` (PLU-CALIBRAGE-1)

Sœur de `sous_destinations`, `regles:` porte les règles **chiffrées** de la zone — celles que
le calcul de capacité affichait « ESTIMÉ ». Cinq rubriques, chacune en **feuilles** nommées ;
une feuille est une règle atomique. Lues par `src/labuse/plu/destinations.py`
(`regles_zone(commune, zone)`, `regles_commune(commune)`, `iter_regles_calibrees()`).

| rubrique | feuilles | valeurs portées |
| --- | --- | --- |
| `hauteur` | `faitage` · `egout` · `niveaux` | `m` (faîtage/égout) · `r_plus` (R+n) |
| `emprise_sol` | `ces` | `pct` (ou `m2` si valeur absolue) |
| `retraits` | `voie` · `limites_separatives` | `formule` (texte, ex. « H/2 min 3 m ») + `min_m` |
| `stationnement` | `par_logement` · `par_m2_sdp` · `par_typologie` | `places` · `par_m2` · `detail[]` |
| `mixite` | *(feuille plate)* | `seuil_logements`\|`seuil_m2` + `quota_pct` + `portee` |

Chaque feuille porte **article + page_pdf + citation** et un `statut` ∈ `propose` \| `valide` ;
`propose` = écrit par l'agent (`labuse plu extraire`), `valide` = tranché à la revue
(`labuse plu revue`). Le **verrou V6a** interdit toute feuille `valide` sans article + page_pdf
+ citation.

- **Silence du règlement** : `absent: true` avec la citation qui le PROUVE (« non réglementé »),
  `statut` et article/page compris — jamais une case vide.
- **Règle non trouvée** : la feuille est **absente du YAML** (distinct de `absent: true`, qui
  affirme le silence, citation à l'appui). Rien n'est inventé.
- **Renvoi** : un secteur qui renvoie ses *destinations* à sa zone mère peut porter ses
  *règles chiffrées propres* — `regles_zone` lit d'abord les règles de la zone, ne suit le
  `renvoi` que si la zone n'a AUCUNE règle à elle.

#### Les deux générations de PLU (art. 6-12 ↔ chapitres thématiques)

Avant la modernisation (décret n° 2015-1783, PLU prescrits/révisés à compter du 01/01/2016),
le règlement numérote des **articles 1 à 16** par zone ; après, il s'organise en **chapitres
thématiques** (usage / caractéristiques urbaines, architecturales, environnementales,
paysagères / équipements et réseaux — art. R151-17, R151-27 à R151-50). Une rubrique `regles`
se lit dans l'une ou l'autre ; la feuille cite l'article/chapitre **réel** du document
(`CORRESPONDANCE_GENERATIONS` dans `destinations.py`) :

| rubrique | articles 6-16 (avant 2016) | chapitres thématiques (après) |
| --- | --- | --- |
| `hauteur` | art. 10 (hauteur max.) | Volumétrie et implantation — hauteur |
| `emprise_sol` | art. 9 (emprise au sol) | Volumétrie et implantation — emprise |
| `retraits` | art. 6 (voies/emprises publiques) + art. 7 (limites séparatives) | Volumétrie et implantation — implantation |
| `stationnement` | art. 12 (stationnement) | Équipements et réseaux — stationnement |
| `mixite` | servitude de mixité sociale (art. 2 / dispositions générales, L151-15/L151-41 4°) | Usage des sols — mixité sociale (L151-15) / OAP |

Doctrine (identique aux `plu_<slug>.yaml` de constructibilité) :

- chaque valeur cite **article + page_pdf** du document `meta.document` ; rien de déduit ;
- une sous-destination absente de `sous_destinations:` = **non mentionnée** par le
  règlement → le verdict effectif découle de `silence:` (autorisé/interdit), lui-même
  cité ; distinct de `non_lu` (pas encore lu) ;
- les règlements antérieurs à la nomenclature R151-28 parlent en « occupations et
  utilisations du sol » : on mappe UNIQUEMENT ce que le texte porte (citation à l'appui),
  le reste demeure non mentionné ;
- verrou CDAC (L752-1 code de commerce, > 1 000 m² de surface de vente) : règle statique
  portée par le module, PAS par ces fichiers.
