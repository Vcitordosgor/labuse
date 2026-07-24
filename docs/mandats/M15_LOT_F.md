# M15 — LOT F : renommages et explications

**Branche** : `fix/m15-f-noms` · Build 0 erreur · Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuve `qa/m15/F/f1_outils_renommes.png`.

Affichage seulement — les **clés techniques** (`key: 'scoring-v2'`, `o9-rarete`, `o10-bascules`, `simulplu`, `o7-carnet`, `duediligence`, `num` M-codes) sont **inchangées** (URL/logs/QA préservés).

## F1 — Renommages (nom retenu · alternatives consignées)
| Outil | Avant | **Retenu** | Alternatives écartées |
|---|---|---|---|
| 1 | Scoring (P) | **Radar des mutations** | « Parcelles à surveiller », « Priorité de prospection » |
| 7 | Pipeline rareté | **Rareté du foncier** | « Épuisement du foncier », « Tension foncière » |
| 8 | Bascules datées | **Quoi de neuf** | « Changements récents », « Journal des mouvements » |
| 17 | Simulateur PLU | **Changement PLU** (piste Vic) | « Et si le PLU changeait ? », « Simuler un reclassement » |
| 20 | Carnet de secteur | **Suivi de secteur** | « Portefeuille de secteur », « Tableau de bord secteur » |
| 21 | Due diligence | **Contrôle avant achat** | « Audit de parcelle », « Vérification avant achat » |

**« v2 » retiré** : plus aucun libellé de verdict ne porte « v2 » (déjà fait M14-F1 ; vérifié : seule la clé technique `scoring-v2` le garde, jamais affichée).

## F2 — Explications améliorées (descriptions client, sans jargon)
- **5 Scan patrimoine** (ton plus vendeur) : « Un nom de propriétaire, et TOUT son foncier ressort d'un coup — repérez les gros détenteurs à approcher. »
- **6 Mode bailleur** (Vic ne comprenait pas — jargon LLS/QPV retiré) : « Repérez le foncier taillé pour le logement social — quartiers prioritaires, TVA réduite, leviers du bailleur. » (Ce que fait l'outil : liste les parcelles propices au logement social ; sa bannière interne est servie par le back `lecture_lls`.)
- **7 Rareté du foncier** (clarifié) : « Où le foncier se raréfie : combien de constructible reste-t-il par commune, et pour combien de temps (horizon ZAN). »
- **20 Suivi de secteur** : description conservée (déjà claire).

## Notes pour lots suivants
- **RG1** : l'outil « Mode bailleur » (M06) lit `commune` depuis le store → hérite du filtre carte. **À couper en LOT G (RG1).**
- Les **bandeaux internes complets** (RG2) des 22 outils = pass dédiée (croise LOT E). Ce lot a traité les **noms** + les **descriptions de liste** des outils nommés par le mandat.
