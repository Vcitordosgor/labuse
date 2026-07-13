# M6 §1.3a — Matrice usage × zone × commune (PLU) et distinction des usages par le moteur

Audit LECTURE SEULE — 13/07/2026 — branche `audit/grand-check` — run v2 servi : `m36-l2f-2026-2026-07-12`.
Livrables : ce document + `1-3a-matrice-plu.csv` (836 lignes = toutes les zones PLU en base, 24 communes).

## 0. Méthode et sources

- **Inventaire zones** : `spatial_layers` `kind='plu_gpu_zone'` — 836 couples (commune, libellé) distincts
  (`scripts/zones_inventory_full.txt`, extrait SQL lecture seule).
- **Moteur audité (2 étages)** :
  1. **Cascade** `src/labuse/cascade/layers/phase1.py` › `ZonagePluGpuLayer` + `config/cascade_rules.yaml`
     (layer `zonage_plu_gpu`, l. 64-79) : classement par **préfixe de `typezone` GPU** (`subtype` en base :
     U / AU / AUc / AUs vs A / N). U/AU → bonus `zonage_u_au` (constructible) ; A/N → HARD_EXCLUDE si
     recouvrement ≥ 90 %.
  2. **Faisabilité** `src/labuse/faisabilite/plu_rules.py` › `resolve_zone(code, commune)` + YAML calibrés
     (`config/plu_saint_paul.yaml` mode **strict**, `config/plu_saint_denis.yaml` mode **progressif** —
     **2 communes sur 24** ; les 22 autres = estimation générique).
- **Règlements écrits** téléchargés et lus (`reglements/*.txt`, conversion pdftotext, pages citées = pages PDF) :

| INSEE | Commune | Document | Vérifié |
|---|---|---|---|
| 97407 | Le Port | règlement 2024-12-09 + jugement TA/CAA | oui |
| 97411 | Saint-Denis | règlement (MS8 fév. 2024, éd. 2026-04-23) | oui |
| 97415 | Saint-Paul | règlement 2012 éd. mars 2026 | oui |
| 97416 | **Saint-Pierre** | Eco-PLU approuvé juin 2024 | **oui (complété par cet audit)** |
| 97418 | Sainte-Marie | règlement 2025-11-26 | oui |
| 97420 | **Sainte-Suzanne** | règlement approuvé 2025-09-29 | **oui (complété par cet audit)** |

**6 communes vérifiées sur 24** (62 lignes de la matrice avec `verif = règlement lu`, dict sourcé
`scripts/verifs_reglement.py`). Les 18 autres communes : colonne `verif = non vérifié` (honnête) ; la
vocation affichée est alors le `libelong` GPU, qui n'est PAS le règlement.

## 1. Réponse à la question centrale : le moteur distingue-t-il les USAGES ?

**Non, à aucun étage.** Il n'existe **aucune notion de destination** (habitat / activité / équipement)
dans le code ni dans les configs :

- La **cascade** classe uniquement sur le préfixe de `typezone` : toute zone U ou AU reçoit le même bonus
  « constructible » (`positive_prefixes: [U, AU]`), qu'elle soit résidentielle (Ua) ou industrielle (Uazi).
  Le règlement écrit n'est jamais lu.
- La **faisabilité** (`resolve_zone`) ne porte que des règles de FORME (hauteurs, reculs, emprise,
  stationnement). Aucun champ « destinations autorisées ». Vérifié empiriquement (lecture seule) :
  - `resolve_zone("U1e","Saint-Paul")` → `constructible_neuf=True, calibree=True, hf=14 m` alors que le
    règlement de Saint-Paul **interdit l'habitat en U1e** (Art. 1.2 p.37-38). Le YAML « gold » lui-même
    calibre les zones éco (U1e, U1ec, U2e, U3e, AU5e) comme si on pouvait y produire du logement.
  - `resolve_zone("Uazi","Saint-Pierre")` → `constructible_neuf=True (générique, hé 9 m)` alors que le
    tableau Art. Ua1 (p.172-175) marque « Logement » **interdit**.
  - Le seul cas d'inconstructibilité « neuf » modélisé est `constructible_neuf=False` pour les zones
    `AU*st` de Saint-Paul — un régime d'ouverture, pas un usage.

C'est exactement le mécanisme qui a produit le cas « logement étudiant proposé en zone industrielle » :
toute zone U est constructible-logement pour le moteur.

### Chiffrage des fausses opportunités (centroïde parcelle dans la zone ; run `m36-l2f-2026-2026-07-12`)

| Périmètre | Parcelles | ev `opportunite` | ev `a_creuser` | v2 brûlantes | v2 chaudes | v2 à creuser | v2 réserve |
|---|---:|---:|---:|---:|---:|---:|---:|
| Zones à vocation éco/activités (91 couples commune×zone, vérifiés + candidats par libellé, hors Ui résidentiel de Saint-Denis) | **6 638** | **500** | 2 135 | **1** | **91** | 2 093 | 377 |
| dont zones où l'habitat est **INTERDIT au règlement vérifié** (26 couples) | **2 457** | **119** | 1 000 | 0 | **25** | 860 | 161 |
| dont zones où l'habitat est **conditionnel** au règlement vérifié (gardiennage/fonction uniquement, 14 couples) | **3 107** | **165** | 1 149 | 0 | **11** | 1 152 | 146 |
| Zones **AU STRICTES** (typezone `AUs` + AUx Saint-Denis — ouverture subordonnée à modif/révision du PLU) | **1 439** | **106** | 779 | **1** | **10** | 729 | 69 |

Cas saillants (détail par zone dans `sql/m6_eco_chiffrage_result.txt`, requêtes dans `sql/m6_eco_chiffrage.sql` / `sql/m6_chiffrage2.sql`) :

- **Brûlante rang 17** : `97422000AD1237` (Le Tampon) en **2AUd** — zone AU stricte fermée : rien n'y est
  autorisable sans modification du PLU. Fausse opportunité en tête du run servi.
- **Brûlante rang 194** : `97413000CD0729` (Saint-Leu) en **AUE** (à urbaniser économique — non vérifié,
  règlement Saint-Leu non téléchargé) + 8 chaudes AUE Saint-Leu.
- **Chaude rang 48** : `97415000AB0847` (Saint-Paul) en **AU1ec** — renvoi U1e/U1ec : habitat **interdit**
  (règlement vérifié p.37-38, 55). 9 chaudes AU1ec au total.
- **25 chaudes du Tampon en 1AUe/2AUe** (économiques, non vérifiées) ; 13 chaudes Saint-Pierre en
  Uazi/Uazc/Uaza/Uazp (habitat interdit vérifié).
- Le Port **Ue** : 440 parcelles, 46 en `opportunite` — le règlement (Art. Ue 2 p.80) n'admet qu'UN
  logement de fonction par unité foncière.

## 2. La matrice (CSV)

`1-3a-matrice-plu.csv` — 836 lignes, colonnes : commune, zone (libellé), typezone, n_polygones,
surface_ha, vocation_reglement, habitat_autorise, verdict_moteur (cascade), usages_moteur,
faisabilite_moteur (`resolve_zone` exécuté, lecture seule), ecart, anomalie_rattachement, source (page),
**verif** (`règlement lu (…pdf)` / `non vérifié`).

Bilan des écarts :

| Catégorie | Lignes |
|---|---:|
| **ECART MAJEUR — habitat INTERDIT au règlement, moteur = constructible logement** | **26** |
| **ECART MAJEUR — habitat conditionnel (gardiennage/fonction), moteur = constructible sans condition** | **14** |
| ECART PROBABLE — libellé économique, non vérifié au règlement | 49 |
| ECART — AU stricte (typezone `AUs`) traitée constructible par la cascade | 43 |
| ECART autre (OAP en renvoi, secteur annulé par le juge) | 2 |
| ANOMALIE DONNÉE — polygone d'un document voisin rattaché à la mauvaise commune | 8 (81 lignes concernées au total, col. `anomalie_rattachement`) |
| conforme (vérifié, usage habitat admis ou exclusion correcte) | 12 |
| sans écart détecté / hors périmètre éco (majoritairement zones résidentielles, A et N) | 682 |

Les 26 « habitat INTERDIT » : Saint-Pierre Uazp, Uazpc, Uaza, Uazc, Uazi, AUazc, AUazi, Uep, AU01/02/03,
AU0c-1 ; Saint-Paul U1e, U1ec*, U2e, U3e, AU1e, AU1ec, AU1est, AU3e, AU5e ; Sainte-Marie UEp, 1AUep ;
Sainte-Suzanne UE ; Saint-Denis AUx ; Le Port 2AUem, Uppp. (*U1ec compté avec U1e : même Art. 1.2.)

## 3. Politique des zones inconnues du calibrage — défaut appliqué, et danger

Trois régimes distincts, du plus sûr au plus dangereux :

1. **Cascade (typezone)** : la base ne contient que des typezones normalisés (U 283, N 217, AUc 186,
   A 74, **AUs 58**, AU 18) — pas de préfixe inconnu aujourd'hui. Un préfixe inconnu donnerait un PASS
   neutre (ni bonus ni exclusion). Danger réel : **`AUs` (AU stricte) commence par « AU » → même bonus
   constructible qu'une zone ouverte** (1 439 parcelles, cf. §1).
2. **Commune calibrée `mode: strict`** (Saint-Paul uniquement) : code hors YAML → `None` (non
   constructible). Sûr par construction… mais le YAML lui-même calibre les zones éco en logement (cf. §1).
3. **Commune calibrée `mode: progressif`** (Saint-Denis) et **22 communes sans YAML** :
   `_zone_generique()` — on retire les chiffres de tête du code (« 1AUe » → « AUE ») et **tout préfixe
   U/AU devient constructible logement avec hé générique 9 m** (`he_defaut_generique_m`). C'est le défaut
   appliqué à la quasi-totalité de l'île. Dangereux car :
   - toutes les zones éco (UE, Ue, UZ, US, Uaz*, AUe…) y deviennent des gisements logement ;
   - les AU fermées non conformes au motif `AU\w*st` passent au travers : vérifié empiriquement,
     `resolve_zone("2AU","Saint-Pierre")` → constructible générique ; idem `AU01`, `1AUste`, `2AUe` ;
   - à Saint-Denis (progressif), **AUx** — zone où « toutes constructions sont interdites » (Art. AUx.1/2
     p.110) — est calibrée `a_verifier` sans hauteur exploitable → retombe sur l'**estimation générique
     constructible hé 9 m** (vérifié empiriquement). 92 parcelles, 1 chaude.

## 4. Règles manquées (sourcées)

| # | Commune / zone | Page règlement | Ce que fait le moteur | Ce qu'il devrait faire | Impact chiffré (parcelles) |
|---|---|---|---|---|---|
| R1 | Saint-Pierre Uazi, Uazc, Uaza, Uazp, Uazpc, AUazi, AUazc | 97416, Art. Ua1 p.172-175 (tableau : Logement = interdit), caractère p.171 | Bonus U/AU + faisabilité logement générique hé 9 m | Habitat = interdit ; scorer uniquement pour usage activité | 1 316 (Uazi 560, Uazp 369, Uaza 227, Uazc 127…) dont 57 ev `opportunite`, 11 chaudes v2 |
| R2 | Saint-Paul U1e/U1ec, U2e, U3e, AU1e/AU1ec/AU1est, AU3e, AU5e | 97415, Art. 1.2 p.37-38, p.88, p.145, p.254 ; AU p.55-59, 160-161 | Faisabilité **calibrée** hf 14-18 m, constructible logement | Habitat interdit (seules extensions de l'existant) | 621 dont 7 ev `opportunite`, 10 chaudes (AU1ec rang 48) |
| R3 | Sainte-Marie UEp + 1AUep (renvoi UEp) | 97418, Art. U2 pt 4 et 8 p.30 (l'exception gardiennage **exclut** UEp) ; chap. V p.41-42 | Constructible logement générique | Habitat strictement interdit, y compris gardiennage | 144 dont 33 ev `opportunite`, 3 chaudes |
| R4 | Sainte-Suzanne UE | 97420, Art. UE1.2 + tableau p.20-21 | Constructible logement générique | Habitat interdit | 95 dont 6 ev `opportunite` |
| R5 | Le Port Ue, Uem, Us, Up, Umi (+ Saint-Pierre Uemi, Sainte-Marie UEa/UEc/UEm) | 97407, Art. Ue 2 p.80, Us 2 p.120, Up 2 p.109 ; 97416 Art. Ue1 p.188-189 ; 97418 Art. U2 pt 4 p.30 | Constructible logement sans condition | Habitat **conditionnel** : 1 logement de fonction/gardiennage max, hébergement interdit | 3 107 dont 165 ev `opportunite`, 11 chaudes |
| R6 | Zones AU strictes toutes communes (typezone `AUs` : 2AU*, AUst, AU0*, AUx…) | ex. 97411 Art. AUx.1/2 p.110 ; 97407 Art. 2AU 1-2 p.157-158 ; 97416 Art. AU0 1 p.200 ; 97415 p.59 | Bonus « constructible » identique aux zones ouvertes ; faisabilité générique constructible | Geler : inconstructible tant que le PLU n'est pas modifié (au mieux « réserve foncière ») | 1 439 dont 106 ev `opportunite`, **1 brûlante rang 17** (Le Tampon 2AUd), 10 chaudes |
| R7 | Le Port Uppp (plaisance et pêche) | Jugement TA Réunion n°1900330 du 28/02/2022, définitif (CAA Bordeaux 22BX01470) — secteur **annulé** ; texte toujours au GPU | Constructible (typezone U) | Appliquer le régime Up de droit commun ; signaler l'annulation contentieuse | 1 polygone, 30 ha |
| R8 | Rattachement commune des polygones GPU | — (anomalie donnée, pas règlement) | 81 lignes de zones contiennent des polygones d'un document voisin (ex. Saint-Denis « UEa/UEc/UEp » = PLU de Sainte-Marie ; Saint-Paul « UE/UEm/AUEm » = La Possession ; « Ue/AUse » = Trois-Bassins) | Rattacher la zone à la commune de l'`idurba`, pas à la commune d'emprise | fausse la matrice ET tout croisement commune×zone (col. `anomalie_rattachement` du CSV) |
| R9 | Saint-Denis Uip (secteur PRUNEL) | 97411, Art. Ui.1 p.52 | Constructible logement standard | Logements neufs interdits en 1er front de certains axes ; conditions de mixité | 100 parcelles, 1 chaude |

Nota conforme : Saint-Denis **Ui** n'est PAS une zone industrielle — c'est la zone résidentielle
intermédiaire (« l'habitation domine », industrie interdite, Art. Ui.1 p.51-52). Ses 6 099 parcelles ne
sont donc pas des fausses opportunités d'usage ; elles ont été retirées du périmètre éco du chiffrage.

## 5. Reproductibilité

- Dict des vérifications sourcées : `reports/m6-audit/scripts/verifs_reglement.py` (62 entrées, 6 communes).
- Générateur : `reports/m6-audit/scripts/build_matrix.py` (entrées : `zones_inventory_full.txt`,
  `eco_list2.txt`, `verifs_reglement.py` ; appelle `resolve_zone` en lecture seule).
- Chiffrages SQL (SELECT uniquement) : `reports/m6-audit/sql/m6_eco_chiffrage.sql` (+ `_result.txt`),
  `reports/m6-audit/sql/m6_chiffrage2.sql`.

## 6. Recommandations (pour M6 Phase 2 — hors périmètre de cet audit lecture seule)

1. Ajouter une dimension **destination** au calibrage (`habitat: oui|non|conditionnel` par zone dans les
   YAML PLU et/ou une liste `usage_eco_prefixes` dans `cascade_rules.yaml`) et l'appliquer au scoring
   logement ; les 62 entrées vérifiées de `verifs_reglement.py` sont directement réutilisables.
2. Traiter `typezone AUs` (+ motifs AU0/2AU/AUst élargis) comme **gel** : réserve foncière, jamais
   brûlante/chaude.
3. Corriger le rattachement commune des polygones GPU (par `idurba`) — préalable à tout calibrage.
4. Étendre la vérification règlementaire aux 18 communes restantes (priorité : Saint-Leu — brûlante AUE
   rang 194 —, Le Tampon — 25 chaudes 1AUe/2AUe —, La Possession, Saint-Louis).
