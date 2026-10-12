# Suite 1 — règles PLU AU MOTEUR + run q_v19 (delta)

## Application au moteur (plu_exceptions_effet.json + db.py + zonage.py)
- D-49 Sainte-Rose Ua/1AUa ≥2500 m² : majoration he_m 9→11, hf_m 12→14 (majoration_surface, decision=applique, modifie_calcul:true). APPLIQUÉE au moteur (vérifié : he_m 11 sur AL0376).
- D-48 Saint-Joseph U2 gradation : decision=non_modelisee (moteur à hauteur UNIQUE ne peut pas band-er par profondeur) — PORTÉE sur la fiche (« règle non modélisée »), le moteur garde le palier >12 m (13/11, = le headline affiché).
- D-50 recul H/2 : NON couplé mécaniquement. Mesuré : inseter H/2 sur TOUTES les limites effondre la SDP (BW2262 503→131, AL1115 313→exigu, AV1095 376→55, −74 à −100 %) car la mitoyenneté par limite est inconnue. → PORTÉE « non modélisée » (capacité = recul plancher 3 m, borne haute).
- D-52 stationnement : hors-SDP (aucun effet).

## Run q_v19 (run_seq 16 = copie run 15 + delta 1545) — comparaison à q_v18 (run 15)
  parcelles dont la SDP change    : 0
  parcelles dont la cause change  : 0
  parcelles dont la métadonnée non-modélisée change : 412
  → le SCORE ne lit que sdp/cause/taux/capacité (pas regles_non_modelisees) → q_v19 score ≡ q_v18, 0 parcelle change de bande/signal.
  5 exemples (métadonnée ajoutée, SDP INCHANGÉE) :
    97412000BO0219 — SDP 13029 m² (identique à q_v18, + note « règle non modélisée »)
    97412000BO0528 — SDP 2939 m² (identique à q_v18, + note « règle non modélisée »)
    97412000BO0085 — SDP 466 m² (identique à q_v18, + note « règle non modélisée »)
    97412000BO0086 — SDP 682 m² (identique à q_v18, + note « règle non modélisée »)
    97412000BO0082 — SDP 226 m² (identique à q_v18, + note « règle non modélisée »)

## Verdict : AUCUNE parcelle ne change de SDP/cause/score. Le seul delta est la MÉTADONNÉE de
transparence (412 parcelles portent les notes « gradation / recul H/2 non modélisée »). Run 16
non servi, manifeste toujours sur run 15. RIEN n'est servi ni basculé.
