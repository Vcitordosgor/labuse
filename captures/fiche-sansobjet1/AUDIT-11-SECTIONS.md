# FICHE-SANS-OBJET-1 — audit des 11 sections : lignes évaluées jetées sans repli « sans objet »

Question par section : y a-t-il des lignes ÉVALUÉES (cascade `f.lines`, avec un `result`) puis
JETÉES avant affichage, sans repli « sans objet » pour les récupérer ?

5 onglets d'évaluation seulement : `regles`→§4 · `risques`→§5 · `marche`→§8 · `proprio`→§1 ·
`reseaux`(layer `acces`)→§6. Les 6 autres sections n'affichent que des MESURES/faits typés (pas de
vérifications à `result`) → rien à replier, dit explicitement.

| # | Section | Évalue des lignes ? | Jetées sans repli AVANT ? | Combien | Traitement |
|---|---------|--------------------|---------------------------|---------|------------|
| 1 | Identité | oui — proprio (BODACC, dirigeant, PM) | **OUI** pour une personne physique (Lot 4 les retirait du flux, en silence) | 3 (PP) | **REPLI AJOUTÉ** (ce mandat). PM : les résidus « inconnu » masqués sont des CONTRADICTIONS (RETOURS-11F F11), pas des « sans objet » → jamais surfacés |
| 2 | Terrain | non — mesures (pente, exposition, azimut, surface libre, OCS GE, piscine) | — | 0 | Rien à replier (mesures) |
| 3 | Bâti | non — mesures (emprise, hauteur, DPE, toit, RNB, BAN PLUS) | — | 0 | Rien à replier (mesures) |
| 4 | Urbanisme | oui — `regles` | **OUI — angle mort** (§4 ne montrait que les non-PASS, aucun repli ne ramassait les PASS) | ~12 (16 PASS − `bati`/`dpu`/`peb` re-servis) | **REPLI AJOUTÉ** (cœur du mandat) |
| 5 | Risques et environnement | oui — `risques` | non (repli déjà présent) | 15 foldés | Repli existant — **le modèle** |
| 6 | Réseaux et desserte | oui — `acces` | non — **affichée inline** (jamais jetée) | 1 | Affichée telle quelle dans « Accès » |
| 7 | Fiscalité et dispositifs | non — dispositifs à absences typées | non | 0 ligne évaluée | DPU/PEB « Hors… » en note inline (DispositifsBody) ; sinon mesures |
| 8 | Marché | oui — `marche` | non — **affichées inline** (jamais jetées) | 2 (`potentiel_foncier_region`, `zone_activite`) | Affichées telles quelles ; `amenites`/`sitadel` relocalisées §9 (pas jetées) |
| 9 | Quartier | non — mesures (équipements, IRIS, permis à proximité, dépôts) | — | 0 | Rien à replier (mesures) |
| 10 | Potentiel | non — mesures/calcul (SDP, transformation, capacité, calcul tracé) | — | 0 | Rien à replier (mesures) |
| 11 | Simulation | non — calcul (bilan/charge foncière, Mode B, portes) | — | 0 | Rien à replier (calcul) |

## Bilan
- **1 angle mort** (§4 Urbanisme) → repli ajouté (cœur du mandat).
- **1 rejet délibéré** (§1 Identité, personne physique, Lot 4) → repli ajouté aussi, pour que
  RIEN ne soit jeté en silence (le flux principal reste nettoyé ; les lignes reviennent repliées).
- **§5** avait déjà le repli (le modèle copié).
- **§6, §8** montrent leurs lignes « sans objet » INLINE (jamais jetées) → pas le même trou ;
  laissées telles quelles (les folder serait de la cohérence de grammaire, hors de ce mandat).
- **§2, §3, §7, §9, §10, §11** n'affichent que des mesures/faits → rien à replier (dit ici).

Preuve : `captures/fiche-sansobjet1/{constrained,simple}_{1_replie_ferme,2_replie_ouvert}.png`
(§4, 12 et 10 lignes), `identite_PP_sans_objet.png` (§1 PP, 3 lignes), `recherche_foret.png`
(« forêt » trouve désormais « Hors forêt publique »). tsc -b vert · vitest 205/205.
