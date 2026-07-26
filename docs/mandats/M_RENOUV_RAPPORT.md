# M-RENOUV — LE SEGMENT RENOUVELLEMENT · Rapport final

**Mandat** : rendre visible, comme segment SÉPARÉ, le gisement chiffré par DOC-P
(docs/SCORING_SPEC.md, annexe) : les parcelles écartées à l'étage 0 pour occupation bâtie
mais en zone U/AU avec capacité réelle. **Sans toucher au pipeline servi.**
**Filet** : tag `avant-renouv`. **Golden** : 116/116 à chaque lot + 3 cas nouveaux (lot C).
**Non-régression** : tiers servis identiques au bit près à chaque lot :
`brulante 120 · chaude 1 031 · reserve_fonciere 3 587 · a_creuser 72 980 · ecartee 353 945`.

## Branches (aucune mergée — merge Vic A → B → C, puis LOT D)

| Lot | Branche | Commits | Contenu |
|-----|---------|---------|---------|
| A | `feat/renouv-a-segment` | 27ddae2 | table + score + CLI `labuse renouv` + tests 8/8 |
| B | `feat/renouv-b-ui` | aae811f, ca411cd | fiche/carte/outil/PDF + preuves qa/renouv/ |
| C | `fix/renouv-c-gardes` | (tip) | méthodo Sources + golden étendu (+3 cas) |

B est branchée sur A (elle a besoin de la table), C sur B. Ordre de merge impératif A→B→C.

---

## LOT A — la table du segment

### A1 · Définition (figée) — les 5 conditions, toutes requises

1. exclue à l'étage 0 par **BatiLayer** (HARD_EXCLUDE francs : `deja_bati` ≥ 50 % d'emprise,
   `deja_bati_probable` ≥ 30 %, `ensemble_bati` ≥ 15 % ∧ (≥ 3 bâtiments ∨ 1 bât. ≥ 400 m²)) —
   lue dans `dryrun_cascade_results` du run servi, code reconnu par le préfixe du motif
   (contrat `bati.classify`, testé par symétrie) ;
2. `zone_plu ∈ {U, AU}` (p_model_ext_dataset, as-of 2026) ;
3. capacité : `sdp_residuelle_m2 > 100` **OU** `surface_m2 ≥ 600` ;
4. **non copro** (`p_model_ext_copro` : RNIC ∪ DVF) — un immeuble en copropriété ne se
   renouvelle pas par un acheteur unique ;
5. **non foncier public** : la couche cascade `foncier_public` (HARD_EXCLUDE = domaine non
   acquérable) **existe et est appliquée** — le stade municipal n'est pas servi comme potentiel.

### L'ENTONNOIR (mesuré, run `q_v7_defisc`, as-of 2026)

| Étape | Parcelles | Δ |
|-------|----------:|---|
| 1. écartées BatiLayer (codes francs) | **195 209** | = 55,1 % des 353 945 écartées |
| 2. ∩ zone U/AU | **182 330** | −12 879 |
| 3. ∩ capacité (SDP > 100 ou surf ≥ 600) | **73 078** | −109 252 (= chiffre DOC-P exactement) |
| 4. − copropriétés | **71 313** | −1 765 |
| 5. − foncier public → **SEGMENT FINAL** | **68 445** | −2 868 |

### A2 · Le score (heuristique transparente, config/renouvellement.yaml commentée)

`renouv_score` ∈ [0,100] = somme de 4 composantes stockées séparément, normalisation par
**percent_rank intra-segment** (robuste, sans échelle à calibrer) :
potentiel résiduel (SDP) **40** · assiette (surface) **25** · contexte de marché
(`rot_bati_brute` du secteur) **20** · divisibilité (`division_or_candidates`) **15**.
Le chargeur **REFUSE** une config dont Σ poids ≠ 100. Aucun modèle appris (le P dédié =
mandat futur). Distribution saine : étalée de 10 à 100, médiane ~45 ; 27 parcelles divisibles.

### A3 · Table et CLI

`parcel_renouvellement` (idu PK, score, 4 composantes, code_bati_origine, sdp/surface/zone
dénormalisés, commune, rang_segment, rang_commune, run_label, computed_at) — rebuild complet
idempotent, précédent `entonnoir_motifs`. `labuse renouv` : recalcul + entonnoir + top.

### Top 20 île (commenté)

| # | IDU | Score (p+a+m+d) | Zone | SDP | Surface | Origine |
|---|-----|-----------------|------|-----|---------|---------|
| 1 | 97403000AP1902 | 91 (38+23+15+15) | U | 1 224 | 1 881 | ensemble_bati |
| 2-4 | 97402000AK0262/1778/2042 | 87 (39+24+9+15) | U | 1 799-2 731 | 2 764-3 059 | ensemble_bati |
| 5-6 | 97403000AR0816, AS1143 | 86-85 | U | 1 274-2 445 | 1 762-3 069 | ensemble_bati |
| 7 | 97404000AZ0004 | 85 (40+25+20+0) | U | 11 040 | 16 418 | ensemble_bati |
| 8-20 | Le Port (AC0033, AS01xx…) | 85 (40+25+20+0) | U | 3 211-50 487 | 4 983-72 010 | mixte |

Lecture : deux profils en tête. (a) **Entre-Deux/Bras-Panon** (rangs 1-6) : parcelles moyennes
(1 800-3 000 m²) à SDP forte ET géométrie favorable (les +15 de divisibilité) — du
renouvellement « diffus » actionnable. (b) **Le Port** (rangs 8-20) : grandes emprises
d'ensembles bâtis aux trois composantes continues saturées (40+25+20) — du renouvellement
« d'îlot », plus lourd. Les ex æquo à 85 sont un artefact assumé du percent_rank (saturation
des hauts quantiles) ; le rang les départage par IDU (déterministe).

### Répartition par commune (les 8 premières)

Le Tampon 8 492 · Saint-Paul 8 108 · Saint-Denis 7 242 · Saint-Pierre 6 816 ·
Saint-André 4 758 · Saint-Louis 4 634 · Saint-Joseph 3 031 · Saint-Leu 2 859.
(Le Port ne garde que 888 : son gisement bâti est massivement **foncier public** — cohérent.)

**Preuves lot A** : entonnoir CLI, tiers avant/après identiques (diff vide), golden 116/116,
tests 8/8 (config, symétrie Python/SQL des codes, doctrine wording, définition A1 en base de
test, aucune écriture hors table, idempotence), suite complète = état de main (10 échecs
préexistants vérifiés sur un worktree main : 9 `test_front_reliquats` + 1 `test_auth` flaky
d'ordre — zéro régression).

---

## LOT B — servir le segment

- **B1 fiche** : verdict d'en-tête **INCHANGÉ** (« Écartée ») ; badge **cuivre**
  (`TOKENS.renouv #C9834E`, teinte propre — ni vert statut, ni violet signal, distinct de
  l'ambre viabilité) « **Renouvellement — rang N/M** » + libellé exact
  « Parcelle occupée — potentiel de renouvellement urbain » ; tiroir « pourquoi » = les
  4 composantes en barres points/max + rang commune + phrase de limite. La divisibilité
  s'affiche « **géométrie favorable** » (O12 : jamais une promesse de division).
- **B2 carte** : toggle « Renouvellement » (panneau couches, **OFF par défaut**) → couche
  geojson cuivre + légende « Renouvellement — occupées, potentiel de renouvellement » ;
  la troncature est **DITE** (toast « 1 500 affichées sur 8 108 (meilleurs rangs) — Saint-Paul »)
  — jamais un « tout » silencieux. Outil « **Renouvellement** » (groupe Détecter) : liste
  triable score/SDP/surface/rang commune, bandeau définition + avertissement permanent.
- **B3 exports** : **UNE ligne conditionnelle** dans la synthèse Flash (le Dossier la reprend,
  même moteur) : « Segment Renouvellement — parcelle occupée, potentiel de renouvellement
  urbain : rang 1/68445 (score 91/100). Composantes dominantes : … » — vérifiée dans le PDF
  réel (`qa/renouv/dossier_AP1902.pdf`), **zéro occurrence d'« opportunité » dans tout le PDF**.
- Backend : bloc fiche + `/map/renouvellement.geojson` + `/renouvellement/liste`, tous
  `to_regclass`-gardés (table absente → l'app vit normalement). Le flux principal `/parcels`
  n'est **pas** touché : pas de tri renouv_score dans la liste générale (doctrine : jamais
  mélangé aux Chaudes — le tri vit dans l'outil dédié).

**Preuves lot B** (commitées `qa/renouv/`) : `fiche_badge_ferme.png`,
`fiche_pourquoi_ouvert.png`, `carte_saintpaul_toggle_on.png` (cuivre visible au zoom, fiche
HK0117 rang 4/68 445), `outil_liste.png`, `dossier_AP1902.pdf`. Contrôles : fiche d'une
écartée hors segment → `renouvellement: null` ; tsc 0 ; build OK ; golden 116/116 ;
tiers identiques.

---

## LOT C — honnêteté et garde-fous

### Texte méthodo (page Sources, section « Segment Renouvellement ») — INTÉGRAL pour relecture Vic

> **Segment Renouvellement**
> Le classement principal écarte volontairement les parcelles **déjà occupées** (bâties).
> Le segment Renouvellement rend visibles celles d'entre elles qui restent en **zone
> constructible (U/AU)** avec une **capacité réelle** (surface constructible résiduelle
> supérieure à 100 m², ou assiette d'au moins 600 m²) — hors copropriétés et hors foncier
> public. Son score (0-100) est une **règle de calcul transparente**, pas un modèle
> prédictif : droits à bâtir résiduels (40), taille de l'assiette (25), rotation du bâti
> dans le secteur (20), géométrie favorable (15) — chaque parcelle est située par rang au
> sein du segment.
> ▲ **La limite : ce segment identifie un potentiel physique et réglementaire ; il ne prédit
> pas une mise en vente et ne constitue pas une opportunité qualifiée.**

(Variantes du même wording : info-bulle de la couche carte, bandeau de l'outil, tiroir fiche,
avertissement de l'API liste — tous sans le mot « opportunité » sauf pour le NIER.)

### Golden : les 3 cas ajoutés

1. **97413000DM0210** (déjà au jeu des 116, écartée riche, DANS le segment) : son bloc
   `api.fiche.renouvellement {rang_segment, renouv_score}` est gelé — badge perdu = FAIL ;
2. les **31 autres parcelles riches** gèlent `renouvellement: null` — badge fantôme sur une
   écartée hors segment = FAIL (ex. 97424000AD0409) ;
3. `meta.tiers_effectifs` gèle les **5 effectifs servis STRICTS** — toute dérive = FAIL
   (prouvé : dérive simulée « chaude 1 030 » → FAIL détecté).

⚠ **Piège documenté** : ne JAMAIS régénérer la référence golden par `--dump` seul — en mode
dump le script ne lit pas la référence et **perd les 84 ancres J3** (constaté). La référence a
été patchée **chirurgicalement** (diff = uniquement les champs nouveaux) ; note gravée dans
`meta.m_renouv`.

### Notifications — NON branchées (exigence)

Constat : zéro référence au segment dans `alertes.py` / `radar.py` / `emails.py`. Le segment
n'émet **aucune** notification. *Comment on le brancherait* (mandat futur, non codé) : un
détecteur d'ENTRÉES au recalcul (diff `parcel_renouvellement` avant/après sur `idu`), throttlé
par commune, qui alimenterait le digest hebdomadaire existant (jamais une alerte temps réel :
le segment bouge avec les runs, pas avec le marché) — wording « nouvelles parcelles au
segment Renouvellement », jamais « nouvelles opportunités ».

---

## Reportés (hors mandat, consignés)

- **Modèle P dédié au renouvellement** (walk-forward + arène + gel) — l'heuristique actuelle
  classe, elle ne prédit pas. Le label d'un tel modèle reste à définir (mutation ? dépôt de
  PC ? division effective ?) — non trivial.
- **Notifications** (ci-dessus). — **Tuiles MVT** : la couche carte est du geojson top-rangs ;
  l'embarquer dans `mvt_parcels` (colonne renouv) serait un `build-mvt` de plus, non requis.
- **Le tri renouv_score dans la liste principale** : refusé par doctrine, assumé.

## Incidents de session (transparence)

Deux collisions avec une session M22 concurrente **dans le même clone** :
1. au démarrage : HEAD sur un WIP M22 non commité → stash étiqueté (récupéré depuis par la
   session M22), branche A rebasée sur main ; le tag `avant-renouv` préexistait (1d20896,
   contient main — filet valable) ;
2. en plein lot B : la session M22 a **commité sur ma branche B puis l'a déplacée** (tip
   6385cbc) → mes 15 fichiers étaient non commités sur sa lignée. Réparé : stash → reset de ma
   branche sur la base A (les commits M22 restent sur `feat/m22-d-potentiel`, rien de perdu)
   → pop propre (bases identiques vérifiées) → push immédiat.
   **Recommandation : ne plus lancer deux mandats simultanés dans le même clone** (worktrees).

## Récapitulatif des garanties

- Cascade, étage 0, modèle P, tiers servis, `parcel_p_score_v2` : **intouchés** (testé +
  golden (3) + diff tiers au bit près, à chaque lot).
- « Opportunité » : introuvable dans le segment (testé unitairement + vérifié dans le PDF).
- Chiffres clés : **68 445** parcelles, entonnoir 195 209 → 182 330 → 73 078 → 71 313 → 68 445 ;
  top île à Entre-Deux/Bras-Panon (diffus) et Le Port (îlots) ; masse à Le Tampon/Saint-Paul/
  Saint-Denis.
- LOT D (vérification sur main mergée) : **en attente du merge Vic** A→B→C.
