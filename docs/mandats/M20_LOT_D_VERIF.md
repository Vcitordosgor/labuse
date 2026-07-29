# M20 — LOT D : vérification sur `main` mergée

Après merge Vic **A → B → C** (`9cea898 · f0f1ea1 · a677ef0`, tip `a677ef0`). Reboot de main, recapture **sur main**.
Merge propre (0 marqueur de conflit), `tsc + vite build` 0 erreur. **Non poussé.**

## Golden
`Bilan: 116/116 PASS, 0 FAIL` (`LABUSE_DEV_MODE=1`, API :8000).

## Checklist du mandat

| Point | État | Preuve |
|---|:---:|---|
| Tuile **Courrier** présente et fonctionnelle, module ouvert avec parcelle pré-remplie | ✅ | `qa/m20/d/D_courrier_PM.png` — idu `97418000AT2317` pré-rempli |
| **Aucune identité de personne physique** (cas PP testé explicitement) | ✅ | `qa/m20/d/D_courrier_PP.png` — idu `97418000AT2374` pré-rempli, bannière SPF/CERFA, **aucun nom** (test auto : « aucun nom exposé » = vrai) |
| **7 tuiles** visibles, libellés entiers, aucune troncature, aucun scroll horizontal | ✅ | `qa/m20/d/D_barre_7tuiles.png` — `PDF · Dossier · Finance · 1950 · Cadastre · Maps · Courrier` |
| **Dossier** contient les sections enrichies (contexte commune + solaire) | ✅ | `qa/m20/d/D_dossier_section07.png` (+ `dossier_AT2317_main.pdf`) — 9 marqueurs présents (Contexte commune, permis accordés, SRU, QPV, ENAF, Gisement solaire, gradient côtier, millésime, Généré via LABUSE) |
| **Non-régression fiche M19** : verdict, tiroirs, micro-preuves, carte accentuée, IA, Pipeline, Projet | ✅ | `qa/m20/d/D_fiche_M19.png` |
| **Golden 116/116** | ✅ | ci-dessus |

### Détail non-régression M19 (mesuré sur `97418000AT2317`)
- **Carte VERDICT** encadrée présente (`data-verdict-card`), verdict « Brûlante ».
- **8 tiroirs** : regles · risques · proprio · marche · faisabilite · viabilisation · confiance · pourquoi.
- **Carte accentuée violette** = Propriétaire : `border-color = rgb(68,53,99)` (#443563) confirmé.
- **Micro-preuves** intactes : Règles « 126 m² SDP » + jauge ; Risques « 1 vigilance » + segments « 10 couches » ;
  Marché « 498 €/m² » + sparkline ; Faisabilité « R+2 · SDP 126 m² · calcul tracé ».
- **IA** (« Une question sur cette parcelle ? »), **+ Pipeline**, **+ Projet** présents. **0 erreur console.**

## Verdict LOT D
Merge propre, golden 116/116, tous les points du mandat vérifiés sur main, non-régression M19 complète.
**M20 clos côté CC.** Réserve reportée (non bloquante) : la porte de quota Dossier reste un stub « toujours vrai »
(activation = décision Vic, cf. `M20_C_PARITE_DOSSIER.md` C3).
