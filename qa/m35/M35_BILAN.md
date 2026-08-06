# M35 — BILAN (cohérence & nettoyage confiance)

**Branche `m35-coherence-nettoyage`** · base `main` 0b89d877 (post-M34) · commits atomiques
`[M35-LotA…E]`. **Aucune écriture sur le run servi, les tiers ou le cache scoring** — le mandat
touche l'affichage, les compteurs, la référence golden et du code non servi.

## LOT A — Golden : référence régénérée, 117/117

Geste gardé `qa/golden_regen.py` (117 parcelles relues, **84 ancres J3 préservées**, 0 triplet
cascade/matrice/tier bougé, référence cite `q_v8_calibre` — garde #6 OK). Résultat : **117/117**.

Les 2 écarts actés (cause : writer externe hermes, désactivé 05/08 — les valeurs nouvelles sont
celles que M32 déclare correctes, max(BD TOPO, CoSIA)) :

| IDU | champ | avant (référence M32) | après |
|---|---|---|---|
| 97411000AO0748 | sdp_residuelle_m2 · taux_emprise_pct | 7 013 · 0 | 6 888 · 1 |
| 97423000AB1908 | sdp_residuelle_m2 · sous_densite · taux_emprise_pct | 122 · true · 0 | 0 · false · **118** |

(AB1908 : la structure CoSIA 160 m² cesse d'être servie « terrain nu » — l'intention M32.)

## LOT B — Motif client : la machinerie ne sort plus

- `served_run_exceptions.motif_client` (nouvelle colonne) : formulation PRODUIT ; le motif
  interne (M28/M32, scores FLAIR, dettes, prénoms, IDU tiers) reste INTACT en base pour la
  traçabilité et **n'est plus jamais servi**.
- `verdict_servi` ne lit que `motif_client` ; exception sans motif client → repli neutre
  (« Classement ajusté après vérification manuelle — détail disponible sur demande. »), jamais
  le motif brut. Toutes les surfaces (fiche, exports md/html, one-pager, comparateur, assistant,
  shortlist) héritent par le point M34 — **confirmé** : `served_run_exceptions` n'a qu'UN
  lecteur dans src (`verdict_servi`), vérifié par grep + bout-en-bout AL1154.
- Les 5 entrées auditées et réécrites côté client (interne → client) :

| IDU | motif client servi |
|---|---|
| AL1154 | Piscine détectée sur imagerie aérienne 2025 — usage du terrain à vérifier. |
| AK1442 | Piscine centrale détectée sur imagerie aérienne 2025 — un terrain avec piscine n'est pas un terrain nu ; usage à vérifier. |
| AP0323 | Occupation vérifiée sur imagerie aérienne 2025 — bâti mineur sous le seuil, terrain servi au classement. |
| AT0870 | Occupation vérifiée sur imagerie aérienne 2025 — servie au classement. |
| HE0234 | Géométrie de parcelle atypique vérifiée — servie au classement. |

- **Consigne pour les gestes futurs** : toute bascule qui écrit le registre écrit `motif` ET
  `motif_client` (à intégrer au prochain script de bascule).
- 2 verrous : mots interdits (mandat/prénom/modèle/dette/IDU tiers) absents du motif servi ;
  repli neutre.

## LOT C — Trois pourcentages : trois grandeurs, trois libellés

Cartographie (CY0197 : 29/22/46 · CX0639 : 32/27/54) — les trois chiffres sont JUSTES :

| Où | Grandeur | Dénominateur | Source | Point de calcul |
|---|---|---|---|---|
| badge division | bâti au sol / parcelle | surface parcelle | max(BD TOPO, CoSIA) | `parcel_filtre_bati.ratio_pct` (builder M28) |
| texte vigilance | bâti au sol / parcelle | surface parcelle | **BD TOPO seul** | `bati.py::stats_batch` (rail R1 — mesure NON modifiée, ses seuils alimentent les signaux) |
| résiduel | bâti au sol / emprise constructible | **emprise constructible max** | max(BD TOPO, CoSIA) | `residuel.py::compute_residuel` |

**Décision (2)** : trois libellés explicites, PAS de chiffre unique — les dénominateurs
diffèrent par construction (46 % ≠ 29 % n'est pas une contradiction, c'est deux questions
différentes). Relabels appliqués : badge → « bâti au sol ~N % de la parcelle » ; one-pager
résiduel → « bâti au sol = N % de l'emprise constructible max » (l'export abrégeait en
« de l'emprise » — c'était LA confusion) ; la vigilance disait déjà « (BD TOPO) ».

**Signalement architecture (3)** — non contourné : « emprise bâtie max » est calculée à DEUX
endroits — cache `p_model_bati` (build, consommé par filtre_bati) ET recalcul live
`residuel.py` (stats BD TOPO + parcel_bati_revele). Même formule, deux points de calcul →
candidat à unifier au prochain geste scoring (lire `p_model_bati` dans residuel).

## LOT D — Chiffres décorrélés du tier

**D1 · `/communes` basculé** sur les tiers servis (« chaudes » = brûlantes + chaudes, même
convention que /stats ; dossiers/sans-identité alignés ; `evaluees` = présentes au run).
La dérive était réelle — extraits avant (matrice) → après (tiers) :
Saint-Denis 29→103 · La Possession 54→112 · La Plaine-des-Palmistes 0→35 · Saint-Joseph 17→64 ·
Saint-Paul 213→213. NB : le sélecteur n'affiche plus les compteurs par ligne (VUES item 6) —
l'effet visible est l'ORDRE de la liste (capture 5).

**Inventaire des lecteurs `matrice_statut` restants** (aucun autre COMPTEUR produit ; à
migrer avec l'extinction (c) du rail legacy, post-Train 8) :
- sélections des modules Outils : `modules.py:599/606/1076` (`IN ('chaude','a_surveiller','a_creuser')`) + payloads `statut` (198/396/527/588/715/1070) — des OUTILS sélectionnent encore par matrice ;
- digest hebdo : `events.py:86` (transitions de/vers matrice) ;
- payloads fiche/listes v2 (`statut`, étiqueté « historique » à l'écran) + filtre `statuts` deprecated + `/stats?legacy=1` ;
- interne non affiché : `score_v.py:595`.

**D2 · Score d'opportunité — DÉCORRÉLÉ du tier (mesuré, rien d'implémenté)** :

| tier | n | score médian | min–max |
|---|---|---|---|
| réserve foncière | 2 964 | **57** | 0–85 |
| chaude | 1 041 | 56 | 1–88 |
| **brûlante** | 119 | **54** | 17–80 |
| à creuser | 29 974 | 52 | 0–86 |

Les médianes se tiennent en 5 points sur les 4 tiers et les brûlantes sont SOUS les réserves :
ce score (cascade legacy) ne porte aucune information de classement — il ne peut que
contredire le tier (AL1154 65 > AT2542 61 = le cas type, structurel).
**Recommandation : RETRAIT des surfaces client** (« Opportunité N/100 » des exports/one-pager
et du bloc verdict legacy) — le tier + rang portent le classement ; conserver le score en
API/interne (audit, golden). L'alternative « re-libellé » (ex. « indice dossier historique »)
garde un chiffre qui n'informe pas — déconseillée. **Feu vert Vic requis.**

**D3 · Complétude — quasi-constante (mesuré)** : 3 valeurs sur tout le parc —
92 × 274 123 · 74 × 154 010 · 84 × 3 530. Elle n'informe pas (d'où le « 92/100 » sur les 7
captures M34). **Recommandation : retrait de l'affichage client** ; la vraie jauge par
parcelle existe déjà : l'ICD (0-100, 9 groupes, servi en fiche v2). **Feu vert Vic requis.**

## LOT E — Nettoyage confiance

1. **Score V hors affichage** : déjà fait (ALGO-1 §2 mergé) — re-vérifié : zéro `score_v`/
   `v_band` dans export.py / pdf_premium / briques_pdf ; payload API conservé (audit + golden).
2. **Vue legacy** `v_parcelles_brulantes` : déjà un DROP idempotent (ALGO-1 §3). 
   **`mutation.py` SUPPRIMÉ** (décision Vic M35 ; ALGO-1 recommandait conserver-documenter) :
   module + 3 endpoints `[NON SERVI §7-G]` + tests. Récupération : `git revert`.
   Reliquat consigné : `docs/product/RADAR_MUTATION_*` restent (historique du retrait).
3. **2 docs fausses supprimées** : `docs/BAREME_VERDICT_MUTABILITE.md`,
   `NOTES_SCORING_DRYRUN.md` (les 2 d'ALGO-1 §5, bandeaux → suppression).
4. **5 features instables retirées des entraînements futurs** (M36 stabilité des signes —
   coefficients quasi nuls, signe non stable) : `permis_24m_norm`, `filo_dens_pop`, `qpv`,
   `window_coverage`, `dormance_droits` → `retired=True`. Le registre RESTE complet
   (l'artefact SERVI épinglé les référence — un retrait physique casserait le re-score des
   bascules) ; `FEATURE_NAMES_ACTIFS` (24/29) = base contractuelle de tout fit futur ;
   retrait physique au prochain ré-entraînement.
5. **Zéro impact tier** : aucun fichier du pipeline servi touché ; golden 117/117 après lot.

## QUESTIONS PRODUIT — recommandations (rien d'implémenté)

1. **« bâti au sol = 112 % de l'emprise constructible max » (BW0326)** — NE PAS plafonner :
   > 100 % est un FAIT (bâtiment existant au-delà de la règle actuelle — antériorité ou
   géométrie divergente) et un plafond à 100 % serait un mensonge doux. Reco : libellé dédié
   au-delà de 100 % : « bâti existant au-delà de l'emprise constructible actuelle (~112 %) —
   antériorité probable ou géométrie divergente ». Une ligne de rendu, même point de calcul.
2. **Fourchettes à bornes identiques (« CA ~875 k€–875 k€ »)** — valeur unique préfixée « ~ »
   quand les bornes coïncident À L'AFFICHAGE (« CA ~875 k€ ») ; ne jamais élargir
   artificiellement (inventer de l'incertitude = aussi faux que la sur-précision). Si
   l'égalité vient de l'arrondi, la valeur unique reste la lecture honnête.
3. **« rang 231 153 » (AI1821)** — afficher le rang UNIQUEMENT sur brûlante/chaude (où il est
   un argument de tête) ; réserve/à-creuser affichent le tier seul. Un seuil numérique
   (masquer > N) serait arbitraire ; le critère « tiers hauts » est déjà la sémantique du
   produit. (Aujourd'hui M34 affiche le rang sur tout servable — resserrement d'une ligne.)

## VÉRIFICATION

1. Golden **117/117** après Lot A, re-vérifié **117/117** après Lot E (API bootée sur le code
   M35, 0 incohérence base↔API).
2. Non-régression M34 : re-mesure bout-en-bout (mesure_p2, 1 071 parcelles) — **0 divergence
   dans les deux sens, 0 vocabulaire legacy, 0 incohérence — PASS** (CY0197 : badge relabelé
   « bâti au sol ~29 % de la parcelle », tier intact).
3. Aucun changement de tier, aucune écriture run/cache scoring (diff en foi : affichage,
   compteurs, code non servi, tests, golden).
4. Captures `qa/m35/screens/` : 1 AL1154 (motif client nettoyé) · 2 CY0197 · 3 CX0639
   (pourcentages libellés) · 4 AP1610 (**nue banale — le témoin manquant de M34**) ·
   5 sélecteur /communes (ordre = tiers servis) · **5bis (reprise revue Vic)** carte île,
   analyse activée + `5bis_marqueurs_infobulles.txt` (dump VERBATIM du DOM).

   **Constat de surface (demande revue)** : les compteurs /communes ne sont AFFICHÉS en
   chiffres nulle part à l'écran — c'est un choix de design antérieur (P8/A2 post-revue :
   « plus de compteur de chaudes visible ») . Ils pilotent : l'ORDRE du sélecteur, la
   TAILLE/ÉCLAT des marqueurs communes de la carte île (analyse activée), et l'INFOBULLE
   native au survol du marqueur. Preuve chiffrée (DOM réel, 5bis_marqueurs_infobulles.txt) :
   « Saint-Denis — 103 en priorité dossier (matrice Q×A) » · La Possession 112 · La Plaine 35
   — les valeurs post-bascule. **Saint-Denis = 103 confirmé** (API /communes + DOM).
   ⚠ Relevé M36 : le wording de l'infobulle dit encore « (matrice Q×A) » alors qu'elle sert
   désormais les tiers — même famille que le badge carte « VERDICT · MATRICE Q×A » relevé
   par Vic (aucune modification ici, consigne « rien d'autre sur cette branche »).
5. Suite pytest : 1 301 verts (−21 = tests mutation supprimés) ; 5 échecs PRÉ-EXISTANTS hors
   périmètre (residuel ×4, au_ouverture ×1 — env test, consignés M34, reproduits sans les
   modifs). Écriture DB hors scoring, tracée : colonne + 5 valeurs `motif_client` (Lot B).

## Reliquats consignés

- Migration matrice → tiers des SÉLECTIONS modules Outils + digest events : avec l'extinction
  (c) du rail legacy (post-Train 8).
- Unification « emprise bâtie max » (p_model_bati vs residuel live) : prochain geste scoring.
- D2 (score opportunité) et D3 (complétude) : retraits recommandés, en attente d'arbitrage.
- Q1/Q2/Q3 : recommandations ci-dessus, en attente d'arbitrage.
- `docs/product/RADAR_MUTATION_*` : historique conservé du module supprimé.
