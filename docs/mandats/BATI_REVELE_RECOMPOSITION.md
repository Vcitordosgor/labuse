# RÈGLE « BÂTIE RÉVÉLÉE » — MESURE DE RECOMPOSITION — POINT D'ARRÊT (point 3)

> Chemin A implémenté (règle + cache + câblage, commit 0318a4b). Mesure à blanc
> q_v11_regle_apres : features max ON + règle ON + pondération ON, étage 0 et hystérésis =
> servi, 616 s, features RESTAURÉES vérifiées. **Le servi est intact — rien ne bascule.**

## La règle (périmètre peuplé)
`parcel_bati_revele` : **9 044 en règle** (couche < 20 ET max ≥ 40) · **7 098 en bande
d'adjudication** (20-40, JAMAIS auto-déclassées, restent servies). Motif servi par parcelle :
« bâti détecté CoSIA (PVA juil.-août 2025), N m². SDP affichée = terrain nu théorique
(recalcul de la chaîne résiduel au train 5). »

## Résultats de la mesure — la règle fait EXACTEMENT ce qui a été arbitré
| attendu (arbitrage) | mesuré |
|---|---|
| Les 285 franches sortent par la règle | **285/285 → declasse_bati_revele** (33 brûlantes + 252 chaudes) |
| Bande 20-40 jamais auto-déclassée | ✓ les 56 têtes 20-40 restent servies (2+50 en tête, 4 glissements) |
| 17 exceptions remplacées quand couvertes | **17/17 atterrissent naturellement en declasse_bati_revele** (CH1893 incluse — CoSIA 139 m²) : zéro résiduelle |
| Écartées inchangées | ✓ étage 0 prime (4 433 restent écartées) |
| A/B/AU priment sur la règle | ✓ (~600 restent sous leur déclassement spécifique) |

## Effectifs recomposés (q_v11)
**118 brûlantes · 1 043 chaudes** (recalibrage N_e stable ~1 150 tête) ·
**declasse_bati_revele : 4 010 servies avec motif** (3 616 ex-a_creuser, 252 ex-chaudes,
33 ex-brûlantes, 92 ex-réserve, 17 ex-exceptions) · a_creuser 59 495 · reste inchangé.

## Les ENTRANTES par recomposition : 311 (revue visuelle OBLIGATOIRE)
300 a_creuser→chaude + 11 a_creuser→brûlante. Contrôle de propreté : **310/311 sont hors de
toute population révélée** (aucune discordance bâti CoSIA-vs-couche) ; **1 chaude est en bande
20-40** (signalée au deck). Deck daté : `qa/cosia/cartes_entrantes_recomposition.pdf`.

## Ce qui restera à faire À LA BASCULE (point 4, après ton arbitrage)
1. Bascule 6 gardes (remplacement sous label, comme la pondération) — le run servi recalculé
   règle ON ≡ q_v11 (conformité stricte vérifiée par le script, échec bruyant sinon).
2. Exceptions : plus AUCUN override à ré-appliquer (la règle couvre les 17) — le journal
   q_v8_calibre actuel suit l'archive ; motif « remplacée par la règle » consigné.
3. MVT + golden régénérés dans le même geste (gardes #6).
4. Adjudication de la bande 20-40 en tête (56 cartes) — après bascule, à ta main.
5. Fiche : le tier declasse_bati_revele et son motif (avec la phrase SDP) sont servis par les
   mécanismes existants des déclassés ; vérification visuelle au geste de bascule.

**Rien ne bascule sans ton arbitrage sur ces chiffres + le deck des 311.**
