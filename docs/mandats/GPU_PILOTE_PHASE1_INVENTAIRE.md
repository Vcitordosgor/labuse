# MANDAT GPU-PILOTE — PHASE 1, INVENTAIRE (L'Étang-Salé 97404)

> **Lecture seule. Aucune écriture, aucune ingestion, aucun re-scoring. POINT D'ARRÊT.**
> Archive : `97404_PLU_20250917.zip` (301 Mo, GPU du 17/09/2025). Base : DB `openclaw`, run servi
> `q_v7_defisc`. Tout vérifié par la donnée (shapefiles de l'archive + `spatial_layers` + le YAML).

---

## Tableau d'inventaire — source par source

| Source (archive) | Objets archive | En base ? | Ingéré comme | Ce qui SURVIT / ce qui est PERDU |
|---|---|---|---|---|
| **ZONE_URBA** | 78 zones | **OUI** | `plu_gpu_zone` (78) | garde `libelle` + `idurba` seulement. **DEST\*, URLFIC, TYPEZONE, LIBELONG, FORMDOMI perdus** |
| **PRESCRIPTION_SURF** | 88 | **OUI** | `plu_gpu_prescription` (88) | garde `typepsc/stypepsc/txt/libelle/url_source` + géométrie ✓ |
| **PRESCRIPTION_PCT** | 46 | **OUI** | `plu_gpu_prescription` (46) | idem (SURF+PCT fusionnés = 134) |
| **PRESCRIPTION_LIN** | *absent de l'archive* | — | — | l'archive n'en contient pas |
| **INFO_SURF** | 137 (assain. 81, captage 42, sols 8) | **PARTIEL/NON** | rien en `info_*` | captages (42) et aptitude sols (8) **ABSENTS** ; `zonage_assainissement`(20)/`water`/`sol_pollue` viennent d'AUTRES sources |
| **INFO_LIN / INFO_PCT** | *absents de l'archive* | — | — | l'archive n'en contient pas |
| **Règlement** `97404_reglement_20250917.pdf` | 106 p. | **OUI** (lu par le YAML) | `config/plu_l_etang_sale.yaml` | U complet ; AU dimensions + AUs gel ; **planchers + VRD absents** (voir contrôle) |
| **OAP** `5_Orientations_amenagement` | 1 PDF | **NON** (contenu) | — | 12 zones RENVOIENT à une OAP (via prescription `typepsc 18`), mais le CONTENU opposable n'est pas extrait |
| **Servitudes** `liste_sup` | 1 PDF | **PARTIEL** | `sup` (16 : pm1×14, ac3, el10) | géométrie SUP présente ; libellé/texte non extraits du PDF |
| **Procédure** `procedure` | 1 PDF | **NON** | — | date/type de procédure non en base |
| **URLFIC** (colonne) | — | **VIDE À LA SOURCE** | — | 0/78 zones, 0/134 presc, 0/137 info renseignés — voir Q7 |

**Source de l'ingestion actuelle = `API_CARTO_GPU` (API IGN), PAS ce ZIP.** L'archive téléchargée est
plus riche que ce que l'API a laissé passer, mais sur les DEST\*/URLFIC les deux sont vides.

---

## Réponses aux 7 questions

**Q1 — ZONE_URBA / DEST\*.** ZONE_URBA est en base (`plu_gpu_zone`, 78/78). Les colonnes
`DESTOUI/DESTCDT/DESTNON` sont **doublement absentes** : (a) **vides à la source** (0/78 renseignés
dans le shapefile de l'archive), et (b) **aucun emplacement à l'import** (les `attrs` ne gardent que
`libelle/idurba/partition/source`). Perte d'information : les destinations autorisées/conditionnelles/
interdites par zone n'existent NULLE PART en base — elles ne peuvent venir que du **règlement texte**.
Idem `TYPEZONE` (réduit à AUc/AUs, grossier), `LIBELONG` (dégénéré = `LIBELLE`), `FORMDOMI` (vide).

**Q2 — PRESCRIPTION_\* (la question la plus importante).** SURF (88) + PCT (46) = **134 ingérés**
(`plu_gpu_prescription`), avec `typepsc/stypepsc/txt` ET géométrie (`geom_2975`). Types :
`01`=**EBC** (30), `05`=**ER** (15), `02`=aléa PPR (8 : R1 fort, B2/R2 moyen, submersion),
`07`=case traditionnelle/patrimoine (47), `18`=**renvoi OAP** (12), `24` (16), `31` (6).
**Intersection parcelles servies ∩ bloquant** (9 070 parcelles L'Étang-Salé, run `q_v7_defisc`) :

| tier servi | total ∩ bloquant | dont EBC | dont ER | dont aléa |
|---|---|---|---|---|
| ecartee | 3 654 | 960 | 193 | 3 496 |
| a_creuser | 288 | 16 | 19 | 263 |
| **reserve_fonciere** | **13** | 0 | **2** | 11 |
| **chaude** | **3** | 0 | 0 | 3 |

→ **16 parcelles servies EN TÊTE** (3 chaudes + 13 réserve) intersectent un bloquant, toutes portées
par l'aléa (2 ER en réserve, 0 EBC en tête). La cascade écarte déjà l'essentiel (3 654 `ecartee`).
**Nuance à ne pas gommer** : intersecter ≠ inconstructible (un EBC/ER PARTIEL laisse du constructible)
— ces 16 sont des drapeaux À VÉRIFIER, pas des exclusions. La brique EBC/ER existe et est
géo-jointe ; elle n'est simplement pas encore un maillon de la cascade.

**Q3 — INFO_\*.** INFO_SURF (137) **quasi pas ingéré** : les captages (42) et l'aptitude des sols (8)
sont **absents** ; ce que la base porte (`zonage_assainissement` 20, `water` 127, `sol_pollue` 5)
vient d'autres sources, pas d'INFO_SURF. INFO_LIN/PCT absents de l'archive.

**Q4 — Règlement lu par le YAML.** `config/plu_l_etang_sale.yaml` a lu **la même archive**
(`97404_reglement_20250917.pdf`, GPU `97404_plu_20250917`, millésime **2025-09-17**, offset page −1).
**Pas de décalage de source.** Nuance : le YAML étiquette « approbation 2025-09-17 » qui est la date
d'ARCHIVE/publication GPU ; le règlement lui-même est *modifié le 04/12/2024* (contenu) — distinction
à conserver (millésime archive ≠ date de la pièce). Couverture : U complet (hauteur/emprise/reculs
sourcés à la page) ; AU dimensionnel + AUs=gel ; **manque** (voir contrôle).

**Q5 — OAP.** Le dossier `5_Orientations_amenagement` (PDF) **n'est pas exploité** (aucun contenu
d'OAP dans les configs). Mais **12 zones renvoient à une OAP**, connu via la prescription
`typepsc 18` (OAP AUa « Le stade », AUb « RHI Butte Citronnelle », AUe/AUs « Les Sables », AUt « Le
golf »…). Le LIEN zone→OAP est en base ; le CONTENU opposable de l'OAP, non.

**Q6 — Servitudes (`liste_sup`).** Géométrie SUP ingérée (`sup`, 16 : pm1×14 = PPR, ac3, el10), mais
libellé/texte NON extraits du PDF `liste_sup`. Partiel.

**Q7 — URLFIC.** **Vide à la source** (0 renseigné sur ZONE_URBA/PRESCRIPTION/INFO dans l'archive) →
ne peut PAS servir de lien d'annuaire tel quel. En base, `plu_gpu_zone` ne garde même pas la colonne ;
`plu_gpu_prescription.url_source` existe mais vaut l'**endpoint API générique**
(`https://apicarto.ign.fr/api/gpu/prescription-pct`), pas un lien de document citable. **Piste réelle** :
`NOMFIC` EST renseigné (`97404_reglement_20250917.pdf`) et le YAML porte déjà
`url: https://www.geoportail-urbanisme.gouv.fr/api/document?grid=97404` — le lien annuaire se
**construit** (grid + nom de fichier + page), il ne se lit pas dans URLFIC.

---

## Contrôle de validité (les 3 faits imposés) — **1/3 déjà en base**

| Fait de contrôle | Statut | Où |
|---|---|---|
| **AUs fermée** (réserve long terme, ouvrages techniques seuls) | ✅ **PRÉSENT** | YAML `zones_au_st`, gel, verbatim « AU 1.2 clause 11, p.77 » |
| **AUa/AUb/AUc : 10 logements min + densité 50/30/15 log/ha** | ❌ **ABSENT** | YAML n'a que densité générique 30 + mixité 20 % + note « opérations d'ensemble » ; aucun plancher |
| **VRD internes ET externes à la charge de l'opérateur** | ❌ **ABSENT** | aucune trace dans le YAML ni les configs |

Les deux manques sont exactement la cible de la Mission 1 : **planchers** (§C du format Phase 2) et
**charges opposables** (§F). Le zonage + les dimensions sont là ; ce qui rend une parcelle en zone
ouverte *non constructible seule* (seuil de densité minimale) et *plus chère* (VRD externes) ne l'est
pas. La Phase 2 doit les extraire du texte — ils ne sont dans aucune couche géographique.

---

## Ce qu'il faut décider avant la Phase 2 (ne PAS enchaîner)
1. **DEST\* vides à la source** → les destinations viendront du règlement (§G) ; le croisement
   « règlement vs DESTOUI/CDT/NON » demandé au §G sera *vide côté shapefile* ici — à acter.
2. **URLFIC vide** → le §J (annuaire) s'appuiera sur `grid=97404` + `NOMFIC` + page, pas sur URLFIC.
3. **EBC/ER géo-joints mais hors cascade** → la Phase 2 produit les faits ; leur branchement dans la
   cascade (faire d'un EBC/ER un bloquant) est un autre mandat (aucune écriture ici).
4. **OAP contenu non extrait** mais liens zone→OAP connus (12 zones) → le §H pourra les référencer ;
   l'extraction du texte d'OAP est à cadrer (PDF `5_Orientations_amenagement`).

**RIEN ÉCRIT, RIEN INGÉRÉ, RIEN CALIBRÉ. Attente du feu vert pour la Phase 2.**
