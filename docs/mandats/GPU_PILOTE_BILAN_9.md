# GPU-PILOTE — BILAN DES 9 COMMUNES À JOUR

> Les 9 communes dont l'archive locale est présente ET à jour (garde-fou sha **9/9 concordant**).
> Extractions : `config/calibrage/extraction_paquet{A,B,C}.yaml`. L'Étang-Salé (pilote) à part.
> **Rien écrit en base, aucun YAML existant modifié, aucun re-scoring.** Les 14 autres attendent tes
> retéléchargements. Ceci N'EST PAS le diff final (qui exige les 24) — c'est la consolidation des 9.

## Tableau consolidé

| INSEE | commune | ouverture AU | plancher densité | OAP densité/social | VRD opérateur | name=desc | sha |
|---|---|---|---|---|---|---|---|
| 97401 | Les Avirons | conditionnelle (modif) | — | — | non extrait | non | ✓ |
| 97402 | Bras-Panon | **conditionnelle_etat_tiers** (1AU) | — | social 50% | non extrait | **oui** | ✓ |
| 97403 | Entre-Deux | conditionnelle (modif/révision) | — | — | non extrait | **oui** | ✓ |
| 97406 | La Plaine-des-Palmistes | conditionnelle (modif) | **10 LLS/opération** | a_verifier (OAP graphique) | non extrait | non | ✓ |
| 97415 | Saint-Paul | conditionnelle (modif) | — | a_verifier (OAP 413 p) | non extrait | non | ✓ |
| 97416 | Saint-Pierre | conditionnelle (modif/révision) | via OAP | **50/60/80 log/ha · 20-40%** | non extrait | **oui** | ✓ |
| 97419 | Sainte-Rose | **conditionnelle_etat_tiers** (1AU, hors 1AUc) | — | — | non extrait | non | ✓ |
| 97423 | Les Trois-Bassins | **conditionnelle_etat_tiers** (2AU→1AU) | **35/30/20 log/ha** | social 25/40% | non extrait | non | ✓ |
| 97424 | Cilaos | conditionnelle (AUst réserve) | — | — | non extrait | non | ✓ |
| — | *(rappel) L'Étang-Salé* | *conditionnelle_operation + AUs fermée* | *50/30/15 + planchers* | *par site (OAP)* | *interne+externe* | *non* | *✓* |

## Les faits nouveaux que les YAML actuels ne portaient pas (le cœur)

1. **Statut d'ouverture AU — sur les 9/9.** Aucune AU n'est « ouverte » sans condition : toutes
   subordonnées à une modification/révision, ou à un phasage. C'est le gisement transverse (dette #7
   à l'échelle) : le zonage seul disait « AU constructible », le règlement dit « pas encore ».
2. **Dépendance de phasage inter-zones — 3 communes** (Bras-Panon, Sainte-Rose, Les Trois-Bassins) :
   une AU ne s'ouvre qu'après aménagement d'une autre (2AU→1AU). Le champ `dependance` du schéma le
   porte ; aucun YAML actuel ne modélise de dépendance inter-zones. Cas fin : Sainte-Rose exclut
   nommément 1AUc.
3. **Planchers de densité — 4 communes, valeurs PROPRES** : L'Étang-Salé 50/30/15, Les Trois-Bassins
   35/30/20 (règlement), Saint-Pierre 50/60/80 (OAP), La Plaine 10 LLS/opération. **Ni universels, ni
   propres à L'Étang-Salé.** Une parcelle sous le seuil = inconstructible seule, fait absent des YAML.
4. **Prévalence OAP** : la densité/social réels viennent de l'OAP par site (Saint-Pierre le plus
   riche). Le règlement renvoie explicitement à l'OAP.
5. **Charges VRD opérateur** : trouvées seulement à L'Étang-Salé pour l'instant (chapitre « réseaux »
   des 9 non lu en détail — `non_extrait`, pas `sans_objet` : à confirmer, ne pas conclure à l'absence).

## Ce que le schéma a encaissé (aucun arrêt)
`conditionnelle_operation`, `conditionnelle_etat_tiers` (+ `dependance`), `fermee` (AUs/AUst),
planchers au règlement OU via OAP, prévalence règlement/OAP, `name`=description (garde-fou 21077 sur
Bras-Panon/Entre-Deux/Saint-Pierre). **Aucun cas non descriptible sur les 9.** Le schéma tient.

## Points ouverts (hors extraction, te reviennent)
- **Bloquant opposabilité** : Saint-André (413 têtes/7 brûlantes) + Saint-Leu (348/9) — **761 têtes /
  16 brûlantes sur le REPLI GÉNÉRIQUE** (mesuré : `_calibrated_yaml`=None, `calibree=False` sur
  100%). Zonage réel via AGORAH (idurba 2019 St-André / **2007** St-Leu), mais RÈGLES devinées. GPU a
  perdu la trace. → tes appels mairie (opposabilité) + décision calibrer/geler.
- **14 archives** à (re)télécharger — cf. `GPU_PILOTE_PAQUETS_ETAT.md`.
- **VRD des 9** : à extraire (chapitre réseaux) si tu veux le poste de coût, avant le diff final.

## Familles de trame (cabinet rédacteur) — nouveau champ de vérification
Ajout au schéma (arbitrage Vic) : `cabinet_redacteur`. Si les 24 se regroupent en quelques familles,
une anomalie dans l'une se cherche dans les autres. Détection = signature texte du règlement.

| famille | communes | preuve |
|---|---|---|
| **DUTEILH-PERRAU URBANISME ET ENVIRONNEMENT** | **L'Étang-Salé (97404) · Saint-Leu (97413)** | signature texte + **verbatim AUs identique** + trame partagée : planchers 10 log + densité log/ha, VRD internes/externes, prévalence OAP |
| non détecté au texte | 97401, 97402, 97403, 97406, 97415, 97416, 97419, 97423, 97424 | cabinet en logo/page de garde (image) — pas extractible du texte ; à confirmer visuellement |

**Implication** : la famille DUTEILH-PERRAU partage une STRUCTURE (numérotation d'articles, planchers,
VRD). Vérifier une valeur sur L'Étang-Salé, c'est aussi la vérifier sur Saint-Leu — et un défaut de
calibration sur l'une doit être cherché sur l'autre. À mesure que les 14 arrivent, je note le cabinet
de chacune ; les faux positifs de sous-chaîne (« ITEC », « OTE » apparaissent dans tous les docs) sont
écartés — seule la signature « X URBANISME ET ENVIRONNEMENT » ou un nom de cabinet explicite compte.

## Suite
Prêt à reprendre en paquets de 4 dès que les 14 archives sont là. Le **diff final consolidé**
(YAML vs extraction vs parcelles touchées) se fera sur les 24, pas avant. Ping **par paquet de 4**.
