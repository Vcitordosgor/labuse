# SDP-UNIQUE-1 — captures AVANT / APRÈS de la fiche (AB0785, IE0241)

Captures du **payload servi à la fiche** (`GET /parcels/{idu}`), source directe de ce que le client
lit : la tuile d'en-tête rend `potentiel_transformation.sdp_residuelle_m2` ; le verdict rend
`analyse_labuse.sdp_residuelle_m2`. JSON bruts dans ce dossier (`*-AVANT.json`, `*-APRES.json`),
reproduits par restart du serveur sur chaque run (cache L1 mémoire vidé).

> Rendu visuel non capturé : le SPA local est derrière authentification et son build statique n'est
> pas servi sur ce poste ; la valeur affichée est une fonction 1:1 de ces champs (tuile = en-tête,
> carte verdict = verdict). La preuve de cohérence écran/outils/PDF est la recette
> (`recette-sdp-coherence.txt`, 11 témoins servables OK).

## 97411000AB0785 (multi-bâti, 11 bâtiments)

| | en-tête (tuile « SDP restante ») | verdict LABUSE | lecture |
|---|---:|---:|---|
| **AVANT** (Mac sert le run 1 legacy) | **850 m²** « potentiel modéré » | **0** « aucune SDP » | **CONTRADICTION** (constat A-001 / NU-E-001) |
| **APRÈS** (run 17 q_v20 servi) | **0** « densité atteinte » | **0** | **COHÉRENT** |

## 97411000IE0241 (maison, parcelle de référence)

| | en-tête (tuile « SDP restante ») | verdict LABUSE | lecture |
|---|---:|---:|---|
| **AVANT** (run 1 legacy) | **0** « densité atteinte » | **92** | **CONTRADICTION** (sens inverse) |
| **APRÈS** (run 17 q_v20) | **92 m²** « potentiel modéré, bâti conservé » | **92** | **COHÉRENT** |

La contradiction venait du socle Mac servant le run résiduel legacy 1 (parcel_residuel) face au
score_labuse déjà en q_v20 — un **artefact de run**, pas un défaut de calcul. L'étape 0 (servir le
run 17 comme la prod) la ferme ; les corrections + le test de cohérence la verrouillent pour la suite.
