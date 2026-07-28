# RAPPORT — Coût variable par taille, PHASE A (mesure). Point d'arrêt.

**Exécuté le 28/07/2026** (branche `mesure/cout-par-taille-phaseA`). **LECTURE SEULE — aucune
application.** Base `origin/main` porteuse du mandat consommateurs (compute_bilan_servi + bassins
démotés), vérifié. Golden **116/116** et tiers **au bit près** (120/1031/3587/72980/353945)
avant ET après. Pas de fichier mandat déposé — exécuté d'après la consigne Vic.

## 0 · Verdict en une phrase

**Le coût variable par taille est le MAUVAIS instrument : il n'y a pas d'économie d'échelle de
construction** (le coût d'équilibre implicite est PLAT hors VRD), et **la courbe apparente est un
artefact VRD/terrain déjà modélisé** — l'appliquer double-compterait le VRD. Le coût audité PLAT
2 550 (conservateur) est le bon. La vraie question de TYPE d'opération relève de la spec
multi-modes, pas d'un coût par taille.

## 1 · Volume par tranche — robuste, pas du bruit (question Vic n°1)

Opérations PC 2015+ (≥ 3 lgt, non-social) dans les **16 communes couvertes**, au prix de sortie
SERVI (`resolve_prix_sortie_servi`). Coût d'équilibre implicite = `2550 + charge_centrale /
(surf_hab × 1,15)` (linéarité du coût dans `compute_bilan`).

| Tranche | n | coût impl. (avec VRD) q1/méd/q3 | coût impl. (SANS VRD) |
|---|---|---|---|
| 3-4 | **733** | 2 361 / 2 595 / 2 726 | **2 891** |
| 5-9 | **336** | 2 611 / 2 737 / 2 867 | **2 891** |
| 10-19 | **189** | 2 720 / 2 777 / 2 976 | **2 891** |
| 20+ | **340** | 2 732 / 2 781 / 2 841 | **2 825** |

Les quatre tranches tiennent sur 189 à 733 opérations — **pas du bruit**. Les médianes sont stables.

## 2 · La vraie question tranchée (question Vic n°2) : ni économie d'échelle, ni type

**a. Hors VRD, le coût implicite est PLAT (~2 891) sur toutes les tranches.** Ce n'est pas une
coïncidence : hors VRD, le coût implicite vaut mathématiquement **`prix × 0,76 / 1,15 = prix ×
0,661`** — purement piloté par le PRIX de sortie, **indépendant de la taille**. (Vérifié : prix
4 375 → 2 891 ; 4 730 → 3 126.) **Il n'y a AUCUNE économie d'échelle de construction.**

**b. La courbe apparente (avec VRD, 2 595 → 2 781) est un artefact VRD/TERRAIN.** Les petites
opérations ont plus de terrain par bâtiment → VRD (€/m² terrain) rapporté au m² habitable plus
élevé → coût de construction implicite d'équilibre plus bas. **Or le VRD est DÉJÀ un poste du
modèle** (terrain-based). Un « coût par taille » calé sur cette courbe **double-compterait le
VRD** — il rehabillerait en coût de construction un effet déjà porté par le poste VRD.

**c. Ce n'est pas non plus une différence de TYPES.** Croisement vendu / tenu (build-to-hold,
revente DVF post-PC) — coûts implicites médians proches (~75 €/m² d'écart) :

| Tranche | n vendu / méd. | n tenu / méd. |
|---|---|---|
| 3-4 | 142 / 2 651 | 591 / 2 577 |
| 5-9 | 70 / 2 795 | 266 / 2 718 |
| 10-19 | 68 / 2 772 | 121 / 2 785 |
| 20+ | 143 / 2 787 | 197 / 2 778 |

Les 3-4 sont bien majoritairement tenues (591/733 = 81 %, patrimonial), MAIS leur coût implicite
(tenu 2 577 vs vendu 2 651) est PROCHE — le type ne crée pas d'écart de coût. Le résidu de courbe
subsiste même chez les vendues, ce qui confirme qu'il est **géométrique (VRD/terrain), pas typologique**.

## 3 · Pourquoi le chiffre du mandat (2 018 → 2 573) a disparu

La courbe « 2 018 (3-4) → 2 573 (10-19) » chiffrée AVANT était un **artefact des prix
pré-correction** : mesurée sur l'ancien instrument (médiane mixte, prix trop bas dans les communes
bon marché), le coût implicite qui annulait la charge à ces prix bas était bas. **Avec l'instrument
corrigé (16 communes, appartements/île), les coûts implicites sont tous ≥ 2 550 et plats hors VRD.**
Le « problème des 3-4 non viables à 2 550 » (86 % ≤ 0 mesuré alors) venait des PRIX, pas du coût,
et il est réglé : les communes bon marché sont désormais « non calculable » (pas servies à un faux
prix), et dans les 16 couvertes les 3-4 sont viables (coût implicite 2 595 > 2 550).

## 4 · Test d'acceptation & tiers (questions Vic n°3-4)

- **Aucun coût par taille n'est proposé** → rien à faire passer au back-test : le coût reste PLAT
  2 550. L'instrument courant (16 communes) tient déjà à ~89-94 % (mesuré aux tours précédents,
  inchangé). Introduire une courbe de coût baisserait artificiellement la charge des grandes
  opérations (coût ↑ avec la taille) sans justification — à l'inverse du besoin.
- **Tiers** : mesure lecture seule, golden 116/116 + tiers au bit près avant/après.

## 5 · Recommandation (point d'arrêt Vic)

- **NE PAS ouvrir d'instrument « coût par taille ».** Il n'y a pas d'économie d'échelle de
  construction (coût plat hors VRD = prix × 0,661) ; l'effet de taille visible est le VRD/terrain,
  déjà modélisé. Le coût audité 2 550 (conservateur) est correct.
- **La question de TYPE reste ouverte, mais ce n'est pas un coût — c'est un MODE.** Les 3-4 lgt
  patrimoniales (81 % tenues) ne relèvent pas du bilan promoteur de marché : elles relèvent du
  **mode patrimonial locatif de la spec multi-modes** (équilibre par rendement locatif + défisc),
  au même titre que le social relève du mode D. C'est là que la distinction se traite, pas dans un
  coefficient de coût.
- **Si un raffinement du VRD est souhaité** (le poste terrain est aujourd'hui un placeholder 90
  €/m²), c'est un mandat « VRD par devis » distinct — mais c'est du VRD, pas du coût de construction
  par taille.

## Artefacts

`/tmp/cout_taille_phaseA.py` (LECTURE SEULE, coût implicite par tranche + croisement vendu/tenu).
Golden 116/116 + tiers au bit près avant/après.
