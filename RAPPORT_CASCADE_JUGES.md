# Cascade de juges piscines (Lot 8 révisé) — rapport final · 11/07/2026

**Juge retenu : `FLAIR-INC ≥ 0,30 ET probe ≥ 0,50` — précision 90,7 % @ rappel 74,5 %**,
mesuré sur les 300 verdicts sanctuarisés. Critère produit Vic (« ≥ 90 % même si le
recall tombe ») ATTEINT. 100 % local, 0 €/run, licence Etalab 2.0 (attribution IGN).

## Protocole (discipline sanctuaire)

- **Étage 0** : 300/1 393 verdicts sanctuarisés (stratifiés confiance × commune,
  119 strates, seed fixe) — jamais utilisés pour entraîner ni régler ; 1 093 en
  train/calibration. Badge « fiabilité V0 » + exports commerciaux suspendus (423).
- Tout choix de seuil/règle fait sur TRAIN (probas croisées 5-fold pour la probe) ;
  chaque mesure sanctuaire déclarée avant tir.

## Chemin des mesures (sanctuaire, dans l'ordre)

| Juge | Précision | Rappel des vrais | Verdict |
|---|---|---|---|
| V0 colorimétrique (profil strict, réf.) | 79,3 %* | — | matérialisée provisoirement |
| Étage 1 — probe DINOv2+logreg (meilleur point) | 85,4 % | 74,5 % | ✗ |
| Étage 2 — VLM Haiku 4,5 seul | 64,8 % | 87,9 % | ✗ (confiance non informative) |
| Étage 2 — veto probe≥0,5 ET Haiku | 83,0 % | 74,5 % | ✗ (train 99/89 = surajusté) |
| Étage 2bis — variante Sonnet (pré-déclarée) | — | — | bloquée : crédits API épuisés |
| Étage 3 — FLAIR-INC seul (seuil 0,3) | 81,4 % | 89,2 % | ✗ |
| **Étage 3 — FLAIR ≥ 0,3 ET probe ≥ 0,5** | **90,7 %** | **74,5 %** | **✓ RETENU** |

\* mesuré sur les 966 verdicts de la session initiale (460 dans le profil).

## Pourquoi FLAIR a marché

Modèle IGN `FLAIR-INC_rgb_15cl_resnet34-unet` (HuggingFace IGNF, **Etalab 2.0** =
usage commercial OK) : segmentation entraînée sur l'ortho aérienne française à 20 cm
avec une classe NATIVE « swimming pool » — notre distribution d'entrée exacte, en
inférence pure (aucun fine-tune). Piège résolu : normalisation ImageNet requise
(vérifiée sur piscines connues : fraction pixels piscine 0,5-0,8 vs 0,0 en /255).
Combiné à la probe (juge indépendant, axe texture/contexte), les erreurs des deux
se recouvrent peu → l'intersection franchit les 90 %.

## Re-score et re-matérialisation (faits)

- probe_score persistée sur les 19 899 candidats ; juge_flair calculé partout où la
  règle peut jouer (probe ≥ 0,35 : 11 306 scorées, le reste = auto-reject probe).
- Auto-acceptées par le juge : 7 697 + verdicts humains 'ok' →
  **parcel_equipements : 8 307 parcelles piscine** (vs 9 757 en V0 — plus propre).
- Presets convergés recomptés : piscinistes-construction 5 542 · parc-piscines 495.
- Gradient conforme : La Possession 6,2 %, Étang-Salé 6,0 %, Saint-Paul 4,9 % …
- Rappel documenté au seuil retenu : ~74,5 % des vrais candidats V0 (le recall
  AMONT de la V0 — piscines sombres/couvertes non candidates — s'y ajoute ;
  estimation globale ≈ 55-65 % des piscines bleues visibles).

## Ce qui t'attend (2 sessions courtes, outil à quota)

1. **Bande d'incertitude — 298 vignettes** : `/ortho/validation?profil=bande`
   (flair 0,26-0,30 × probe ≥ 0,5 ∪ flair ≥ 0,3 × probe 0,48-0,50). Tes verdicts
   basculent ces cas limites en vérité humaine (matérialisation les respecte déjà).
2. **Certification officielle — 100 vignettes fraîches** :
   `/ortho/validation?profil=juge&quota=100` (tirées AU-DESSUS du juge, jamais vues).
   → LE chiffre contractuel de précision. S'il confirme ≥ 90 % : je rouvre les
   exports (suspension config `exports_suspendus`) et retire le badge V0.

## Transposition PV (Lot 4) — documenté comme demandé

23 529 candidats PV en base (10 056 CES probables ; 153 parkings APER `equipe=TRUE`).
Le juge VLM se transposait tel quel mais Haiku a déçu sur les piscines ET les crédits
API sont épuisés. **Reco PV** : (1) ta validation 150 (`?type=pv`) mesure la V0 ;
(2) si insuffisant, MÊME recette que les piscines : FLAIR n'a pas de classe PV, mais
probe DINOv2 + tes 150 labels PV = étage 1 PV (local, ~20 min) ; les annotations CES
sont déjà séparées. Pas de dépendance API.

## Reste ouvert

- Crédits API Anthropic épuisés — seule conséquence : variante Sonnet abandonnée
  (plus nécessaire) ; le copilote IA de l'app est aussi concerné (stub tant que
  non rechargé).
- Job pente non bâtie : 259 051/423 452, checkpointé, se termine seul.
- Purge du cache tuiles (5,6 Go) : APRÈS ta certification (les vignettes en dépendent).
