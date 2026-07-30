# MANDAT GPU-PILOTE — PHASE 2, EXTRACTION (L'Étang-Salé 97404)

> Fichier d'extraction produit : **`config/calibrage/extraction_l_etang_sale.yaml`** (NEUF, à côté
> du calibrage existant — ce dernier n'est PAS modifié). Rien écrit en base, aucun re-scoring.
> Sources : règlement `97404_reglement_20250917.pdf` (106 p.) + OAP (25 p.), archive EN VIGUEUR.

## Contrôle de validité — les 3 faits RETROUVÉS sans qu'on les souffle

| Fait imposé | Retrouvé | Verbatim / source |
|---|---|---|
| **AUs fermée** | ✅ | « Ces espaces non équipés sont inconstructibles. Ils ne pourront être ouverts à l'urbanisation qu'à l'occasion d'une procédure de modification ou de révision du PLU. » — AU caractère de zone, **p.75** |
| **AUa/b/c : 10 log min + densité 50/30/15 log/ha** | ✅ | « à condition qu'elles s'insèrent dans des opérations d'ensemble comportant un minimum de **10 logements** […] avec une **densité minimale de 50 log/ha (AUa), 30 (AUb) et 15 (AUc)**, sauf dispositions […] dans les Orientations d'Aménagement » — AU 1.2 §1, **p.75** |
| **VRD internes ET externes à la charge de l'opérateur** | ✅ | « Les équipements d'infrastructures indispensables […], qu'ils soient **internes ou externes** à celle-ci, sont **à la charge exclusive de l'opérateur** » — AU 1.2, **p.75** |

Le schéma et la méthode tiennent : les 3 faits sont dans le texte, extraits avec article + page.

## L'écart — ce que le YAML dit vs ce que le règlement dit

| Champ | YAML actuel (`plu_l_etang_sale.yaml`) | Règlement (extraction Phase 2) | Écart |
|---|---|---|---|
| AU dimensions (hauteur, emprise, reculs) | présent, sourcé | identique | **aucun** — le YAML est juste |
| AUs gel | présent (`zones_au_st`) | fermée, verbatim p.75 | comblé (verbatim + voie d'ouverture ajoutés) |
| **Planchers 10 log + densité 50/30/15** | **absent** | AU 1.2 §1 p.75 | **COMBLÉ** — nouveau (§C) |
| **VRD internes+externes opérateur** | **absent** | AU 1.2 p.75 | **COMBLÉ** — nouveau (§F) |
| Mixité sociale AUa/AUb | « 20% si >1000 m² SDP » (présent) | idem MAIS « ne s'applique pas si OAP » | **précisé** : l'OAP prévaut |
| **Densité/social réels par site (OAP)** | **absent** | OAP p.5-25 | **COMBLÉ** — nouveau (§H) |
| Perméabilité / espace vert par secteur | partiel | AU 2.6 p.82 (20-30% EV, 30-40% perméable) | complété |
| Destinations autorisées/interdites | absent | AU 1.1/1.2 p.75-76 | complété (shapefile DEST* vide) |

**Conclusion Mission 1** : les deux gisements annoncés (planchers de densité, VRD externes) n'étaient
NI dans le zonage NI dans le YAML — uniquement dans le texte. Ils sont maintenant extraits, sourcés,
verbatim. Une parcelle en AUc isolée (< 10 logements) est **inconstructible seule** malgré une zone
ouverte : ce fait n'existait nulle part avant cette extraction.

## Ajout 1 — l'OAP prévaut sur le règlement (finding structurant)

Le règlement pose des densités *blanket* (50/30/15) MAIS **renvoie explicitement à l'OAP** (« sauf
dispositions particulières définies dans les Orientations d'Aménagement », p.75 ; « [les 20% social]
ne s'applique pas dans les zones AU faisant l'objet d'une OAP », p.76). L'OAP, opposable, donne des
valeurs **par site** qui diffèrent :

| Site OAP | zone | densité OAP | % social OAP | vs règlement |
|---|---|---|---|---|
| AUa Le Stade (p.7) | AUa | 50 log/ha | **50%** | densité = ; social 50% > 20% |
| AUb Amont ZAC Collège (p.5) | AUb | 30 log/ha | 25% | densité = ; social 25% > 20% |
| AUb RHI Butte Citronnelle aval (p.9) | AUb | **50 log/ha** | 50% | densité 50 > blanket 30 |
| AUb RHI amont (p.11) | AUb | 30 log/ha | 50% | social 50% > 20% |
| AUc Ravine Sheunon (p.13) | AUc | **30 log/ha** | 25% | densité 30 > blanket 15 |
| AUc Le Lambert (p.15) | AUc | non chiffré | non chiffré | **a_verifier** (texte muet) |
| AUt Le Golf / AUe Les Sables / AUs | — | tourisme/éco/gel | — | pas de densité logement |

→ **Sans l'OAP, la constructibilité réelle (plancher de densité par site) est inconnue.** Le §H de
l'extraction porte `oap_contenu_extrait` (oui/partiel) + `oap_prescriptions` + verbatim. Le cas
« Le Lambert » est marqué `a_verifier` (jamais supposé sans effet).

## Ajout 2 — lien d'annuaire construit, ouvert, CONFIRMÉ

URLFIC est vide à la source → le lien se construit et se **résout dynamiquement** :
1. Résolveur : `https://www.geoportail-urbanisme.gouv.fr/api/document?grid=97404`
2. Filtrer `effectiveStatus == "EN_VIGUEUR"` → `id = 7058f72863540b49692dd4e3c37085f8`
3. Téléchargement : `https://www.geoportail-urbanisme.gouv.fr/api/document/7058f72863540b49692dd4e3c37085f8/download`

**Test live (30/07)** : HTTP **200**, `application/zip` 11,4 Mo, redirige vers
`data.geopf.fr/telechargement/.../97404_PLU_20250917.zip` = **le document EN VIGUEUR** (publié
08/12/2025, orig. `97404_PLU_20250917`) — le bon document.

**Deux réserves à graver** :
- **Granularité** = archive DU entière, pas le PDF règlement seul à la page. L'annuaire cite
  l'article + la page en clair (verbatim), le lien pointe le document.
- **id NON stable** (change à chaque révision) → **résoudre à la volée via grid=97404, jamais
  coder l'id en dur**. Un lien codé en dur serait mort à la prochaine modification du PLU (« un lien
  mort est pire que pas de lien »).

## Ajout 3 — dette EBC/ER consignée (NON implémentée)

Consignée en dette #10 (`V8_DETTES_CONSIGNEES.md`). Rappel de la mesure Phase 1 : la brique EBC
(typepsc 01, 30 objets) / ER (typepsc 05, 15 objets) est en base, géo-jointe, mais n'est ni un
maillon de cascade ni un drapeau de fiche. Ta nuance est retenue : **intersecter ≠ inconstructible**.
La dette demande un DRAPEAU de fiche (« parcelle partiellement en EBC », « emplacement réservé n°X »),
pas une exclusion. Non implémenté ici.

## Couverture et limites honnêtes (§I)
- **AU** : couverture 80-95% par secteur (verbatims + pages). Non extraits : tableau stationnement
  complet (AU 2.7.3, partiellement illisible en texte), niveaux max, OAP « Le Lambert » chiffres.
- **U** : reportées du calibrage existant (dimensions + pages) ; destinations et verbatims intégraux
  NON extraits (couverture 40-60%) → phase 2bis si tu veux l'annuaire complet sur U.
- **A / N** : identité + constructibilité habitat seulement (hors cible produit) ; chapitres non relus.
- **Procédure** (0_Procedure) : non lue. **Servitudes** (liste_sup) : géométrie en base, texte non extrait.

## Point d'arrêt
Extraction rendue sur **L'Étang-Salé uniquement**. Rien écrit en base, YAML existant intact, aucune
autre commune. Les 3 faits de contrôle sont retrouvés. En attente de ton retour avant toute suite
(brancher les planchers/VRD/OAP dans la faisabilité, ou étendre à d'autres communes).
