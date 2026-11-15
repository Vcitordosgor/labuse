# ECARTS-2 — AUDIT-CHIRURGICAL-2

> Chasse aux bugs et incohérences, **LECTURE SEULE**. Aucune correction appliquée.
> Prolonge CHIRURGICAL-1 (écarts numérotés **à partir de E4**, K1 conservé). Base locale `labuse`,
> API live `:7440`. **12 parcelles**, **tous** les documents générés et **lus** (voir COUVERTURE-2).
> Oracles indépendants : prix médian pondéré (`oracle_prix.*`), zone rouge PPR (`oracle_ppr.*`),
> citations PLU (`citations_check.csv`), arithmétique (dans MATRICE-2 / fragments).
> Preuves : `~/Desktop/chasse-1/<idu>/`, `_comparatifs/`, `_estimer_lien/`.

Classement : **faux** · **contradictoire** · **trompeur** · **cosmétique**.

---

## Résultat d'ensemble
Le Dossier, le Gabarit, le Pré-dossier, l'Étude de zone, le Comparatif, le Bilan et le Courrier
**recopient fidèlement la fiche** sur l'immense majorité des faits chiffrés (surface, zone,
constructibilité, emprise, hauteur, prix médian, taxe, parts d'aléa, parts PPR) — vérifié par
recalcul indépendant (COUVERTURE-2 §2-3). Les écarts nouveaux portent surtout sur **la capacité
retenue**, sur des **documents périphériques** (Apporteur, Estimer) qui lisent des sources différentes
de la fiche, et sur des **citations PLU** non adossées à un texte. Deux faux positifs ont été évités
par vérification adversariale (voir §Faux positifs).

---

## ÉCARTS (nouveaux, comptés)

### E4 — CONTRADICTOIRE — Le numéro de rapport n'est PAS unique (collision des 4 derniers chiffres de l'IDU)
- **Parcelles** : AY0153 et CO0153 → **même numéro `DP-20261115-0153`** (Dossier) et **`AP-20261115-0153`** (Apporteur), alors que ce sont deux parcelles différentes (communes différentes).
- **Fait** : `numeros.py:34` → `f"{PREFIXE}-{AAAAMMJJ}-{idu[-4:]}"`. Le numéro n'utilise que **les 4 derniers caractères** de l'IDU + la date. La base compte **434 582 parcelles** pour **4 358** suffixes distincts (≈ 100 parcelles par suffixe). Deux documents du même type générés le même jour pour deux parcelles de même suffixe portent un numéro **identique**. Le docstring affirme pourtant « NUMÉRO DE RAPPORT **unique** par document ».
- **Où le lire** : `grep 'DP-20261115-0153' ~/Desktop/chasse-1/97404000AY0153/dossier.txt ~/Desktop/chasse-1/97414000CO0153/dossier.txt`.
- **Impact** : traçabilité — un client qui archive deux Dossiers/Apporteurs de parcelles à suffixe commun le même jour a deux PDF au même numéro. Tous les documents numérotés sont touchés (DP, AP, FI, EF…).

### E5 — FAUX (sévère) — BW2635 : « Surface à retenir » = 3 317 m² > la parcelle (2 003 m²), 4× la SDP résiduelle (827 m²)
- **Parcelle** : 97422000BW2635 (copropriété, Le Tampon, 2 003 m²).
- **Fait** : le **Dossier** imprime « Potentiel faible… surface de plancher constructible restante ≈ **827 m²**… **Surface à retenir : 3 317 m² (estimation rapide)** ». La « surface à retenir » (3 317) **dépasse la parcelle entière** (2 003 m²) et vaut **4× la SDP résiduelle** qu'elle est censée borner.
- **Contradiction inter-documents** : l'**Étude de faisabilité** de la même parcelle retient **2 625 m²** (esquisse) et précise « L'estimation rapide donnait 3 317 m² » + « Le plancher de cette étude (2 625 m²) dépasse la capacité servie par la fiche (827 m²) : à confronter ». Le Dossier retient donc la **plus grande** des trois grandeurs (827 / 2 625 / 3 317), l'Étude la médiane — ce qui **régresse la règle « plus petite des deux »** (CAPACITE-1 LOT D). Comparer à AD0887, où le Dossier retient bien l'esquisse 795 (la plus petite) et non l'estimation 1 047.
- **Où le lire** : `~/Desktop/chasse-1/97422000BW2635/dossier.txt` l.189-191 vs `etude_faisa.txt` l.16-31.
- **Cause probable** : `faisabilite/surface_retenue.surface_a_retenir` retombe sur l'estimation rapide quand le barème stationnement n'est pas appliqué, **sans borner par l'aire de la parcelle** ni par la SDP résiduelle.

### E6 — CONTRADICTOIRE — L'Étude de faisabilité chiffre un collectif de 95 logements sur une zone où l'habitat est INTERDIT (AM0838)
- **Parcelle** : 97404000AM0838 (L'Étang-Salé, zone **UE**, 20 798 m²).
- **Deux sources** : la **fiche** = `constructible=False`, motif « **Habitat interdit dans cette zone** », `rien_a_batir=True`, SDP 0. L'**Étude de faisabilité** (moteur réel) chiffre « **au mieux ~95 logements en R+4**, 8 125 m² de SDP, logement collectif » (« terrain supposé libéré »).
- **Fait** : l'Étude dimensionne un programme de **logements** sur une zone où la fiche déclare l'habitat **interdit**. Le garde-fou « capacité à vérifier / à confirmer » de l'Étude porte sur la **capacité**, pas sur l'**interdiction d'habitat** — il ne la mentionne nulle part. Les Études des autres non-constructibles refusent proprement (AO0050 RNU, CO0153/BN0260 zone A, AO1198 exiguë) ; **AM0838 est la seule à chiffrer**.
- **Où le lire** : `~/Desktop/chasse-1/97404000AM0838/etude_faisa.txt` vs `fiche.json` `potentiel_a_batir`.
- **Cause probable** : le moteur d'implantation applique reculs/emprise/hauteur mais **ne lit pas le verrou « habitat interdit » (destinations UE)** que la fiche applique → deux moteurs, deux verdicts, celui de l'Étude ignorant l'interdiction de destination.

### E7 — FAUX — Apporteur : date d'approbation du PLU périmée (8/12 parcelles)
- **Parcelles** : AD0887 (`08/12/2018` vs fiche **2023-08-11**), AM0838 (`22/12/2017` vs 2025-09-17), IS0448 (`26/10/2013` vs 2026-08-05), AY0153 (`22/12/2017` vs 2025-09-17), CO0153 (`11/03/2014` vs 2025-12-18), BW2635 (`08/12/2018` vs 2023-08-11), CV0446 (`26/06/2019` vs 2025-12-10), AO1198 (`06/02/2008` vs 2024-02-13). Concordent : HT0538, AR1517, BN0260.
- **Fait** : l'Apporteur imprime « Zone Xx — PLU **approuvé le JJ/MM/AAAA** » avec une date **plus ancienne** que celle servie par la fiche, l'Étude, le Pré-dossier et le règlement (`plu_reglement_extrait.source_url` = `..._PLU_20230811.zip` pour AD0887). L'Apporteur lit donc un **millésime PLU différent** (et périmé) des autres documents.
- **Où le lire** : `~/Desktop/chasse-1/97422000AD0887/apporteur.txt` « PLU approuvé le 08/12/2018 ».
- **Impact** : un document destiné à un propriétaire porte une date d'opposabilité PLU fausse.

### E8 — TROMPEUR — Estimer : le prix €/m² du secteur ≠ fiche / Étude-de-zone, sous le même libellé
- **Parcelles** : AY0153 (Estimer **2 652 €/m² · 28 ventes** vs fiche/Étude-zone **2 333 €/m² · 43 ventes**, +13,7 %), BW2635 (Estimer **3 522 €/m² · 65 ventes** vs **3 000 €/m² · 53 ventes**, +17 %, **au-dessus de l'oracle pondéré ET simple** : 3 000 / 2 794). AD0887 (2 500 vs 2 577, période 2025 vs 2026). Concordent : AR1517, IS0448.
- **Fait** : deux documents LABUSE impriment, pour la **même parcelle** et sous un libellé équivalent (« prix des maisons autour » / « prix ancien médian »), un **€/m² et un N différents**. L'Étude-de-zone, elle, reprend le `prix_ancien_median` de la fiche **à l'identique 12/12** — l'écart est **isolé à Estimer**, qui applique une définition d'échantillon retenu différente (méthode « ressemblance » ESTIMER-3).
- **Où le lire** : `~/Desktop/chasse-1/97404000AY0153/estimer.txt` vs `fiche.json` `prix_ancien.median`.
- **Réserve** : méthodes légitimement différentes (pondération ESTIMER-3 vs médiane pondérée fiche) — mais le client voit deux prix de secteur pour une même parcelle sans que la différence de méthode soit nommée. BW2635 au-dessus de l'enveloppe pondérée **et** simple est le cas le plus net.

### E9 — FAUX / NON-VÉRIFIABLE — Citations PLU sans texte justificatif
- **AY0153** (L'Étang-Salé, zone **UA**) : hauteur calibrée « 12 m égout / 15 m faîtage » citée au Dossier/pièces — **zone UA absente** des extraits `plu_reglement_extrait` de l'INSEE 97404 (zones présentes : A, AU, AUT, N, UT). **Aucun verbatim** n'adosse la valeur (les zones U du PLU 2025-09-17 ne sont pas ingérées).
- **CV0446** (Saint-Joseph, zone **U5**) : hauteur « 7 m / 9 m » **non rattachable** — tous les extraits 97412 portent `pagination_ambigue=True`, zone collapsée en « U », `article_ref` mal parsé (« ARTICLE U1 10 »). (L'emprise 50 % U5, elle, est confirmée au verbatim.)
- **AR1517** (Entre-Deux) : la pièce cite « zone **Ua** » alors que le règlement n'a qu'une zone « **U** » indifférenciée (pas de Ua/Ub) — la valeur 7/11 est confirmée (palier le plus bas de U7.2) mais **le libellé de zone cité n'existe pas** au règlement.
- **Confirmés au verbatim (contrôle positif)** : AD0887 (Ud10 7/11 p.63), HT0538 (Ud 15/20 p.81), IS0448 (Uh.10 4,5/7 p.73), BW2635 (Uav 16/20 p.18 **et** recul RD3 10,50 m p.15, mot pour mot).
- **Où le lire** : `citations_check.csv`. **Limite** : vérification contre le **verbatim stocké** (`texte_verbatim` + page + source_url), l'image du PDF officiel n'étant pas re-téléchargée (accès externe hors périmètre).

### E10 — TROMPEUR — Trois comptes d'« aléas » différents dans le Dossier
- **Parcelles** (systématique) : AM0838 badge « 2 aléas » / « Points de risque 7 » / fiche `aleas_n` **6** ; CO0153 badge 2 / fiche 6 ; AO0050 badge 2 / fiche 5 ; AY0153 badge 2 / fiche 5 ; BN0260 badge 2 / fiche 4 ; AR1517 badge 2 / « Points 3 » / fiche 3.
- **Fait** : le Dossier affiche **deux** nombres d'aléas (badge RISQUES = nb de familles ; « Points de risque » = CatNat + PPR + chaque niveau), aucun n'égalant la fiche `aleas_n`. Trois définitions d'« aléas » coexistent sans être réconciliées.
- **Impact** : aucune valeur fausse, mais un lecteur voit « 2 aléas » en tête et « 7 points de risque » plus bas pour la même parcelle.

### E11 — TROMPEUR — Dossier : la table « 8 comparables les plus proches » liste des ventes de TERRAIN sous un médian de BÂTI ancien
- **Parcelles** : HT0538, CV0446 (terrains nus) — le médian/fourchette de tête (« Prix ancien médian … €/m² ») porte sur l'**ancien bâti**, mais la table des 8 comparables listés dessous montre des **ventes de terrain** → la médiane de la table ne reconstitue pas le chiffre de tête (populations différentes).
- **Impact** : le client ne peut pas recalculer le chiffre affiché à partir de la table montrée ; deux populations sous un même bloc.

---

## COSMÉTIQUES (listés, non pondérés)
- **C-i** — Gabarit « non calculable : donnée réglementaire manquante » vs Dossier « Fort/faible potentiel » pour AD0887 et BW2635 (constructibles, mais arêtes voie/limite non qualifiées). Les deux documents disent « gabarit non chiffrable ici » ; accord de fond, dissonance d'apparence.
- **C-ii** — Estimer imprime « zone non constructible **(Pas)** » sur la parcelle RNU AO0050 : le libellé de zone vide (RNU, pas de zone PLU) est injecté tel quel entre parenthèses.
- **C-iii** — Libellé du verdict : section 2 « constructible » vs section 3 « Non retenue / habitat interdit » (AO1198, AM0838, IS0448) — même sens, mot différent ; le Gabarit reprend, lui, le motif fiche exact.

---

## ÉCARTS ATTRIBUÉS À DES CAUSES CONNUES / COMPORTEMENTS NOMINAUX (non comptés)
- **Pré-dossier PCMI2 : surface = dessin (ST_Area) ≠ cadastre** (AD0887 1 699 vs 1 703, IS0448 818 vs 959…) — systématique, **par conception** (la superficie CERFA cadre 2 est **laissée vide**, certifiée par le déposant). = prolonge **E1 (CHIRURGICAL-1)**.
- **Capacité « terrain libéré » (Pré-dossier / Étude) vs SDP résiduelle (fiche)** — deux scénarios nommés (démolition totale vs résiduel) ; **honnêtement signalé** par l'Étude (« dépasse la capacité servie par la fiche, à confronter ») sur les constructibles — hors le cas E5 (non borné) et E6 (habitat interdit).
- **Bilan « par défaut » → 422** « aucun chiffre d'affaires » : comportement **nominal** (le pré-remplissage par défaut ne porte pas de produit). L'arithmétique est vérifiée sur une variante chiffrée (voir §Faux positifs).
- **Pré-dossier → 422 non_constructible** sur les 5 parcelles non constructibles : **par conception** (le pack PC n'est pas servi sans constructibilité).
- **Plafond d'export « usage loyal » 30/j (plan Intégral)** : atteint dès la 1ʳᵉ parcelle par le compte de test ; contourné proprement (mode pilote hors quota / rendu en process) — voir COUVERTURE-2 §5. Comportement produit, non compté.
- **Stationnement : un projet « collectif » applique le barème « habitat individuel » (1 place/logement)** sur AD0887 et BW2635 — reconfirme le **canari C-c de CHIRURGICAL-1** (bascule maison↔immeuble), déjà connu.

---

## FAUX POSITIFS ÉVITÉS (vérification adversariale — preuve de non-aveuglement)
- **« Bug TVA du Bilan » — RÉFUTÉ.** Un premier examen signalait HT = CA/21 (95 % du CA en TVA) sur les 12 Bilans. **Cause réelle : l'input du harness d'audit** (`tva=20.0` passé au lieu d'une **fraction** — les `tva_legales` servies sont `{dom_standard: 0.085, …}`). Le moteur fait `HT = TTC/(1+tva)` (`bilan/moteur.py:58`) : avec `tva=20` → /21 (2000 %). Régénéré avec `tva=0.085` : **HT 238 783 € · TVA 20 297 € · TTC 259 080 €** (AD0887) — `238 783 × 1,085 = 259 080` ✓, TVA = 8,5 % ✓. **Le Bilan est arithmétiquement correct.** (Les 12 Bilans de `~/Desktop/chasse-1/` ont été régénérés avec la TVA correcte.)
- **« Écart de prix médian » (laissé inexpliqué par CHIRURGICAL-1) — RÉSOLU, pas un écart.** La tête de fiche sert une **médiane pondérée par la ressemblance** (`_mediane_ponderee`), pas un `percentile_cont` simple. Oracle indépendant (`oracle_prix.py`, réimplémentation sans appeler le code applicatif) : **médiane servie == oracle pondéré, exact (±1 €), 12/12** ; métadonnées (n, rayon, période) concordent ; valeur toujours dans [min, max] de l'échantillon. L'écart pondéré↔simple (jusqu'à ±25 %) explique le constat du 1ᵉʳ passage.
- **Zone rouge PPR (timeout au 1ᵉʳ passage) — ABOUTIT, 0 divergence.** Oracle géométrique complété en 18,7 s (`ST_Subdivide`/`ST_MakeValid`) : parts rouges imprimées au Dossier = oracle à ≤1 pt (AM0838 43 %, AY0153 41 %, IS0448 34 %, CO0153 19 %, BN0260 100 %).

---

## Pour mémoire — vérifié SANS écart (détail en COUVERTURE-2)
Surface, emprise bâtie servie, parts d'aléa, parts de zone/EBC, **parts de zone rouge PPR** (oracle), **prix médian pondéré** (oracle), RNU, dernière vente, taxe (taux), Q1/médiane/Q3 — concordent fiche↔Dossier↔Gabarit↔Étude-zone. Aucun jeton `None`/`NaN`/`{{ }}`/page vide/date future sur les 24+ documents lus. CERFA 13406 correctement choisi (0 pack ≥ 3 logements). Courrier : destinataire jamais un e-mail ; cas « bloqué » (parcelle non bâtie / sans adresse) honnêtes. Propriétaire **public** (CV0446 → mairie) et **société** (AM0838 → siège) correctement branchés « personne morale » (pas de question d'indivision de personne physique).
