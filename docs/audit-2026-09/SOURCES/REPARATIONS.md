# LOT 6 — Synthèse et ordre des réparations

*SOURCES-AUDIT-1. Rien n'est codé ici : chaque ligne du plan deviendra un mandat. Le tableau
complet des verdicts est en tête de `SOURCES-AUDIT.md` ; le détail par source en `fiches/<id>.md`.*

---

## 1. Le tableau des verdicts (sur 116)

| Verdict | Nombre |
|---|---|
| 🟢 PLEINE | 62 |
| 🟡 PARTIELLE — couverture incomplète | 14 |
| 🟡 PARTIELLE — champs manquants | 10 |
| 🟠 SERVIE HORS REGISTRE | 4 |
| ⬜ À DEMANDER / À BRANCHER | 10 |
| 🟣 MANUELLE | 5 |
| ⚫ RETIRÉE (déjà) | 5 |
| 🔗 ALIAS (doublon) | 3 |
| 🏛 HUB (catalogue) | 3 |
| 🔵 BRANCHÉE INVISIBLE | **0** |
| 🔴 À RETIRER | **0** |
| **Total** | **116** |

**Lectures clés** :
- **0 branchée invisible** : après enquête, les 5 candidates « invisibles » de la première
  passe (SIRENE, RTAA, CatNat, Taxe, DVF Région) sont toutes servies — par API, par règles, ou
  hors registre. Aucune source connectée n'est vraiment introuvable pour un pro.
- **0 à retirer** : les 4 retraits « décidés » sont **en attente** (lus en direct, lot 0 S2),
  pas prêts. Les 5 déjà retirées sont propres.
- **24 partielles** (couverture + champs) : c'est le gros du travail honnête à faire.
- **4 servies hors registre** : provenance non tracée (trou de registre, pas de danger client).

## 2. Les principes non respectés (relevés source par source)

Le lot 1 marque, par source, les principes tenus/non tenus (colonnes `principes_ok` /
`principes_ko` du CSV). **Violations relevées** (7 sources) :

| Principe non tenu | Sources | Nombre |
|---|---|---|
| Provenance — **licence à confirmer** | Parc National (7), RPG proxy (10), Potentiel foncier Région (15), Espaces protégés INPN (25) | 4 |
| Provenance — **chiffre servi sans réservoir déclaré** | CatNat (97), Taxe d'aménagement (98) | 2 |
| **Couverture réelle non exposée** (statut binaire) | LiDAR HD (70) | 1 |

**Licences « à confirmer » (au-delà des 4 ci-dessus, incluant hubs/manuelles/retirée)** :
7 (Parc National), 9 (Potentiel foncier urbanisme), 10 (RPG), 11 (Région ODS hub), 12 (PEIGEO),
15 (Potentiel foncier), 25 (INPN), 26 (VRD/SPANC), 68 (Office de l'eau), 80 (ZNIEFF Région,
retirée) — **10 lignes** à trancher juridiquement.

> Réserve d'honnêteté : l'évaluation des 5 principes n'a PAS été menée exhaustivement sur les
> 116×5 (le CRS EPSG:2975 « à vérifier, pas à supposer » demande une inspection base par source
> non faite ici — voir §4). Les violations ci-dessus sont **celles constatées**, pas un audit
> complet des principes. C'est un flou à lever.

## 3. Le plan de réparation, dans l'ordre

D'abord ce qui est **servi faux ou trompeur**, puis l'**incomplet**, puis les **candidates GO**.
Ordre de grandeur : **S** (petit, ½–1 j) · **M** (moyen, quelques jours) · **L** (gros, semaine+).

### A. Servi faux ou trompeur (priorité 1)

| # | Source | Ce qu'il faut faire | Taille |
|---|---|---|---|
| A1 | **OCS GE / Occupation du sol** (22, cand. #2) | L'UI affiche « OCS GE (IGN) » mais sert **BD CARTO V5** : soit dire la vérité (« BD CARTO, proxy grossier »), soit obtenir l'OCS GE natif 974. Corriger l'étiquette d'abord. | S (étiquette) / L (vraie donnée) |
| A2 | **LiDAR HD** (70) | Exposer la **couverture réelle** (statut non binaire) : « connecté — verdict toiture sur N/431 663 ». Ajouter un champ couverture au modèle. | M |
| A3 | **CatNat** (97) | Rattacher `catnat_gaspar` à un chiffre du registre (provenance tracée). | S |
| A4 | **Taxe d'aménagement** (98) | Rattacher `taxe_amenagement`/`taxe_amenagement_taux` aux chiffres taxe (`reservoirs={}` aujourd'hui). | S |
| A5 | **VRD / SPANC** (26) | Dire au client que la donnée est **manuelle** ; trancher la licence. | S |
| A6 | **Familles dédoublées** (S4) | Fusionner `fiscal`/`fiscalite`, `reglement`/`reglementaire`, `terrain`/`topographie`, `assainissement`/`reseaux` (+ migrer `FAMILLE_DE_CATEGORIE` et les vues). | M |
| A7 | **Compteur Circuit** (S1) | Afficher les 116 par statut (dérivé), étendre V2a au total. | S |
| A8 | **Licences « à confirmer »** (10 lignes) | Trancher juridiquement source par source ; retirer ce qui n'est pas réutilisable commercialement. | M |

### B. Doublons à trancher (priorité 2 — S3)

| # | Paire | Action | Taille |
|---|---|---|---|
| B1 | Potentiel foncier Région 9 vs 15 | Retirer **9** (0 chiffre), garder 15, clarifier licence. | S |
| B2 | DVF Région (119) | Décider : témoin de filtre (hors vitrine) ou retrait. | S |
| B3 | SIRENE 21 vs 86 | Documenter le rôle de chaque canal dans leur `i` (ne pas fusionner). | S |

### C. Les 4 retraits en attente (priorité 2 — lot 0 S2)

Chacun : **1) mandat qui coupe le lecteur vivant** (ou abandonne la fonction), avec sa recette ;
**2) puis** passage en `retiree`. Ordre par risque décroissant :

| # | Source | Lecteur à couper d'abord | Taille |
|---|---|---|---|
| C1 | **Office de l'eau** (68) | `anc_service.py` (ANC de 6 communes) — décider si on garde l'ANC 100 % | M |
| C2 | **Parkings APER** (51) | `viabilisation_build` + `ortho_pv`/`ortho_tiles` + Flash | M |
| C3 | **DINUM** (45) | Score V + facettes propriétaire + Scan | L (touche le Score V) |
| C4 | **BD ORTHO IRC** (69) | ombrage végétal du solaire + scoring P | L (touche le scoring) |

*(Si la fonction servie doit vivre, la source ne se retire pas — elle se re-documente.)*

### D. Incomplet — couverture (priorité 3)

Presque tout se **demande** (lot 2 / `DEMANDE-REGION-EPCI.md`), la couverture étant bornée par
le producteur, pas par nous :

| # | Source | Action | Taille |
|---|---|---|---|
| D1 | **SUP AS1** (44) | Demander les périmètres de captage (ARS/DEAL) — plus gros trou réglementaire. | M |
| D2 | **DPU** (107) | Récupérer les 20 DPU communaux manquants. | M |
| D3 | **Assainissement SIG** (63/134) | Demander aux 5 EPCI (20 communes). | M |
| D4 | **PEB Pierrefonds** (108) | Demander à la DGAC/DEAL. | S |
| D5 | Zones humides (112), CBS (117), SIS (115) | Conformes au producteur — surveiller, pas de dette. | — |

### E. Incomplet — champs / fraîcheur (priorité 3)

| # | Source | Action | Taille |
|---|---|---|---|
| E1 | **PLU règlement** (3) | Ingérer le règlement écrit intégral (aujourd'hui : extrait) pour le Copilote. | L |
| E2 | Sudocuh (62), PLH (42), Carte loyers (130) | Fiabiliser la fraîcheur des dépôts manuels. | S |
| E3 | RPG proxy (10) | Pinner l'année, trancher la licence, ou passer au vrai RPG (DAAF). | M |

### F. Les demandes (priorité 3 — lot 2, déjà prêtes)

10 lignes `a_faire` → `DEMANDE-REGION-EPCI.md` (SAR, ZAE, ZAC, OPAH, ORT infra, ENS, OLL micro,
assainissement SIG, ZPPA) + 1 à surveiller (Réunion Express).

### G. Manuelles sous convention (priorité 4)

Fichiers fonciers (27), LOVAC (141), DV3F (142) : **une** demande Cerema via une **collectivité
mandante** couvre les trois. Sinon rien ne bouge (honnêteté préservée : DVF ouvert en attendant).

### H. Candidates GO (priorité 4 — lot 5, chacune son mandat)

| # | Candidate | Mandat | Taille |
|---|---|---|---|
| H1 | **RNB** | Ingérer l'ID bâtiment national ; relier DPE/permis/copro au même bâti. | M |
| H2 | **OCS GE** natif 974 | Obtenir la donnée (WFS en 400 → téléchargement) ; remplacer le proxy BD CARTO ; corriger l'étiquette (voir A1). | L |

*ATTENTION (7)* — TOPAGE, BNPE, SCoT, OAP, SAGE, Géologie, BSS, BDLISA : à rouvrir seulement
sur besoin ferme, avec affichage contextuel honnête. *NON (5)* — BAAC, SISE, mobile,
Conservatoire (licence), CoSIA hors bâti.

---

## 4. Ce qui reste dans le flou (et comment le lever)

1. **Les schémas producteurs (« champs non pris »)** : non consultés (pas de scraping). Pour
   chaque source PLEINE/PARTIELLE, comparer le schéma publié au schéma ingéré demande d'ouvrir
   la doc de chaque producteur — non fait ici (marqué « non vérifié »). *Lever : une passe
   documentaire producteur par producteur.*
2. **Le CRS réel en base (EPSG:2975 ?)** : le principe dit « vérifié, pas supposé ». L'inspection
   `Find_SRID`/`ST_SRID` table par table n'a pas été menée. *Lever : un script qui liste le SRID
   effectif de chaque table géométrique et le compare au CRS attendu.*
3. **La couverture parcellaire chiffrée** de chaque source : mesurée seulement là où une table
   par parcelle existe (végétation, solaire). Pour les couches (intersection parcelle × couche),
   le calcul est coûteux et non fait. *Lever : un batch d'intersection par source, hors mandat
   lecture seule.*
4. **Les comptes « base locale »** : cette base de dev sous-peuple certaines tables (DPE 17,
   toiture_lidar 27) alors que d'autres sont à l'échelle prod. Les comptes du CSV sont donc
   **indicatifs** ; le millésime/couverture du code (`tables.py`) fait foi. *Lever : rejouer le
   script sur la base servie.*
5. **La liste exacte du prompt tiers (15 candidates)** : non retrouvée comme fichier ; les 15
   sont reconstituées depuis le mandat. *Lever : récupérer le prompt d'origine si nécessaire.*
6. **L'évaluation exhaustive des 5 principes sur 116** : partielle (violations constatées, pas
   audit complet). *Lever : croiser le script CRS (2) + la passe documentaire (1).*

---

## Rappel : rien n'est ingéré, rien n'est mergé

Ce mandat **instruit et documente**. Les seules écritures en base envisagées (4 retraits, lot 0)
n'ont **pas** été appliquées — les quatre sources sont lues en direct. Chaque ligne du §3
deviendra un mandat séparé, avec sa recette.
