# LOT 5 — Les 15 candidates : instruites, pas exécutées

*SOURCES-AUDIT-1. Ce mandat **instruit**, il n'intègre rien : chaque GO fera son propre mandat.
Chaque candidate porte, en premier, « déjà présente : oui / non / partiellement » (contrôlée
contre les 116 réelles), la donnée NOUVELLE nommée, le doublon vérifié, la valeur pour un pro
de l'immobilier, la licence textuelle, la granularité honnête, puis le verdict.*

## Trois corrections au prompt tiers (avant tout)

1. **LABUSE ne possède PAS BDNB.** BDNB (id 89) est **retirée** (métropole seule, 0 ligne 974
   sur 22,3 M vérifiées, SCORING-3). Donc le **RNB n'a pas à s'effacer devant BDNB** — il
   pourrait au contraire combler le manque de référentiel bâtiment stable.
2. **LABUSE ne possède PAS SPANC ni les zonages d'assainissement complets.** SPANC (id 26) est
   **manuelle** ; les zonages SIG complets (id 134) sont **à faire** (4/24 via GPU). Les
   candidates eau/assainissement s'évaluent contre cet état **réel**, pas supposé.
3. **On ne code rien ici.** Chaque GO déclenche un mandat d'intégration dédié.

## Les principes du prompt tiers, retenus pour les 116 (pas réservés aux nouvelles)

Provenance complète conservée · filtrage 974 au plus tôt · **CRS LABUSE respecté (EPSG:2975 —
à VÉRIFIER dans la base, pas à supposer)** · tests minimum par source (répond, 974 présent,
géométrie valide, CRS reconnu, volume non nul, identifiants présents, date récupérée) ·
anti-régression (un volume qui tombe à zéro n'écrase jamais la production). Le **lot 1** note,
source par source, lesquels sont déjà tenus (colonnes `principes_ok` / `principes_ko` du CSV).
Le décompte est en `REPARATIONS.md` (lot 6).

---

## Tableau de synthèse

| # | Candidate | Déjà présente ? | Verdict | En une phrase |
|---|---|---|---|---|
| 1 | **RNB** — Référentiel National des Bâtiments | non | **GO** | Identifiant bâtiment stable qui manque depuis le retrait de BDNB. |
| 2 | **OCS GE** — occupation du sol grande échelle | **partiellement (proxy BD CARTO mal étiqueté)** | **GO** | La donnée officielle d'artificialisation ZAN, que le proxy actuel usurpe. |
| 3 | **TOPAGE** — réseau hydrographique | partiellement (BD TOPO water + ravines DPF) | **ATTENTION** | Doublon partiel ; utile pour les cours d'eau BCAE, pas prioritaire. |
| 4 | **BNPE** — prélèvements en eau | non | **ATTENTION** | Approche des captages (AS1 manquante) mais granularité point, pas parcelle. |
| 5 | **SCoT** — schéma de cohérence territoriale | non (Sudocuh suit la procédure, pas le contenu) | **ATTENTION** | Cadre supra-communal utile au récit, faible effet parcellaire. |
| 6 | **OAP** — orientations d'aménagement | partiellement (documents GPU) | **ATTENTION** | Souvent déjà dans le GPU ; vérifier le graphique avant de dédoubler. |
| 7 | **SAGE** — gestion des eaux | non | **ATTENTION** | Vrai manque mais faible valeur foncière directe. |
| 8 | **BAAC** — accidents corporels | non | **NON** | Sans lien foncier ; bruit pour un pro de l'immobilier. |
| 9 | **SISE-Eaux** — qualité eau potable | non | **NON** | Santé publique, pas foncier. |
| 10 | **Couverture mobile** (Arcep) | non (fibre id 126 présente) | **NON** | La fibre à l'immeuble suffit ; le mobile n'ajoute rien au foncier. |
| 11 | **Conservatoire du littoral** | non | **NON** | Licence non spécifiée : sans réutilisation commerciale écrite, c'est NON. |
| 12 | **Géologie** (carte BRGM) | non | **ATTENTION** | Contexte cartographié, JAMAIS une nature de sol parcellaire. |
| 13 | **BSS** — Banque du Sous-Sol (forages) | non | **ATTENTION** | Points de sondage ponctuels ; contexte, pas vérité parcellaire. |
| 14 | **BDLISA** — référentiel hydrogéologique | non | **ATTENTION** | Entités hydrogéo à petite échelle ; contexte de nappe. |
| 15 | **CoSIA — classes hors bâti** | **oui (bâti ingéré)** | **NON (déjà)** | Le bâti CoSIA est déjà pris ; l'artificialisation, c'est OCS GE (#2). |

*Note d'honnêteté : la liste exacte du prompt tiers n'a pas été retrouvée comme fichier dans le
dépôt ; ces 15 sont reconstituées depuis les familles nommées dans le mandat SOURCES-AUDIT-1.
Les faits d'accès ci-dessous marqués « non vérifié » n'ont pas été sondés en direct (pas de
scraping) — ils viennent du code et de la connaissance des jeux publics.*

---

## Fiches d'instruction

### 1. RNB — Référentiel National des Bâtiments — **GO**
- **Déjà présente** : non. (BD TOPO bâtiment et CoSIA bâti existent, mais aucun identifiant
  national stable de bâtiment.)
- **Donnée nouvelle** : l'**identifiant bâtiment unique et pérenne** (RNB ID), qui relie un
  bâtiment à travers BD TOPO, DPE, permis, adresses — le liant que BDNB aurait donné.
- **Doublon vérifié** : contre BD TOPO (17, géométrie bâti) et CoSIA (83, emprise IA). Le RNB
  n'est PAS un doublon : il apporte l'**ID stable**, pas la géométrie. Il NE s'efface PAS
  devant BDNB (retirée, 0 ligne 974).
- **Valeur pour un pro** : rattacher DPE, permis, copropriété et propriétaire au **même**
  bâtiment sans réconciliation géométrique fragile — fiabilise la fiche bien.
- **Licence** : Licence Ouverte / Etalab (RNB, data.gouv) — *non vérifié à la date du jour*.
- **Granularité** : bâtiment (honnête, rattachable à la parcelle via emprise).
- **Verdict — GO** : comble un manque réel (liant bâtiment) laissé béant par le retrait de BDNB.

### 2. OCS GE — occupation du sol grande échelle (artificialisation) — **GO**
- **Déjà présente** : **partiellement, et mal étiquetée**. La couche « Occupation du sol » de
  l'app affiche « Sources : OCS GE (IGN) » mais sert en réalité **BD CARTO® V5** (`kind='ocs_ge'`,
  `attrs.src='BDCARTO_V5'`, 1 643 emprises, 3 classes grossières). L'OCS GE natif 974 **n'est
  pas exposé** au WFS Géoplateforme (400) — non détenu (PROXYS-SOURCES A3).
- **Donnée nouvelle** : **l'usage du sol et l'artificialisation officielle** (référentiel fin
  millésimé, standard ZAN) — ce que CoSIA (couverture) n'a pas et que le proxy BD CARTO ne peut
  pas dire.
- **Doublon vérifié** : contre CoSIA (83, couverture bâti IA) et BD CARTO proxy (22). OCS GE
  ≠ CoSIA (usage/artificialisation juridique vs couverture physique).
- **Valeur pour un pro** : la mesure ZAN officielle (artificialisé/non) — argument de
  constructibilité et de trajectoire foncière.
- **Licence** : Licence Ouverte 2.0 (IGN) — *non vérifié*.
- **Granularité** : polygone d'usage (fin) — honnête.
- **Verdict — GO** : double bénéfice — obtenir la vraie donnée ET **corriger un mensonge
  d'étiquette** actuel (l'UI dit OCS GE, sert BD CARTO). *Bloquant connu : WFS 974 en 400 —
  le mandat d'intégration devra trouver un autre canal (téléchargement Géoplateforme).*

### 3. TOPAGE — réseau hydrographique — **ATTENTION**
- **Déjà présente** : partiellement (BD TOPO `water`/`ravine` (17) + ravines DPF DEAL (111)).
- **Donnée nouvelle** : le référentiel hydrographique **national homogène** (cours d'eau BCAE,
  toponymie, ordre de Strahler).
- **Doublon vérifié** : recouvre largement BD TOPO water + ravines DPF. Apport surtout de
  cohérence/toponymie.
- **Valeur pour un pro** : marges de recul cours d'eau, statut BCAE — utile mais couvert en
  partie par ravines DPF (servitude réelle).
- **Licence** : Licence Ouverte (OFB/IGN) — *non vérifié*.
- **Granularité** : tronçon hydrographique — honnête.
- **Verdict — ATTENTION** : doublon partiel ; à considérer seulement si les reculs cours d'eau
  deviennent un besoin ferme.

### 4. BNPE — prélèvements en eau — **ATTENTION**
- **Déjà présente** : non.
- **Donnée nouvelle** : les **points de prélèvement** (captages AEP, forages) et volumes.
- **Doublon vérifié** : contre SUP AS1 (périmètres de protection de captage) — qui est
  justement **absente** (id 44, AS1 non publiée au GPU). BNPE donne le **point**, pas le
  **périmètre de protection** réglementaire.
- **Valeur pour un pro** : indice de proximité d'un captage ; mais sans le périmètre AS1, ne
  donne pas la servitude opposable.
- **Licence** : Licence Ouverte (Sandre/OFB) — *non vérifié*.
- **Granularité** : **point** — à NE PAS présenter comme une contrainte parcellaire (le point
  n'est pas le périmètre).
- **Verdict — ATTENTION** : intéressant comme signal, mais la vraie cible reste AS1 (à demander,
  lot 2/7). Ne pas confondre point de prélèvement et périmètre de protection.

### 5. SCoT — schéma de cohérence territoriale — **ATTENTION**
- **Déjà présente** : non (Sudocuh id 62 suit les **procédures**, pas le contenu du SCoT).
- **Donnée nouvelle** : les **orientations supra-communales** (armature urbaine, zones
  préférentielles) — le maillon entre SAR et PLU.
- **Doublon vérifié** : contre Sudocuh (procédures) et le module destinations. Pas un vrai
  doublon de contenu, mais faible granularité.
- **Valeur pour un pro** : contexte de récit ; effet parcellaire indirect.
- **Licence** : documents publics — *non vérifié*.
- **Granularité** : périmètre EPCI / orientation — contexte, pas parcelle.
- **Verdict — ATTENTION** : valeur narrative, priorité basse.

### 6. OAP — orientations d'aménagement et de programmation — **ATTENTION**
- **Déjà présente** : **partiellement** — les OAP font partie des **pièces du PLU** ; le GPU
  (id 3) en porte une partie (documents/prescriptions). À vérifier si le **graphique** OAP est
  ingéré ou seulement le règlement.
- **Donnée nouvelle** : les **secteurs d'OAP** (opposables en compatibilité) en géométrie.
- **Doublon vérifié** : contre GPU (3) — risque fort de redondance ; instruire d'abord ce qui
  est déjà dans le GPU.
- **Valeur pour un pro** : sur un terrain en OAP, les règles de composition changent le projet.
- **Licence** : Licence Ouverte (GPU) — *non vérifié*.
- **Granularité** : secteur d'OAP (polygone) — honnête.
- **Verdict — ATTENTION** : GO conditionnel — seulement pour la part **non** déjà servie par
  le GPU. Auditer le GPU avant.

### 7. SAGE — schéma d'aménagement et de gestion des eaux — **ATTENTION**
- **Déjà présente** : non.
- **Donnée nouvelle** : les **périmètres SAGE** et règles de gestion de l'eau.
- **Doublon vérifié** : contre rien (aucune source eau-planification en base).
- **Valeur pour un pro** : faible en direct (foncier) ; contexte réglementaire de l'eau.
- **Licence** : Licence Ouverte (Sandre/Gest'eau) — *non vérifié*.
- **Granularité** : périmètre de SAGE — contexte.
- **Verdict — ATTENTION** : vrai manque thématique, faible valeur foncière — priorité basse.

### 8. BAAC — accidents corporels de la circulation — **NON**
- **Déjà présente** : non. **Donnée nouvelle** : localisation d'accidents.
- **Valeur pour un pro** : quasi nulle pour le foncier/l'immobilier ; bruit.
- **Granularité** : point d'accident. **Licence** : Licence Ouverte — *non vérifié*.
- **Verdict — NON** : hors sujet foncier (confirmé par le mandat : candidate a priori faible).

### 9. SISE-Eaux — qualité de l'eau potable — **NON**
- **Déjà présente** : non. **Donnée nouvelle** : résultats de contrôle sanitaire de l'eau.
- **Valeur pour un pro** : santé publique, pas foncier.
- **Granularité** : unité de distribution / point de prélèvement. **Licence** : Licence Ouverte.
- **Verdict — NON** : hors sujet foncier.

### 10. Couverture mobile (Arcep) — **NON**
- **Déjà présente** : non (mais la **fibre à l'immeuble** id 126 l'est déjà).
- **Donnée nouvelle** : niveaux de couverture 4G/5G par opérateur.
- **Valeur pour un pro** : la fibre couvre déjà le besoin « connectivité » ; le mobile n'ajoute
  rien de décisif au foncier.
- **Granularité** : maille/dalle. **Licence** : Licence Ouverte (Arcep).
- **Verdict — NON** : redondant avec l'axe connectivité déjà servi.

### 11. Conservatoire du littoral — **NON**
- **Déjà présente** : non.
- **Donnée nouvelle** : parcelles/terrains du Conservatoire du littoral.
- **Doublon vérifié** : contre 50 pas géométriques (47), espaces protégés INPN (25) — recouvre
  en partie le littoral protégé.
- **Licence** : **« licence non spécifiée »** (signalé par le mandat). **Sans réutilisation
  commerciale écrite, c'est NON.**
- **Granularité** : parcelle/périmètre. **Verdict — NON** : verrou licence. À rouvrir seulement
  si une licence de réutilisation commerciale est obtenue par écrit.

### 12. Géologie (carte géologique BRGM) — **ATTENTION**
- **Déjà présente** : non.
- **Donnée nouvelle** : formations géologiques (contexte de sol).
- **Granularité HONNÊTE** : **carte à petite échelle (1/50 000)** — un **contexte**, JAMAIS une
  nature de sol parcellaire. La fiche devrait dire « formation géologique du secteur », pas
  « le sol de cette parcelle est… ».
- **Valeur pour un pro** : contexte de fondation/retrait-gonflement — indicatif.
- **Licence** : Licence Ouverte (BRGM) — *non vérifié*.
- **Verdict — ATTENTION** : n'intégrer qu'avec un affichage explicitement contextuel.

### 13. BSS — Banque du Sous-Sol (forages/sondages) — **ATTENTION**
- **Déjà présente** : non.
- **Donnée nouvelle** : **points** de forages et sondages (logs géotechniques).
- **Granularité HONNÊTE** : **point** ponctuel — présence d'un sondage à proximité, jamais une
  vérité de sol pour toute la parcelle.
- **Valeur pour un pro** : indice géotechnique proche ; utile en pré-étude.
- **Licence** : Licence Ouverte (BRGM). **Verdict — ATTENTION** : contexte ponctuel seulement.

### 14. BDLISA — référentiel hydrogéologique — **ATTENTION**
- **Déjà présente** : non.
- **Donnée nouvelle** : entités hydrogéologiques (nappes).
- **Granularité HONNÊTE** : **petite échelle** — contexte de nappe, pas une donnée parcellaire.
- **Valeur pour un pro** : faible en direct ; contexte eau souterraine.
- **Licence** : Licence Ouverte (BRGM/Sandre). **Verdict — ATTENTION** : contexte seulement.

### 15. CoSIA — classes hors bâti — **NON (déjà là pour l'essentiel)**
- **Déjà présente** : **oui** — le bâti CoSIA (id 83) est ingéré (445 190 objets).
- **Donnée nouvelle** : les autres classes CoSIA (végétation, eau, route) — marginales pour le
  foncier ; **l'artificialisation officielle, c'est OCS GE (#2), pas CoSIA.**
- **Verdict — NON** : ne pas re-brancher CoSIA sous un autre nom ; la vraie donnée manquante
  (artificialisation) est en #2.

---

## Bilan des verdicts candidates

- **GO (2)** : RNB, OCS GE. *(RNB comble le trou BDNB ; OCS GE apporte l'artificialisation ET
  corrige une étiquette mensongère.)*
- **ATTENTION (7)** : TOPAGE, BNPE, SCoT, OAP, SAGE, Géologie, BSS, BDLISA → soit doublon
  partiel, soit granularité contextuelle à afficher honnêtement, soit faible valeur foncière.
  *(8 items — ATTENTION regroupe les « oui mais ».)*
- **NON (5)** : BAAC, SISE-Eaux, couverture mobile, Conservatoire du littoral (licence),
  CoSIA hors bâti (déjà là).

**Chaque GO ouvrira son propre mandat d'intégration** (ordre proposé dans `REPARATIONS.md`).
