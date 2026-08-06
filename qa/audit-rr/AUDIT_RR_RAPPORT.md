# AUDIT RR — le chiffre qui vend LABUSE (M39-BIS, lecture seule)

**Branche** `audit-rr-fond`, base `main` `570aac85`. **LECTURE SEULE** : aucune écriture DB, aucune
modification de `src/`/config. Chaque affirmation est adossée à un script versionné (`qa/audit-rr/`)
+ CSV.gz, avec effectif et IC95 (Katz-log). Harnais gelé : fold 2025 (`p_model_ext_dataset`), scores
out-of-sample `reports/m36-foncier/scores-2025-fold-final.csv`, hors copro, ex æquo seedés 974.
**Contrôle île reproduit : RR@1158 = 6,6–6,7×** (gelé 6,73). Base de mutation île = 1,51 %.

---

## LOT A0 — LES DEUX QUESTIONS DE LA VAGUE 2 (en tête, sans les adoucir)

### A0.1 — Le paradoxe du permis (`a0_1_permis.py`)
**La prémisse du mandat est infirmée sur pièces** : aucune feature ne pèse « +1,30 ». Coefs réels
(model-card) : `permis_bin` (permis SUR la parcelle) coef **0,045** / IV **0,045** (7ᵉ) ;
`permis_24m_norm` (densité permis du secteur) coef 0,283 / IV 0,023. La feature DOMINANTE est
`tenure_bin` (ancienneté de détention, IV **0,209**), puis `zone_plu` (0,140), `rot_bati` (0,108).
Le permis n'est PAS le moteur du modèle.

**MAIS empiriquement, le permis est partout dans les têtes :**
| Univers | n | base | RR (têtes) [IC95] |
|---|---|---|---|
| Île (contrôle) | 428 k | 1,51 % | **6,61 [5,56 ; 7,87]** |
| **SANS permis** (92 % du parc) | 392 970 | 1,49 % | **4,50 [3,59 ; 5,64]** |
| **AVEC permis** (8 %) | 35 269 | 1,84 % | **12,60 [8,67 ; 18,32]** |

- **Les têtes sont à 85,6 % porteuses d'un permis** (vs 8,2 % du parc) — confirme M42.
- **Le pouvoir prédictif SURVIT sans aucun permis : RR 4,5×** (IC exclut 1). Le produit ne fait pas
  QUE « détecter un permis déjà déposé ».
- **Mais le 6,6× headline est un MÉLANGE** fortement tiré par les 8 % à permis (RR 12,6). Le permis
  est as-of propre (daté avant le label — prédicteur légitime), mais **public et trouvable en
  Sitadel** : la valeur ajoutée PROPRE de LABUSE est le tri à ~4,5× sur les 92 % sans permis.

### A0.2 — Fuite temporelle sur TOUTES les features (`a0_2_anteriorite.py`)
Par construction (dictionnaire) : features DVF/Sitadel/tenure/permis = as-of propres, **0 % postérieur**
au label. La fuite est ailleurs — les **couches STATIQUES « millésime unique, ingestion 2026 »** sont
**100 % postérieures** au label 2025 ; fuite RÉELLE si l'attribut CHANGE avec la mutation
(bâti/canopée/NDVI/friche/piscine/PV/densité/dormance/SDP), nulle s'il est invariant (pente, surface,
socio-démo, distance).

| Catégorie | Part de l'IV | Fuite |
|---|---|---|
| Features as-of propres (DVF/Sitadel/tenure/permis) | ~52 % | non |
| Statiques INVARIANTES (pente, surface, filo, qpv, accès) | ~12 % | non |
| **Statiques qui CHANGENT avec la mutation** (bâti, canopée, friche, piscine, PV, densité, dormance, SDP) | **23,5 %** | **OUI** |
| `zone_plu` (reclassement PLU postérieur possible) | 12,1 % | partielle |
| **Fuite TOTALE (borne SUPÉRIEURE, univariée)** | **35,6 %** | |

**La dette « fuite des couches statiques » est enfin chiffrée : jusqu'à 23,5 % (dure) à 35,6 % (avec
zonage) de l'information univariée** vient de features décrivant l'état POST-mutation (2026 vu après
2025). C'est une **borne supérieure** (l'IV est univariée ; la contribution marginale dans le modèle
L2 régularisé est ≤). **Test définitif NON exécuté** (re-scorer sans ces features = retrain, hors
lecture-seule) — **signalé comme la prochaine mesure à faire pour trancher la contribution marginale.**

---

## LOT A — La méthode est-elle solide ? (`dictionnaire-features.md`, `algo1_rr_commune.py`)
- **Population** : parcelles du fold 2025 avec label non nul, **hors copro** (`p_model_ext_copro`).
- **Fenêtre / label** : label L2-F = mutations DVF de [01/01/2025, 31/12/2025] (nature L2 dédupliquée,
  `exclue_l2f` retirée). Features strictement antérieures au 01/01/2025 (as-of).
- **« Tête »** = top-K par score out-of-sample (K=1158 gelé), ex æquo **seedés 974** (jamais l'ordre
  de table — fragilité M36 : au bord du top, 988/1000 sont ex æquo, palier de 514 ; l'allocation
  exacte par commune dépend du seed → RR île défini « à l'ordre des ex æquo près »).
- **RR** = (taux mutation dans le top) / (taux base). IC95 Katz-log.
- **Biais classiques** :
  - **Censure à droite** : OUI, présente — cycle DVF semestriel, ~6 mois de latence + S1-2026 non
    publié. Le label 2025 est quasi complet (millésime clos) ; l'effet est faible sur 2025 mais réel
    sur les folds récents. *Non re-quantifié ici (M36 lot2_b0_censure existe).*
  - **Biais de survivance** (parcelles sorties par division/fusion) : **NON TESTÉ** — nommé, pas mesuré.
  - **Circularité** (feature dérivée de la mutation) : les features as-of l'excluent par construction ;
    le RISQUE résiduel = les couches statiques 2026 (A0.2) + l'event-bascule côté tiers servis (C.1).
- **Robustesse top-K** (`c4_precision_tete.py`) : le RR TIENT et se resserre proprement —
  top-50 **14,5×** [8,6;24,5] · top-100 13,2× · top-200 10,9× · top-500 8,4× · top-1158 6,6×.
  **Robustesse fenêtre 12/24/36** : NON re-testée ici (fold unique 2025 ; le walk-forward M36 couvre
  le multi-millésime, RR@1158 ~6,73).

---

## LOT B — Pourquoi certaines communes décrochent (`b_commune_rr_ic.csv`)
Verdicts (RR intra-commune, top-k_c ∝ 1158, IC95 Katz) :
- **10 concluantes HAUTE** (IC bas > 1, ≥5 mutés) : Sainte-Suzanne (19,5), L'Étang-Salé (17,9),
  Le Port (16,1), Saint-Benoît (14,0), Petite-Île (9,8), **Saint-Pierre (9,3 [5,9;14,7])**,
  Saint-André (8,5), **Saint-Paul (4,6 [2,6;8,2])**, **Saint-Denis (3,8 [1,7;8,2])**, **Le Tampon (3,1 [1,4;6,7])**.
- **8 concluantes à effectif limite** (IC bas > 1, <5 mutés) : Sainte-Rose, Saint-Philippe, Les Avirons,
  La Plaine-des-Palmistes, Sainte-Marie, Saint-Leu, La Possession, Saint-Louis.
- **3 NON concluantes (IC couvre 1)** : Salazie, Entre-Deux, Saint-Joseph.
- **3 nulles (0 muté en tête)** : Bras-Panon, Les Trois-Bassins, Cilaos — **non concluant par PETIT
  ÉCHANTILLON**, PAS un échec prouvé (0/14-18 en tête, base ~1 % → attendu ~0,2 muté ; l'IC ne
  distingue pas de la base). Ne rien conclure.

**B.3 — Les 4 gros marchés « sous la moyenne » : diagnostic.** Ils **prédisent tous** (concluantes
hautes, IC exclut 1), mais à RR plus BAS que l'île (6,7×). **Ce n'est PAS un artefact de taux de base**
(Saint-Pierre 1,51 %, Saint-Paul 1,74 %, Saint-Denis 1,60 %, Le Tampon 1,71 % ≈ base île 1,51 %).
Le score discrimine simplement MOINS bien en foncier urbain dense. *Cause profonde = hypothèse (features
île-globales moins ajustées au périurbain dense) — **NON testée** ; à éprouver (RR par typologie intra).*

**B.2 — Pourquoi si peu de têtes (Bras-Panon 8-11).** Petit gisement (n=6016, un des plus petits) +
base la plus basse (0,96 %). L'allocation exacte au bord du top-1158 dépend du seed (palier d'ex æquo,
cf. Lot A) — une fragilité connue, pas un choix. **Coupure en plein palier : plausible, non isolée ici.**

---

## LOT C — Mesures alternatives
### C.1 — MONOTONIE (le test le plus important, `c1_monotonie.py`)
- **B. Strates du score FOLD out-of-sample (2025-aligné) = le test VALIDE : MONOTONE.**
  top-118 **13,4× [9,4;19,2]** › 119-1156 **5,9× [4,8;7,1]** › 1157-31134 **2,1× [1,9;2,2]** › reste 0,9×.
  **La hiérarchie du score TIENT.** C'est le résultat à retenir.
- **A. Tiers SERVIS × label 2025 : NON monotone en apparence** (brûlante RR 1,12 [0,28;4,42] non
  concluant, 2/118 ; chaude RR 20,86 ; réserve 0,20 ; à-creuser 1,41). **Mais comparaison BIAISÉE** :
  le run servi est PROSPECTIF (prédit la mutation à VENIR), le label 2025 est passé relatif — une
  brûlante servie est précisément une opportunité PAS ENCORE mutée (attendu : peu de mutations 2025).
  Le RR 20,86 des chaudes **sent la circularité event-bascule** (BODACC procédure → chaude → vente
  forcée 2025). → **Non probant pour la monotonie ; ne PAS lire comme un échec du score.**

### C.4 — Précision en tête (`c4_precision_tete.py`) — le chiffre qui parle au promoteur
**11 des 50 premières ont muté en un an (22 %)** · 20 des 100 (20 %) · 64 des 500 (12,8 %) · base 1,5 %.

### C.2 (bassin) / C.3 (typologie) — **NON TESTÉS** (nommés, pas mesurés). Recommandation : regrouper
les 6 communes non concluantes par bassin **augmente n** et peut atteindre la concluance au niveau
bassin (claim différent, honnête) — à mesurer avant tout usage régional.

---

## LOT D — Ce qu'on a le DROIT de dire (livrable commercial)

**Prouvé, formulation honnête :**
- « Les parcelles en tête de classement mutent **environ 6 à 7 fois plus** que la moyenne du parc »
  (RR@1158 = 6,6× [5,6 ; 7,9], out-of-sample 2025). **Robuste** : plus on resserre, plus c'est net
  (14,5× sur le top-50).
- « **1 parcelle sur 5 du top-100 a muté en un an** » (20 %, vs 1,5 % de base). Le top-50 : **11 sur 50 (22 %)**.
- « Le classement est **monotone** : plus une parcelle est haut, plus elle mute (13× › 6× › 2× › <1×). »

**Prouvé par commune :** promettre un facteur SEULEMENT dans les **10 communes concluantes hautes**
(Sainte-Suzanne, Étang-Salé, Le Port, Saint-Benoît, Petite-Île, Saint-Pierre, Saint-André, Saint-Paul,
Saint-Denis, Le Tampon). **Ne RIEN promettre** à Bras-Panon, Les Trois-Bassins, Cilaos (0 muté en tête)
ni Salazie, Entre-Deux, Saint-Joseph (IC couvre 1).

**Ce qu'il ne faut JAMAIS dire :**
- « 6,7× **partout** » — faux : varie de 3× à 19×, et **6 communes sur 24 sont non concluantes**.
- « Le modèle prédit **votre** mutation » — c'est un lift STATISTIQUE de population, pas une prophétie parcellaire.
- « LABUSE **découvre** des opportunités neuves » sans dire que **85 % des têtes portent déjà un permis
  public** (Sitadel). La découverte propre est ailleurs.

**Réponse type à « et dans MA commune ? » quand c'est non concluant (sans esquive ni survente) :**
> « Sur votre commune, l'échantillon de mutations 2025 est trop petit pour un facteur fiable
> (N observées). Je ne vous promets pas un chiffre — je vous montre le classement, sa méthode, et
> vous jugez sur pièces. Là où on a la matière (10 communes), le facteur tient ; ailleurs on est
> honnête sur l'incertitude. »

**Ce que le modèle détecte VRAIMENT (selon A0.1) — la phrase honnête :**
> « LABUSE détecte **où la mutation foncière se concentre**. Une grande part des têtes portent déjà un
> permis (info publique, Sitadel) ; **la valeur ajoutée propre de LABUSE est le tri à ~4,5× sur les
> parcelles SANS aucun permis** — là où l'information n'est pas déjà sur la table. Et une partie du
> signal (jusqu'à ~¼) vient de couches d'état 2026 : à durcir (dette consignée). »

---

## Ce qui reste à ÉPROUVER (honnêteté — jamais « pas de problème » sans le test)
1. **Ablation propre A0.2** : re-scorer SANS les couches statiques 2026 → contribution marginale réelle
   de la fuite (≤ 35,6 %). Le test définitif. Retrain requis.
2. **Biais de survivance** (parcelles divisées/fusionnées sorties du parc) : NON testé.
3. **Robustesse fenêtre 12/24/36** hors M36 : NON re-testée sur ce fold.
4. **C.2 bassin / C.3 typologie** : NON mesurés.
5. **Circularité event-bascule** (C.1-A, chaude RR 20,86) : à isoler (RR chaude HORS event BODACC).

Scripts : `a0_1_permis.py` · `a0_2_anteriorite.py` · `c1_monotonie.py` · `c4_precision_tete.py` +
`b_commune_rr*.csv`. Tous les CSV en `.gz`. **Aucune écriture. Pas de merge.**
