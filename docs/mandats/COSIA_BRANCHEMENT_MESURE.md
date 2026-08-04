# BRANCHEMENT CoSIA — MESURE À BLANC DU RE-SCORE — POINT D'ARRÊT (étape 3)

> Séquence Vic respectée : chargement + mesure d'emprise (1), re-score à blanc + cartes (2),
> **arrêt sur les chiffres (3)** — la bascule (4, avec les 6 gardes) attend l'arbitrage.
> Le servi q_v8_calibre est INTACT ; les features partagées ont été RESTAURÉES et vérifiées
> (signature ≡ backup) en fin de mesure. Durée totale : 620 s.

## Étape 1 — mesure d'emprise (max BD TOPO/CoSIA vs BD TOPO seule)
16 142 parcelles servies franchissent le seuil des 20 m² : 39 brûlantes, 307 chaudes,
184 réserve, 5 398 a_creuser, 9 122 écartées, ~1 090 déclassées. Delta moyen ~100 m² en tête.

## Étape 2 — re-score à blanc (q_v10_cosia_apres : features max-emprise, étage 0 et
hystérésis = servi, pondération ON)

### LE SORT DES ~290 (la question du mandat) : **le re-score n'en sort que 60 sur 346 (17 %)**
| révélées bâties (>20 m² CoSIA, couche vide) | restent en tête | sortent (a_creuser) |
|---|---:|---:|
| 39 brûlantes | 34 (18 brûlante + 16 chaude) | 5 |
| 307 chaudes | 252 | 55 |
| **346** | **286 (83 %)** | **60 (17 %)** |

**La dette #4 ne se referme PAS par cette bascule.** Trois causes structurelles :
1. L'emprise n'entre au scoring que comme FEATURE de contexte (densité bâtie de secteur,
   caractère nu/bâti) — un signal, pas une règle : le p brut des têtes domine.
2. Le PLANCHER C repose sur la SDP résiduelle (`parcel_residuel`) qui n'est PAS recalculée
   par ce re-score — une bâtie révélée garde la SDP calculée quand on la croyait nue.
3. Il n'existe AUCUNE règle « parcelle bâtie → hors tête » : c'est le « filtre client bâti »
   (dette #4, train 5) — jamais implémenté. La mesure vient d'en faire la preuve chiffrée.

### Effet de bord mesuré — les 17 exceptions reviennent
Un re-score recalcule naturellement les tiers : les 17 exceptions manuelles (overrides
post-scoring) REVIENNENT (8 en brûlante, 9 en chaude) dans q_v10. Toute bascule par re-score
doit les RE-APPLIQUER dans le même geste — ou les remplacer par la règle ci-dessous.

### Mouvements complets (à blanc)
348 mouvements : 65 sorties de tête, 159 entrées mécaniques (rangs libérés + features de
secteur), 19 brûlante→chaude, recalibrages réserve. Effectifs finaux si bascule TELLE QUELLE :
93 brûlantes / 1 142 chaudes. Cartes datées des mouvements en tête :
`qa/cosia/cartes_mouvements_cosia.html`.

## Étape 3 — POINT D'ARRÊT : deux chemins pour refermer la dette, à ton arbitrage
| chemin | principe | effet sur les 346 | coût | risque |
|---|---|---|---|---|
| **A. Règle de déclassement « bâtie révélée »** | max-emprise ≥ seuil → tier déclassé dédié (type declasse B, motif servi « bâti détecté CoSIA {date}, {m²} »), zone 20-40 en adjudication (61 cartes) | **285 franches sortent d'un coup**, motif traçable par parcelle, réversible | ~½ j + bascule 6 gardes | doctrine à écrire (déclassement vs écartement) ; les 61 limites à arbitrer |
| B. Recalcul de la chaîne résiduel (parcel_residuel avec max-emprise) puis re-score | corrige SDP + plancher C à la racine | partiel (les causes 1+2 traitées, pas la 3 — une bâtie à gros terrain peut rester) | chaîne calibrée v8 à re-passer (heures) + re-score | touche TOUTES les SDP servies (bien au-delà de la dette #4) |

**Reco : chemin A** — c'est l'esprit de tes retraits (16 déjà journalisés un à un : la règle
les généralise et remplace les exceptions par un motif systématique, daté, sourcé). Le chemin B
reste juste À TERME (SDP honnêtes) mais est un chantier scoring (train 5), pas la fermeture de
la dette #4. Les deux se combinent : A maintenant, B au train 5.

**Rien ne bascule sans ton arbitrage.**
