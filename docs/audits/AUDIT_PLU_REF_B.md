# AUDIT M-PLU-REF-B — Ce que les règlements disent vraiment (Phase 1, mesure)

**Branche `feat/plu-ref-b`. Aucune écriture. Lecture des YAML calibrés SEULEMENT (pas les PDF).
Mesuré le 15/08/2026. STOP arbitrage.**

## Verdict en une phrase
La conclusion de Phase 0 (« 12 communes empruntent Saint-Paul, il faut calibrer ») est **renversée** :
**99 % des emprises au sol sont déjà DOCUMENTÉES** dans les YAML (64 % chiffrées et consommées par le
moteur, 35 % explicitement « non réglementées » avec source d'article). Il n'y a quasi rien à calibrer.
`coef_occupation` (0,45) et `densite` (30) ne sont **pas** des valeurs de Saint-Paul à caler sur un
règlement : ce sont des **hypothèses de MODÉLISATION qui comblent un silence** — le règlement n'en fixe
aucune. Le marquage Phase 1 (« non calibrée au règlement de {commune} ») est donc **faux par excès** : il
avoue une dette imaginaire là où il y a un silence du droit (ou, pire, là où le règlement EST consommé).

## 1 — Emprise au sol (326 zones, 21 communes outillées)
Le moteur LIT `rules.emprise_sol_pct` par zone (engine.py:255-256) : chiffrée → cap `surface × emprise%`
appliqué ; null → enveloppe bornée par reculs + hauteur + pleine terre.

| classe | zones | % | sens |
|---|---|---|---|
| **CHIFFRÉE** (nombre) | **210** | **64 %** | Sourcé — valeur du règlement, CONSOMMÉE par le moteur |
| **NON RÉGLEMENTÉE documentée** (null + src « Sans objet »/« Il n'est pas fixé de règle »/renvoi) | **114** | **35 %** | silence du règlement, DOCUMENTÉ (source d'article) |
| à vérifier (null SANS source) | **2** | **1 %** | seul vrai trou |

**17 communes** ont au moins une emprise chiffrée (déjà consommée) : bras_panon (14), l_etang_sale (12),
le_port (13), petite_ile (13), saint_denis (20), saint_joseph (24), saint_louis (22), saint_pierre (25),
sainte_marie (16), sainte_rose (9), les_avirons (11), les_trois_bassins (9), la_plaine (9), cilaos (7),
la_possession (3), sainte_suzanne (2), entre_deux (1).
**Emprise 100 % non réglementée** (le cas cité par le mandat) : le_tampon (9/9 U), saint_benoit (0 zone),
salazie, saint_paul (35 zones « pas de règle »). **le_tampon et Saint-Paul sont ATYPIQUES, pas la norme.**

→ `emprise_sol_pct` (règlement) est **capté partout** (chiffré ou silence documenté). `coef_occupation`
(0,45) est un facteur de MODÉLISATION appliqué EN PLUS (« on ne bâtit pas 100 % de l'emprise ») — il n'a
aucun équivalent réglementaire. Le marquage qui les confond induit en erreur.

## 2 — Densité (logts/ha)
**AUCUNE commune, AUCUNE zone n'a de densité réglementée.** `densite_logts_ha_par_niveau` (30) est
**partout** un filet de modélisation (ex-COS, « plafond de sécurité »), jamais une règle écrite. Il n'y a
**rien à calibrer** — dire « densité non calibrée au règlement » n'a pas de sens : le règlement ne fixe
pas de densité, la capacité est une conséquence de calcul (reculs, hauteur, pleine terre).

## 3 — Stationnement
Présent **21/21** communes (`stat_logement` par zone + `regles_transverses.stationnement`), avec source
d'article (ex. « Art. Ua12.2 »). MAIS en **ratio TEXTE** (« 1 place / logement », « 0,5 place/chambre »),
**jamais en m²/place chiffré**. Le moteur consomme `place_m2` (25 m² = AIRE par place, modélisation). La
norme réglementaire (places/logement) est **extraite mais d'une autre nature** que `place_m2` (aire) :
on ne peut pas câbler `place_m2` sur la norme sans une extraction chiffrée m²/place → **autre mandat**.

## 4 — Ce que le moteur consomme réellement (après le correctif de chemin M-PLU-REF)
| paramètre | valeur consommée | provenance |
|---|---|---|
| emprise au sol | `rules.emprise_sol_pct` (zone) si chiffrée, sinon reculs+hauteur | **RÈGLEMENT (Sourcé)** ou silence |
| `coef_occupation` | 0,45 | hypothèse de MODÉLISATION (île, `hypotheses_ile.yaml`) — pas de règle |
| densité | `hyp.densite` 30 | filet de MODÉLISATION (ex-COS) — aucune règle nulle part |
| `place_m2` | `hyp.place_m2` 25 (aire) | MODÉLISATION ; la norme places/logt existe en texte mais autre nature |

**Le marquage Phase 1 est commune-uniforme** (clé `constructibilite_source_ref`), il sonne pour TOUTE
commune ≠ Saint-Paul — y compris sur une zone dont l'emprise EST chiffrée et consommée (Saint-Denis :
20 zones chiffrées). Concrètement faux par excès.

## Conséquences proposées (Phase 2, Vic tranche)
1. **Reformuler le marquage, zone-aware et VRAI** (jamais retiré sans remplacement) :
   - zone à emprise **chiffrée** → **Sourcé** (règlement), aucun « générique » ;
   - zone à emprise **non réglementée** → « emprise au sol non réglementée par le PLU de {commune} —
     hypothèse de modélisation (coef d'occupation ~45 %) ; capacité bornée par reculs, hauteur et pleine
     terre » (silence dit, pas une dette) ;
   - densité → « pas de densité réglementaire ; plafond de modélisation (filet ex-COS) » — jamais
     « non calibrée ». Écrit une fois, voyage avec la valeur (comme Phase 1).
2. **Stationnement** : SIGNALÉ — norme extraite (ratio texte, 21/21) mais pas en m²/place ; `place_m2`
   reste une aire de modélisation ; l'extraction chiffrée = autre mandat. Rien à câbler ici sans elle.
3. **Communes à emprise chiffrée (17)** : déjà consommées par le moteur → **rien à calibrer**. Les seules
   « vraies » à-vérifier : **2 zones** (null sans source) — négligeable, à lister pour Vic si voulu.

## Décision demandée à Vic (STOP)
- Autoriser la **reformulation zone-aware** du marquage (§1) : Sourcé si emprise chiffrée, « non
  réglementée — modélisation » sinon ; densité = filet de modélisation. C'est factuel (dit la vérité du
  YAML), pas une calibration.
- Acter que **le stationnement chiffré (m²/place) et les 2 zones à-vérifier** relèvent d'un autre mandat.
