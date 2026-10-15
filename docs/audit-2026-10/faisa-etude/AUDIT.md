# FAISA-ETUDE-AUDIT-1 — audit de faisabilité du 9ᵉ document « Étude de faisabilité »

> **Mandat** : lecture seule. Branche `audit/faisa-etude-audit-1`, worktree `~/Desktop/labuse-faisaetude`.
> Aucun code modifié, aucun run, aucun merge. Seul écrit : ce fichier.
> **Étape 0** — `pwd` = worktree, branche = `audit/faisa-etude-audit-1`, arbre propre. ✅
> **Méthode** — lecture directe du moteur Faisabilité / Gabarit / exports + des YAML `config/plu_destinations`
> (23 communes) ; 3 explorations ciblées (couverture PLU d/e/f/g · valeurs témoins · catalogue Docs & PDF).
> Aucune base interrogée (pas de run) : les comparaisons Q3 portent sur les **règles de zone servies**,
> pas sur des m² calculés par parcelle.

---

## Q1 — STATUT RÉEL (par règle)

| | Règle | Statut | Preuve |
|---|---|---|---|
| **a** | Hauteur par prospect L ≥ H (St-Denis Ud) | **SERVI** (calculé par parcelle) | `faisabilite/db.py:444-449` (`hauteur_mode=='prospect'` → L = max(largeur voie BD TOPO, plancher 10 m)) ; `zonage.py:57` ; rendu `scenarios.py:70-74` |
| **b** | ER / EBC / SUP déduits de la zone d'implantation (lot D) | **FAIT** (les 3) | ER+EBC : `faisabilite/db.py:117-144` (requête `_EMPRISE`, union retranchée de l'emprise insetée ∩ portion U/AU) + ligne `engine.py:538-553`. SUP : `gabarit/builder.py:371-393` (**RETOUCHES-1 lot D.15**, `kind='sup'`, exclut `pm1` par ORACLE-FIX-1) — l'assiette gabarit est relue par le résiduel |
| **c** | Pleine terre / perméabilité / espaces verts % → m² | **PARTIEL** : pleine terre servie ; perméabilité & espaces verts non distincts | `engine.py:606-621` : `pleine_terre_pct` → `emprise ≤ surface×(1−pt%)`, « ~X m² retenu ». Espaces verts seulement comme **composante** du calcul pleine terre (`zonage.py:65`, `pleine_terre_compose`). Pas de champ perméabilité ni arbres/50 m² |
| **d** | Stationnement par typologie (logement / visiteurs / PMR / commerce) | **ABSENT** (typologie) — seul un **ratio unique** places/logement | `zonage.py:50,80-93` (`stat_logement`, `places_par_logement` ne lit que « X place/logement ») ; `engine.py:731-763` : les « 2 scénarios » = **au sol / sous-sol-silo** (implantation du parking), **pas** une typologie. Aucun visiteur / PMR / commerce |
| **e** | Mixité sociale (seuil SDP/logts → quota) | **SERVI là où la règle est validée** (1 seule commune calibrée : St-Denis) | `engine.py:813-841` (11ᵉ étape : `quota_pct × programme` → nb LLS, sourcé) ; `zonage.py:70` ; `scenarios.py:76-93`. Statut `valide` requis ; `propose`/absente → « non modélisée » |
| **f** | Distance entre constructions (même parcelle) | **ABSENT** | Aucun champ dans `ZoneRules`, aucun calcul (grep « entre construction/bâtiment » = 0 dans `faisabilite/`) |
| **g** | Local vélos / local OM | **ABSENT** | Aucun champ / calcul (grep vélo / ordures = 0 dans `faisabilite/`) |
| **h** | Pente / terrain naturel (MNT LiDAR) | **EN BASE + exploitable par parcelle** ; non branché dans la SDP (informatif) | Raster `rgealti_mnt_5m` (SRID 2975) en base ; coupe LIVE le long d'une ligne `faisabilite/profil_altimetrique.py` (dénivelé, pente moyenne, plus forte pente) ; pente parcellaire servie fiche via `ingestion…ingest_pente` + `fiche_ask.py:219` (vigilances) |
| **i** | Répartition typologique | **UNE SEULE taille moyenne** aujourd'hui | `engine.py:698` : `logt_moyen = (bas+haut)/2` (65–80 m²) ; vendable = habitable ÷ taille **moyenne**. Pas de mix T1/T2/T3 |

**Lecture d'ensemble** : le moteur sert déjà, par parcelle, hauteur (absolue, R+n **et prospect**), reculs
(voie/limites + formule), emprise/CES, pleine terre, SDP résiduelle et capacité en logements, avec ER/EBC/SUP
déduits. Les manques « archi » sont : **stationnement par typologie, espaces verts/perméabilité distincts,
distance entre constructions, vélos/OM, répartition typologique** ; la **mixité** est câblée mais calibrée
sur **une** commune.

---

## Q2 — CALIBRAGE PLU (règles d / e / f / g sur 23 communes)

| Règle | Structuré/chiffré (A) | Citation seule (B) | Absent (C) | Trouvable |
|---|---|---|---|---|
| **d** Stationnement typologie | 23 (mais ratio simple, **0 différencié**) | 0 | 0 | 23/23 — mais aucune ne distingue type/visiteurs/PMR/commerce |
| **e** Mixité sociale | 1 (St-Denis `97411:29-38`) | 16 (texte) | 6 | **17/23** |
| **f** Distance entre constructions | 0 | 3 (`97410:1430`, `97412:57-58`, `97422`) | 20 | 3/23 |
| **g** Vélos + OM | 0 | 0 (OM seul : 8 communes, en **interdiction de dépôt**, pas un local) | 23 | 0/23 |

**Effort d'un PLU-CALIBRAGE-5 (par règle) :**

- **e — mixité : MOYEN, meilleur rapport gain/effort.** Le moteur *consomme déjà* `rules.mixite`
  (St-Denis le prouve) — le travail est de la **transcription + validation** de 16 citations en feuille
  `mixite` (`seuil` → `quota_pct`, article/page), pas du code.
- **d — stationnement typologie : FORT.** Les tableaux par type existent souvent au PDF mais sont marqués
  « non extractibles en texte » (ex. L'Étang-Salé art. 2.7.3, `plu_zonage.yaml`). Il faut un **nouveau
  modèle de données** (par T1/T2…, visiteurs, PMR, commerce) + ré-extraction ciblée + un nouveau calcul
  de besoin de places.
- **f — distance entre constructions : calibrage FAIBLE (3 communes), moteur MOYEN/FORT.** Nouveau champ
  + calcul géométrique entre bâtis projetés. Peu de gisement.
- **g — vélos / OM : FORT pour un gain marginal.** Quasi absent des règlements ingérés (re-extraction PDF
  dédiée), et impact programmatique, pas sur la SDP.

**Priorisation PLU-CALIBRAGE-5 : mixité d'abord** (moteur prêt, 16 communes à transcrire), le reste ensuite.

---

## Q3 — TÉMOINS (LABUSE vs chiffres archis)

> Rappel : PPR et EBC ne sont **pas** des règles de zone chez LABUSE mais des **couches géométriques**
> déduites de l'assiette (ER/EBC `db.py:117-144`, SUP `gabarit/builder.py`, PPR rouge). Leur « présence »
> sur une parcelle dépend de la donnée spatiale, non du YAML de zone.

### Saint-Leu AC 261 / 264 — zone **Ud** (`config/plu_destinations/97413_saint_leu.yaml`)
| Règle archi | LABUSE | Verdict |
|---|---|---|
| 2 places / logement | **2 pl/logement** (`:746`, UD 12 renvoi art. 11) | **MÊME** |
| 12–13 visiteurs | stationnement visiteurs **absent** | **ABSENTE** |
| EBC sur AC 261 | pas de regle de zone ; **déduit géométriquement** si la couche EBC couvre la parcelle | déduit si donnée présente (non vérifié sans requête parcelle) |
| (contexte) hauteur 4/6 m, CES 40 %, reculs 3/3 m, pleine terre 40 % | servis (`:709/716/723/731/738/755`) | — |

### L'Étang-Salé AW 99/451/624/625 — zone **UA** (`97404_l_etang_sale.yaml`)
**Millésime servi = `2025-09-17` (meta l.9) → POSTÉRIEUR au 04/12/2024. ✅**
| Règle archi | LABUSE | Verdict |
|---|---|---|
| Recul voie 4 m | **4 m** (`:41`) | **MÊME** |
| Séparatives : limite si linéaire ≤ 15 m, sinon 3 m | **3 m** plancher (`:48`) ; condition « ≤ 15 m » **absente** | **DIFFÉRENTE** (plancher ok, règle conditionnelle non modélisée) |
| CES 70 % | **70 %** (`:33`) | **MÊME** |
| Hauteur 12 égout / 15 faîtage / 13 acrotère | **12 / 15 / 13** (`:25 / :18 / :22`) | **MÊME** (les trois) |
| Perméabilité 30 % | **pleine terre 30 %** (`:65`) | **MÊME** (servie comme pleine terre) |
| Espaces verts 20 % + 1 arbre/50 m² | absent | **ABSENTE** |
| Stationnement 1 ≤T2 · 1,5 ≤T4 · 2 T5 · commerce 1/100 m² | citation présente, **statut `propose`** (`places:null`, « a_verifier », tableau 2.7.3 non extrait) | **PRÉSENTE EN TEXTE, NON SERVIE** |
| Vélos 1 m² ≤T2 · 1,5 au-delà | absent | **ABSENTE** |
| Mixité > 1 000 m² SDP → 20 % aidé | **citation identique** (`:130-137`) mais **non structurée** (pas de feuille `mixite`) | **MÊME VALEUR, NON MODÉLISÉE** |
| Distance entre constructions 3 m | absent | **ABSENTE** |

### Saint-André AX 255 + 256 — zone **UC** (`97409_saint_andre.yaml`)
| Règle archi | LABUSE | Verdict |
|---|---|---|
| 1 place / logement | stationnement UC variable (1 ou 1,5 pl selon surface/proximité gare), **statut `propose`** (`:291`) | **PRÉSENTE EN TEXTE** (compatible « 1 place » pour aidé/<50 m²), **non servie** en chiffre unique |
| PPR mentionné | overlay géométrique (pas regle UC) | déduit si couche présente |
| (contexte) hauteur 9/12 m | servie (`:258/265`) | — |

### Saint-Denis DL 247 + 248 — zone **Ud** (`97411_saint_denis.yaml`)
| Règle archi | LABUSE | Verdict |
|---|---|---|
| PPR rouge + bleu | overlays géométriques (rouge déduit, bleu signalé) | déduit / signalé |
| Hauteur max 18 m | **18 m** en secteurs Udop/Udp (`:446-461 / :541-556`) | **MÊME** (si parcelle en Udop/Udp) |
| Recul voie 4 m | **formule** voies ≥ 12 m : alignement ou 4 m ; < 12 m : 4 m (`:354-365`) | **MÊME / compatible** |
| Prospect L > H | **prospect L ≥ H servi**, calculé par parcelle (`hauteur_mode='prospect'`, `db.py:444`) | **MÊME** |
| Stationnement 1 place / 3 logements (RPA) | pas de régime RPA | **ABSENTE** |

**Synthèse témoins** : les règles « dures » que l'archi applique (hauteurs, reculs voie, CES, pleine terre,
prospect, 18 m) **concordent** avec LABUSE. Les écarts sont **systématiquement** sur les règles non
modélisées de Q1 : visiteurs, espaces verts/arbres, stationnement par type, vélos, distance entre
constructions, RPA, et la **condition** séparative conditionnelle. Deux cas « valeur juste mais non servie » :
le stationnement par type et la mixité de L'Étang-Salé (texte présent, pas branché).

---

## Q4 — RÉEMPLOI POUR LE NOUVEAU DOCUMENT (avis franc)

**À réutiliser tel quel :** (1) le **moteur Faisabilité 2 scénarios** (`faisabilite/scenarios.py` —
`terrain_libere` / `bati_garde`) qui produit déjà une table « 8 étapes » + section « Ce que le PLU permet »
+ ligne mixité : c'est à ~80 % le **tableau Réglementaire vs Projet** demandé, sans recalcul ; (2) toute
l'**infra PDF** (`exports/rendu.py` WeasyPrint 69, `theme.css` `@page`/cartouche, primitives `table_kv`/
`verdict`/`tuiles`/`section`, cover `builder._cover`, préfixes `numeros`) ; (3) l'**architecture Bloc**
(`exports/blocs/*`, fonctions pures `rendu(valeurs, ctx)`) ; (4) le **catalogue Docs** (`frontend/.../documents/
catalogue.ts` + `exports/builder.DOCUMENTS`) où ajouter une 9ᵉ carte ; (5) le **plan 2D du Gabarit**
(`gabarit/plan_svg.py`) comme **base du plan masse**.

**Recouvrement avec le Gabarit : document À PART, pas de fusion.** Le Gabarit actuel = *carte d'identité
réglementaire* 2D (zone d'implantation, reculs, hauteur, emprise) — **sans colonne Projet, sans coupe, sans
massing** (`exports/blocs/gabarit.py`, DOCS-1 §Lot C « 2D seulement »). L'Étude de faisabilité est le livrable
archi complet : Réglementaire **vs Projet** + coupe gabarit + plan masse (lotissement). Fusionner alourdirait
un document volontairement court et très imprimé (Dossier/Flash/Pré-dossier PC l'embarquent). **Le bon
découplage : l'Étude *réemploie* le bloc gabarit (plan_svg) et la section PLU, et ajoute Projet + coupe +
plan masse.** Le seul vrai chantier neuf, c'est le **rendu** (colonne Projet, coupe, plan masse) — les
*chiffres* existent déjà.

---

## Q5 — VERDICT

| Élément | Statut aujourd'hui | Effort pour l'Étude |
|---|---|---|
| Moteur 2 scénarios + table 8 étapes | servi (`scenarios.py`) | **faible** (réemploi) |
| Infra PDF / Bloc / cartouche / catalogue | servi (`exports/*`) | **faible** (réemploi) |
| Section « Ce que le PLU permet » + prospect + mixité | servie (`scenarios._plu_section`) | **faible** |
| ER / EBC / SUP déduits | fait (`db.py` + `gabarit/builder.py`) | **faible** |
| Pente / MNT exploitable | en base + coupe live (`profil_altimetrique.py`) | **faible** |
| **Tableau Réglementaire vs Projet** (rendu 2 colonnes + saisie projet) | données prêtes, rendu PDF à faire | **moyen** |
| **Coupe gabarit** (élévation) | hauteur/niveaux dispo, mais Gabarit **2D only** | **moyen** (nouveau rendu SVG à partir de `hauteur_m`/niveaux) |
| **Plan masse — lotissement** (lots + voirie + reculs) | plan 2D existe (`plan_svg.py`), pas de découpe en lots | **moyen/fort** |
| **Massing collectif** (implantation volumes) | — | **fort** |
| Mixité calibrée au-delà de St-Denis | 1/23 structurée, 16 en texte | **moyen** (transcription, PLU-CALIBRAGE-5) |
| Stationnement par typologie | ratio unique seulement | **fort** (modèle + extraction) |
| Espaces verts/perméabilité distincts, distance entre constructions, vélos/OM, répartition typologique | absents | **moyen→fort** selon règle |

**Ordre proposé — confirmé et affiné :**

1. **Règles manquantes** — commencer par la **mixité** (moteur prêt, PLU-CALIBRAGE-5 transcription) ;
   repousser stationnement-typologie / vélos-OM (fort, faible gisement).
2. **Tableau Réglementaire vs Projet** — réemploi direct du moteur 2 scénarios, rendu PDF 2 colonnes.
3. **Coupe gabarit** — élévation dérivée de `hauteur_m` + niveaux (nouveau SVG, pas de nouveau calcul).
4. **Plan masse lotissement** — enrichir `plan_svg.py` (lots + voirie + reculs).
5. **Massing collectif** — en dernier (effort fort, pas de pré-requis de données).

**Conclusion** : la matière *chiffrée* d'une étude de faisabilité archi est déjà là et concorde avec les
témoins sur les règles dures. Le document est surtout un **chantier de rendu** (colonne Projet + coupe +
plan masse) posé sur le moteur et l'infra PDF existants — à faire en **document distinct** du Gabarit,
qu'il réemploie. Les seuls vrais trous *de données* sont les règles « de confort » non modélisées
(visiteurs/PMR, espaces verts/arbres, distance, vélos/OM, RPA, typologie), à calibrer par un
PLU-CALIBRAGE-5 **mixité en tête**.
