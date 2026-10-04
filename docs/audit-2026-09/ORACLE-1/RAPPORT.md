# ORACLE-1 — la fiche LABUSE face à la réalité publique et au regard d'un promoteur

**Branche** `audit/oracle-1` · worktree `~/Desktop/labuse-oracle` · lecture seule · API 8645 / front 5845.
Aucune écriture hors `docs/audit-2026-09/ORACLE-1/` et `scripts/coherence/oracles/`. Aucune correction appliquée, aucun mandat proposé hors des tableaux ci-dessous.

## Ce qui a été fait

20 parcelles tirées pour **mettre la fiche en difficulté** (gelées dans `PARCELLES.csv` : 16 communes ; U dense / U pavillonnaire / AU ouverte / AU fermée / A / N ; à cheval sur deux zones et sur deux communes ; PPR rouge / bleue / hors ; nue / bâtie ancienne / récente / copropriété ; personne physique / SCI / EPF / commune / indivision ; 50 pas / ravine / ligne HTA ; 1,7 m² / 44,9 ha ; permis récent / permis annulé ; vendue DVF < 2 ans ; établissement SIRENE). Pour chacune : le Dossier PDF et le JSON de la fiche sont archivés dans `dossiers/`.

- **Lot B** — chaque notion sourçable relue **hors LABUSE** (GPU API Carto, Géorisques, cadastre API Carto, DVF Etalab brut, BAN, IGN alti, SIRENE, RNB/BD TOPO WFS, INSEE, et le PDF du règlement PLU ouvert à la page citée). Livrable `VERITE.csv`.
- **Lot C** — chaque Dossier relu comme un promoteur (6 questions). Livrable `LECTURE.csv`.
- **Lot D** — les contrôles à source stable deviennent des oracles rejouables dans `scripts/coherence/oracles/`. Livrable `ORACLES.csv`.
- **Lot E** (demande en cours de mandat) — comparaison ligne à ligne **écran ↔ données servies ↔ Dossier PDF**, un tableau par parcelle (`lot_e_parts/`, synthèse ci-dessous).

**Accès réseau vérifié** (étape 0) : GPU API Carto, Géorisques, BAN, IGN alti (paramètre `resource=ign_rge_alti_wld` requis), DVF Etalab (miroir OVH), SIRENE recherche-entreprises, INSEE Melodi, cadastre Etalab, data.gouv — tous répondent. Instables : Géorisques `resultats_rapport_risque` (3-4 essais nécessaires) ; Sitadel open data non maillé à la parcelle (DiDO par commune×mois, millésime 2026-09 sous embargo) ; fichier PM DGFiP (bulk, pas d'API par parcelle) ; RGA argiles non couvert en DOM.

## Les chiffres

| | nombre |
|---|---|
| Parcelles | 20 |
| Notions distinctes vérifiées | 78 |
| **Lignes de vérité (Lot B)** | **488** |
| — vrai | 408 |
| — **faux** | **51** |
| — non vérifiable (dit, jamais silencieux) | 29 |
| Lignes de lecture promoteur (Lot C) | 120 (20 × 6 questions) |
| Oracles rejouables (Lot D) | 140 lignes · 67 vrai / 27 faux / 46 non vérifiable |
| Écarts écran↔PDF relevés (Lot E) | 284 « à l'écran, absent du PDF » · 280 « au PDF, absent de l'écran » |

Les 51 faux ne sont pas dispersés : **42 relèvent de trois défauts systémiques** (règles PLU, rayon DVF, contenance), reproductibles d'une commune à l'autre et désormais tenus par trois oracles.

---

## FAUX — en tête, avec la source qui contredit

### Défaut systémique n°1 — règles PLU affichées « non réglementé / à vérifier » alors que le règlement les fixe (18 faux · 9 parcelles)

La fiche et le PDF présentent recul sur voie, recul sur limites séparatives, pleine terre, stationnement, hauteur comme **« non réglementé »** ou **« estimé / à vérifier au règlement »**, alors que l'article correspondant du règlement PLU — ouvert au PDF à la page que LABUSE cite elle-même — fixe une valeur chiffrée. C'est le défaut le plus grave : un promoteur conçoit son implantation sur un « champ libre » qui ne l'est pas.

| parcelle | règle affichée « non réglementé/à vérifier » | ce que dit le règlement (vérifié dans le PDF) |
|---|---|---|
| S03 Saint-Paul AU1st | recul voie / recul limites | art. 6 et 7 : 5 m minimum (p.60-61) |
| S04 La Possession AUst | recul voie / recul limites | art. AUst 6 : 4 m ; art. AUst 7 : 3 m (p.82) |
| S07 Le Tampon Ud | recul voie / limites / pleine terre / stationnement | Ud6.2 : 4 m ; Ud7.1 : 3 m ; Ud13.2 : 40 % perméable dont pleine terre ; Ud12.2 : tableau de places (p.60-69) |
| S09 Le Port Uv | recul voie / stationnement | Uv4 : retrait 25 m RN1001 / 45 m RN4a (Barnier) ; Uv12 : 0,3 pl/logt + visiteurs |
| S10 Saint-André UC | stationnement | art. UC12 : barème complet par destination |
| S11 Saint-Leu UA | recul voie **4 m** | UA6.2 : rue du Général Lambert = alignement ou 2 m (le 4 m ne vaut que pour d'autres rues) |
| S15 Saint-Pierre Uaza | hauteur / stationnement | hauteur plafonnée (règlt p.178) ; art. Ua6 barème de stationnement |
| S16 Bras-Panon UE | stationnement | art. UE12.2 : 50 % SDP commerces/bureaux, 30 % artisanat |

### Défaut systémique n°2 — « N ventes à moins de 500 m » alors que le rayon réel est 1 000/1 500 m ou la commune (13 faux · 13 parcelles)

Le Dossier PDF (et parfois l'écran) annonce un prix médian appuyé sur « *N ventes à moins de 500 m* ». Or le rayon réellement servi (`prix_ancien.radius_m`) vaut **1 000 ou 1 500 m**, voire la commune entière (`commune_fallback=true`). Recalcul haversine sur le fichier DVF Etalab brut : dans presque tous les cas, **0 vente ne tombe réellement à ≤ 500 m**. La médiane elle-même est souvent exacte — c'est **le libellé de proximité qui est faux**, et il fait croire à une comparabilité de voisinage qui n'existe pas.

| parcelle | PDF annonce | réel à ≤ 500 m (DVF Etalab) | rayon réel servi |
|---|---|---|---|
| S03 Saint-Paul | 10 ventes < 500 m | 0 appartement | 1 500 m |
| S04 La Possession | 24 ventes < 500 m | 0 (534–1 487 m) | 1 500 m |
| S05 Saint-Benoît | 65 ventes < 500 m | 0 | commune |
| S08 Saint-Louis | 101 ventes < 500 m | 0 | commune |
| S09 Le Port | 31 ventes < 500 m | 8 | 1 000 m |
| S10 Saint-André | 35 ventes < 500 m | ~3 | 1 000 m |
| S12 Le Tampon | 10 ventes < 500 m | 0 | 1 500 m |
| S16 Bras-Panon | 15 ventes < 500 m | 1 | 1 500 m |
| S19 Salazie | 59 ventes < 500 m | 0 | 1 500 m / commune |
| S20 Sainte-Suzanne | 24 ventes < 500 m | 4 | 1 000 m |

(+ S07, S15, S17 : médiane de secteur recalculée divergente par la méthode d'agrégation.)

### Défaut systémique n°3 — la surface servie est l'aire géométrique du polygone, étiquetée « contenance » (11 faux · 11 parcelles)

LABUSE sert `surface_m2` = l'aire du contour PCI, et le Dossier PDF l'imprime sous le mot **« contenance »**. Or la contenance cadastrale officielle (API Carto cadastre, `properties.contenance`) en diffère. L'écart est souvent faible (< 1,5 %) mais dépasse parfois les 4-6 %, et devient absurde sur une micro-parcelle.

| parcelle | servi « contenance » | contenance cadastrale réelle | écart |
|---|---|---|---|
| S13 Les Avirons | 2 m² | 3 m² | −33 % |
| S07 Le Tampon | 5 916 m² | 6 478 m² | −8,7 % |
| S18 Petite-Île | 874 m² | 914 m² | −4,4 % |
| S04 La Possession | 5 526 m² | 5 280 m² | +4,7 % |
| S03 Saint-Paul | 5 521 m² | 5 754 m² | −4,0 % |
| S19 Salazie | 1 610 m² | 1 710 m² | −5,8 % |
| S02 Saint-Leu | 622 m² | 646 m² | −3,7 % |
| S17 Saint-Benoît | 856 m² | 882 m² | −2,9 % |
| S15 Saint-Pierre | 1 113 m² | 1 273 m² | −12,6 % |
| S10 Saint-André | 10 682 m² | 10 556 m² | +1,2 % |
| S14 Les Avirons | 466 m² | 440 m² | +5,9 % |

### Autres faux (8)

| parcelle | notion | la source qui contredit |
|---|---|---|
| **S20 Sainte-Suzanne** | **permis = « caduc / constructibilité prouvée »** | Le permis a `etat=4` = **ANNULÉ** dans le référentiel LABUSE lui-même (`historique_site` l'affiche « annulé »). Le bloc caducité le présente pourtant comme un PC « autorisé, caduc probable, constructibilité déjà prouvée par l'instruction » et lui applique une surcote ×1,6. Un permis annulé n'est pas une preuve de constructibilité. |
| **S05 Saint-Benoît** | **63 bâtiments** | RNB : 33 bâtiments (23 hors enclaves) ; BD TOPO WFS : 33 (24 hors enclaves). Jamais 63. |
| S07 Le Tampon | 6 bâtiments | BD TOPO WFS : 3 ; RNB : 2 (la fiche elle-même dit `adresses_bati.batiments=3`). |
| S09 Le Port | 6 bâtiments | RNB : 2 (les 2 ids que la fiche liste) ; BD TOPO : 3. |
| S12 Le Tampon | 9 bâtiments | BD TOPO WFS et RNB : 3 (les 3 ids de LABUSE). |
| **S18 Petite-Île** | **propriétaire = « Société (SA/SARL/SAS) », indivision=false** | La dénomination est littéralement « INDIVISAIRES DE LA PARCELLE BE599 » et le SIREN `U23631848` est un pseudo-code DGFiP (préfixe U, 0 résultat recherche-entreprises). Ni société commerciale, ni SIREN réel. |
| **S10 Saint-André** | **propriétaire (siège/APE)** | Entité correcte (Département de La Réunion) mais l'établissement rattaché est faux : Saint-Leu / APE 8622C (médecins) au lieu de Saint-Denis / 84.11Z (administration). |
| S02 Saint-Leu | CASIAS « aucun site » | 2 sites CASIAS ≤ 500 m (Four à chaux Bourbon ~349 m, Sucrerie Dussac ~446 m). Même motif sur S01 et S13 (voir « cosmétique » plus bas). |
| S02 / S10 / S11 | doc d'urbanisme « publié/opposable au GPU » | Le GPU ne sert **aucun** document pour Saint-Leu (97413) et Saint-André (97409) — dépublication constatée. Le PDF imprime la branche « document opposable » ; le JSON se contredit lui-même (`reglement_plu` dit « dépublication » / `plu_fraicheur` dit « présent au GPU »). |

> Détail complet, URL et verbatim : `VERITE.csv` (colonnes parcelle · notion · valeur LABUSE · valeur source · service/URL · page · écart · verdict · pourquoi).

---

## Non vérifiable (29) — dit, jamais silencieux

| famille | n | raison |
|---|---|---|
| Géorisques (endpoint instable / RGA DOM) | 6 | `resultats_rapport_risque` échoue par intermittence ; RGA argiles non publié à La Réunion |
| Sitadel / permis par parcelle | 6 | open data maillé commune×mois, pas de rattachement idu ; millésime 2026-09 sous embargo |
| « autre » (méthodes internes non reproductibles) | 6 | médianes à n interne, voisinage 36 mois glissants hors cache DVF |
| zone PLU / doc urbanisme | 4 | GPU dépublié pour 97413 et 97409 → zone et prescriptions invérifiables via GPU |
| médiane DVF de secteur (méthode) | 4 | agrégation LABUSE non reproductible au point près (fenêtre/déduplication) |
| propriétaire PM (pseudo-SIREN) | 3 | SIREN DGFiP préfixe U (indivision/PM non identifiable), 0 résultat au RNE |

---

## Lot C — la lecture d'un promoteur (6 questions × 20 dossiers)

| question | clair | incomplet | pas clair | absent |
|---|---|---|---|---|
| Q1 — Puis-je construire quoi/combien/à quelle hauteur, qu'est-ce qui l'interdit | 8 | 10 | 2 | 0 |
| Q2 — Puis-je accéder, raccorder, évacuer, avec quelle certitude | 8 | 12 | 0 | 0 |
| Q3 — Qu'est-ce que ça vaut, se vend autour, rapporterait | 2 | 18 | 0 | 0 |
| Q4 — À qui, depuis quand, signal de vente | 11 | 7 | 0 | 2 |
| **Q5 — Coûts cachés (taxes, dépollution, terrassement, archéo, bruit)** | **0** | **20** | 0 | 0 |
| Q6 — Ce qu'il faut aller chercher ailleurs | 13 | 7 | 0 | 0 |

Lecture : la fiche est **honnête sur ses limites** (Q6 « ce qu'il faut vérifier ailleurs » répondu clair 13/20, et les cas inconstructibles — A, N, micro-parcelle — sont tranchés sans ambiguïté). Elle **décroche dès qu'il faut chiffrer un projet** : Q5 (coûts cachés) n'est jamais complète — la taxe d'aménagement est là mais dépollution, terrassement (pente/déblais), archéologie préventive, surcoût acoustique ne sont ni chiffrés ni même listés ; Q3 (rendement) reste à 18/20 incomplet — prix de sortie et comparables présents, mais le **rendement d'une opération** n'est pas posé. Détail par parcelle : `LECTURE.csv`.

### Absences répétées, classées par gravité

**A. Le client se trompe (à corriger en priorité — la fiche induit une décision fausse)**
1. **Règles PLU « non réglementé »** là où le règlement fixe recul/pleine terre/stationnement/hauteur (9 parcelles). Un promoteur dimensionne faux.
2. **Permis annulé présenté comme preuve de constructibilité** avec surcote (S20). Signal d'achat fabriqué.
3. **Propriétaire mal qualifié** : indivision étiquetée « société » (S18), établissement/siège faux (S10). Fausse piste de contact.
4. **PPR : contradiction interne** (S10) — §5 « zone bleue constructible sous prescriptions » vs §10 « Exclusion / capacité 0 m² ». Le promoteur ne sait pas s'il peut construire.
5. **« N ventes à moins de 500 m »** (13 parcelles) : comparabilité de voisinage affichée qui n'existe pas.

**B. Le client perd du temps (information absente ou ailleurs qu'attendu)**
6. **Coûts cachés jamais chiffrés** (Q5, 20/20) : dépollution, terrassement, archéologie, acoustique.
7. **Zone AU fermée non dite comme telle** (S04) : le PDF titre « Fort potentiel — SDP 4 840 m² » sans dire qu'une modification du PLU est requise.
8. **Contenance ≠ aire géométrique** (11 parcelles) : à reporter sur un compromis, l'écart se paie.
9. **Nombre de bâtiments gonflé** (S05 63 vs 33, S12 9 vs 3, S07/S09) : fausse lecture de l'emprise existante.
10. **Régime foncier spécifique noyé** : 50 pas géométriques (S11) et ligne HTA au contact (S12) présents à l'écran mais **absents du PDF** transmis.

**C. Cosmétique (formulation, n'affecte pas la décision)**
11. **CASIAS « aucun site » au rayon 500 m** (S01, S02, S13) : vrai à 0 m (statut structuré `casias='hors'` correct), mais la phrase est trompeuse quand un site est à 350 m.
12. **Page du règlement décalée** de ±2 (S02 stationnement p.10 au lieu de p.12-13).
13. **Adresse BAN** : numéro voisin (S01 : 26 vs 28), même rue, sur la parcelle — sans conséquence.

---

## Lot E — fiche (écran + données servies) vs Dossier PDF

Un tableau par parcelle dans `lot_e_parts/{SLOT}.md` (présent à l'écran/absent du PDF ; présent au PDF/absent de l'écran ; servi dans le JSON mais nulle part). Totaux : **284** lignes vues à l'écran et absentes du Dossier, **280** imprimées au Dossier et invisibles à l'écran. Ce ne sont pas des reformulations : ce sont des blocs métier entiers qui divergent selon le support.

**Systématiquement À L'ÉCRAN mais ABSENT du Dossier PDF que le client transmet :**

| donnée | parcelles concernées |
|---|---|
| Productible solaire (SARAH3, kWh/kWc/an) | 20/20 |
| Gestionnaires réseaux nommés (eau/assainissement/élec, DSP) | 20/20 |
| Lignes électriques HTA/MT au contact ou à proximité | 20/20 |
| Nombre d'arrêtés CatNat de la commune | 18/20 |
| Prescriptions PLU (ER/EBC/OAP) détaillées | 8/20 |
| Servitudes d'utilité publique (SUP) détaillées | 7/20 |
| Établissements SIRENE sur la parcelle | 6/20 |
| Classement sonore / bruit routier | 6/20 |
| Bande des 50 pas géométriques | 5/20 |
| ICPE à proximité | 5/20 |

**Systématiquement AU DOSSIER PDF mais INVISIBLE à l'écran :**

| donnée | parcelles concernées |
|---|---|
| Raccordement / assainissement non collectif (ANC) détaillé | 20/20 |
| % logements non raccordés à l'égout (IRIS INSEE) | 15/20 |
| Ventes « écartées » du calcul de prix | 17/20 |
| Médiane du neuf / VEFA commune | 12-14/20 |
| Mentions légales + n° de rapport propres au PDF | 15/20 |
| Blocs « VÉRIFIÉ : RIEN » (copro, filiation, EBC, ER, PEB, SIS…) | 14/20 |
| Rappel RTAA DOM (aération, protection solaire, ECS) | 12/20 |

Conséquence pour Vic : **le Dossier PDF n'est pas une photographie de la fiche.** Un promoteur qui ne lit que le PDF perd la ligne électrique, le productible solaire, les gestionnaires réseaux et le classement sonore ; un utilisateur qui ne regarde que l'écran ne voit pas l'assainissement non collectif, les ventes écartées ni les mentions RTAA DOM. Les deux supports devraient servir les mêmes blocs.

---

## Lot D — les oracles rejoignent le banc

`scripts/coherence/oracles/` (package `__init__.py` + `__main__.py`), même forme que `scripts/coherence/verite.py`. Rejouable sans navigateur :

```
LABUSE_ORACLE_API=http://127.0.0.1:8645 PYTHONPATH=. python -m scripts.coherence.oracles
  → docs/audit-2026-09/ORACLE-1/ORACLES.csv
```

Cinq oracles à source stable, qui reproduisent les défauts systémiques sur les 20 témoins et que le job nocturne peut reprendre :

| oracle | source publique | ce qu'il tient | résultat sur 20 témoins |
|---|---|---|---|
| `oracle_contenance` | API Carto cadastre (contenance PCI) | surface servie vs contenance, tolérance 1 % | 11 faux / 9 vrai |
| `oracle_dvf_rayon` | DVF Etalab (haversine au centroïde) | libellé « N ventes à 500 m » vs réel ≤ 500 m | 13 faux / 7 vrai |
| `oracle_batiments_rnb` | RNB (bbox parcelle) | nombre de bâtiments servi vs RNB | 3 faux / 15 vrai / 2 n.v. |
| `oracle_georisques` | Géorisques rapport risque au point | présence de risque fiche vs Géorisques | 19 vrai / 1 n.v. |
| `oracle_ban` | BAN reverse | adresse servie vs libellé BAN | 17 vrai / 3 n.v. |

(+ relevés documentaires sismicité/radon par `code_insee`, consignés sans verdict faute de valeur servie comparable dans la fiche.) Total `ORACLES.csv` : 140 lignes · 67 vrai / 27 faux / 46 non vérifiable. Les oracles sismicité/radon/permis Sitadel sont « non vérifiables » dits, comme dans COHERENCE-1.

---

## Annexe — les 20 Dossiers

Tous dans `dossiers/` : `{SLOT}_{IDU}.pdf` (Dossier), `.txt` (texte extrait), `_ecran.txt` (texte affiché, tiroir par tiroir), `{SLOT}_{IDU}.json` (+ `_enrichment.json`, `_zone.json`).

| slot | parcelle | commune | critère du tirage | vrai/faux/n.v. |
|---|---|---|---|---|
| S01 | 97411000AC0196 | Saint-Denis | U dense + bâtie ancienne + copropriété | 20 / 0 / 0 |
| S02 | 97413000CD0532 | Saint-Leu | U pavillonnaire + récente + personne physique | 21 / 3 / 4 |
| S03 | 97415000AB0425 | Saint-Paul | AU ouverte + nue | 22 / 4 / 0 |
| S04 | 97408000AC2877 | La Possession | AU fermée | 21 / 4 / 1 |
| S05 | 97410000CI0215 | Saint-Benoît | zone A + géante (44,9 ha) | 18 / 2 / 1 |
| S06 | 97424000AB0039 | Cilaos | zone N + ravine | 20 / 0 / 0 |
| S07 | 97422000AD0250 | Le Tampon | à cheval sur deux zones (2AUd + A) | 16 / 7 / 1 |
| S08 | 97414000CD0012 | Saint-Louis | à cheval sur deux communes (recouvrement 1 163 m²) | 18 / 1 / 1 |
| S09 | 97407000AO0158 | Le Port | PPR rouge (interdiction) | 22 / 4 / 1 |
| S10 | 97409000AB0018 | Saint-André | PPR bleue (prescription) | 17 / 5 / 2 |
| S11 | 97413000AV0011 | Saint-Leu | littoral 50 pas | 22 / 2 / 3 |
| S12 | 97422000AD0042 | Le Tampon | ligne HTA < 20 m | 19 / 2 / 2 |
| S13 | 97401000AD1303 | Les Avirons | minuscule (1,7 m²) | 27 / 1 / 1 |
| S14 | 97401000AD0238 | Les Avirons | vendue DVF < 2 ans | 24 / 1 / 2 |
| S15 | 97416000CO0579 | Saint-Pierre | SCI + établissement SIRENE | 19 / 4 / 3 |
| S16 | 97402000AD0694 | Bras-Panon | propriétaire EPF | 23 / 2 / 2 |
| S17 | 97410000AB0258 | Saint-Benoît | propriétaire commune | 17 / 3 / 2 |
| S18 | 97405000BE0599 | Petite-Île | indivision probable | 16 / 2 / 1 |
| S19 | 97421000AB0337 | Salazie | permis récent (Sitadel ≥ 2024) | 21 / 2 / 0 |
| S20 | 97420000AB0268 | Sainte-Suzanne | permis caduc / annulé | 25 / 2 / 2 |

**Note sur S08 (à cheval sur deux communes).** Le tirage a confirmé un vrai recouvrement cadastral inter-communes : la géométrie de `97414000CD0012` (Saint-Louis) chevauche `97401000AB0016` (Les Avirons) sur **1 163 m²**. La fiche n'expose pas ce chevauchement ni le risque sur les agrégats communaux ; l'idu portant la commune Saint-Louis, les notions commune sont servies pour Saint-Louis seul.

---

## Reproductibilité

- Tirage : `tirage.sql` (requêtes par critère) → choix gelé dans `PARCELLES.csv`.
- Lot B/C : un sous-agent par parcelle, consignes `CONSIGNES-AGENT.md`, sorties `verite_parts/` + `lecture_parts/`, agrégées par `agreger.py`.
- Lot E : consignes `CONSIGNES-LOT-E.md`, sorties `lot_e_parts/`. Écrans capturés par `ecran_extract.mjs` (Playwright, tiroir par tiroir).
- Lot D : `scripts/coherence/oracles/` rejouable, cache DVF `/tmp/oracle1/dvf/`.
- Quota de consultation de fiches relevé **sur l'instance locale uniquement** (`LABUSE_QUOTA_FICHES_JOUR`), aucune écriture en base.
