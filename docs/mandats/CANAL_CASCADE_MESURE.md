# CANAL CASCADE — MESURE (lecture seule)

> **Statut : MESURE TERMINÉE — POINT D'ARRÊT. Rien appliqué, `q_v7_defisc` intouché.** Mesuré le
> 29/07/2026, base à jour (SDP recalculées `parcel_residuel_rerun`, YAML courants, 9 399 déclassées).
>
> **RÉSULTAT QUI DE-RISQUE LE RE-RUN : le canal cascade n'a AUCUN effet incrémental sur les tiers P.**
> Sur les tiers, il est entièrement porté par des correctifs déjà mesurés (tête-de-liste + P-features
> de phase 1). Sur les scores de cascade, il déplace le socle de capacité, sens correct et intrinsèque.

---

## 1. Les deux canaux agissent sur des SORTIES DIFFÉRENTES (Vic : séparer, voir la compensation)

| Canal | Mécanique | Sortie touchée | Effet sur les TIERS P |
|---|---|---|---|
| **SDP recalculée → `residuel_socle`** | couche SOFT (`positive`/`soft_flag`, `etage0_ext.py:162-168`) — bonus, JAMAIS hard_exclude | score de cascade (`opportunity_score` / a_score / matrice) | **AUCUN** (soft → ne produit ni `exclue` ni `faux_positif` → ne change pas `ecartee_etage0`) |
| **M6 2b (interdit-avec-hauteur)** | hard_exclude (`phase1.py:277-294`) | `ecartee` → `ecartee_etage0` → tiers | **SUBSUMÉ** (voir §2) |

**Pas de compensation cachée** : les deux canaux ne touchent PAS la même sortie. Le socle bouge le
score de cascade ; M6 2b bouge l'écartement. Sur les tiers P, seul M6 2b pourrait agir — et il est
déjà porté ailleurs. Rien ne se compense en se masquant.

## 2. Canal M6 2b : 412 parcelles, ENTIÈREMENT subsumées par le correctif tête-de-liste

Les 412 parcelles interdit-avec-hauteur (recouvrement ≥ 90 %) encore servies dans `q_v7_defisc`
(le run précédait la calibration) que M6 2b devrait exclure : **412/412 sont DÉJÀ `declasse_zone_
fermee`** dans `parcel_constructibilite` (345 à-creuser, 59 réserve, 8 chaude ; 0 non-déclassée).

→ **Elles sortent bien** (Vic) — via le déclassement tête-de-liste, déjà câblé. Le canal cascade
M6 2b n'ajoute RIEN aux tiers : le verdict moteur (cause `habitat_interdit`, testé avant la hauteur,
`engine.py:157`) capture exactement la même population. **« Un seul correctif, deux mandats »
quantifié : M6 2b ⊆ déclassées.**

## 3. Canal SDP → socle : intrinsèque, sens capacité correct

Sur 263 169 parcelles à résiduel : **54 111 changent de palier de socle** (20,6 %) — 40 810 baisse,
13 301 hausse, delta moyen −10. **Sens vérifié, monotone parfait** : socle_baisse = sdp_baisse
(40 810 = 40 810), socle_hausse = sdp_hausse (13 301 = 13 301). Le socle SUIT la SDP.

- **Intrinsèque, pas relationnel** : le score de cascade est ABSOLU (non rangé) → chaque changement
  de socle vient de la SDP propre de la parcelle. **Zéro mouvement relationnel** dans la cascade
  (contrairement aux tiers P, rang global). Une commune non calibrée ne bouge pas par ricochet ici.
- **Sens capacité** : SDP baisse ⇒ socle baisse — c'est le canal CAPACITÉ (moins de droits à bâtir
  = socle plus bas), OPPOSÉ au canal P (SDP baisse ⇒ P monte, WoE décroissant) et CORRECT pour
  chacun : P prédit la mutation, le socle récompense la capacité. Aucun contre-sens.

## 4. Ce que le re-run complet produira réellement (synthèse des 3 mesures)

L'effet du re-run sur le PRODUIT SERVI est désormais entièrement mesuré, canal par canal :

| Sortie | Canal | Effet | Déjà porté par |
|---|---|---|---|
| **Tiers P** | P-features (SDP) | 2 011 mouvements bidirectionnels, sens WoE | phase 1 re-run |
| **Tiers P** | M6 2b (écartement interdit) | 412 sortent | correctif tête-de-liste |
| **Tiers P** | `residuel_socle` | **aucun** (soft) | — |
| **Score cascade** | `residuel_socle` (SDP) | 54 111 paliers, intrinsèque, sens capacité | le re-run |

**Le re-run n'a plus de surprise de TIER à révéler** : son effet sur les tiers est la somme du canal
P-features (phase 1, 2 011 mouvements) et du déclassement (déjà câblé). Reste le déplacement du socle
de capacité sur le score de cascade — intrinsèque et de sens correct.

---

## Recommandation pour le re-run complet (Vic tranche)
Le re-run reste utile pour **matérialiser** l'état cohérent (recalcul résiduel + cascade re-passée +
champion ré-appliqué) et le faire passer par l'arène + bascule. Mais **son effet est connu et borné**
avant de le lancer — plus de gate de découverte, uniquement une matérialisation à valider en arène.
Ordre restant : **re-run complet → arène → décision de bascule Vic.**

*Artefacts (lecture seule) : `parcel_residuel_rerun`, `repli_pcov`, `parcel_constructibilite`.
Aucune donnée modifiée ; `q_v7_defisc` intouché.*
