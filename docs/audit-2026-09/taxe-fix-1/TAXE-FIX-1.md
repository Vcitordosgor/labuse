# TAXE-FIX-1 — Taxe d'aménagement : exonérations, archéologie préventive, taux majorés, surface taxable

**Branche** `fix/taxe-fix-1` (worktree `~/Desktop/labuse-taxefix`, base main `4bbe8a34`) · non mergé · 6 commits (1 par point + 1 adaptation de test).
**Doctrine** : tout passe par `taxe_amenagement.calculer()` (aucun barème/taux en dur ailleurs) ; chaque règle porte sa citation (article, URL Légifrance, date de vigueur).
**Suite de** TAXE-AUDIT-1. Le barème 2026 (892 €/m² = vraie valeur, ne pas y toucher) et les 24 taux communaux sont restés inchangés.

| Point | Commit |
|---|---|
| 1 — Exonérations de plein droit (CGI 1635 quater D) | `5d41ce7f` |
| 2 — Redevance d'archéologie préventive (0,40 %) | `fbd325ce` |
| 3 — Secteurs à taux majoré (DELTA, grain parcelle) | `f1c51f12` |
| 4 — Surface taxable ≠ SDP + taux départemental confirmé | `d86dd131` |
| — adaptation tests fiche §7 (passage par `taux_parcelle`) | `f0af641b` |

État des tests : **pytest 81 passed, 10 skipped** (les skips sont des tests marqués `db` : la base de test `labuse_test`/rôle `labuse` n'existe pas dans cet environnement — limitation d'env, pas une régression ; la logique DB est prouvée en LIVE, voir CAPTURES §3). **tsc + vite build verts. vitest 187/187.**

---

## Point 1 — Exonérations de plein droit (CGI art. 1635 quater D)

**Avant** : un hangar agricole en zone A était taxé plein pot (26 760 € pour 400 m²) ; le PLAI était traité en **abattement 50 %** au lieu d'exonération.

**Après** : `calculer()` gagne `surface_exoneree_m2` + `motif_exoneration`. Une surface **exonérée** ne produit **aucune part (0 €)** — distincte de l'abattement (−50 %) — avec une ligne qui **nomme le motif et son numéro d'article**.

**Source** : CGI art. 1635 quater D (en vigueur 01/01/2026), [Légifrance LEGIARTI000050193341](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050193341), lu le 24/09/2026 ; BOFiP BOI-IF-TU-10-20-30.

**Motifs RETENUS** (rendables sans convention ni liste réglementaire) — cases « Nature du projet » :

| Case | Motif | Article |
|---|---|---|
| Locaux agricoles | serres de production, bâtiments d'exploitation, stockage de récoltes, abris d'animaux, matériel | **1635 quater D, 3°** |
| Logements PLAI / très sociaux | prêt locatif aidé d'intégration (LLTS) | **1635 quater D, 2°** |
| Reconstruction à l'identique | bâtiment détruit/démoli depuis < 10 ans, après sinistre | **1635 quater D, 9°** |
| (déjà présent) < 5 m² | petites surfaces | **1635 quater D, 10°** (citation corrigée : était « 1° ») |

**Motifs LAISSÉS** (non rendables sans deviner ou sans pièce que l'outil n'a pas) : **1°** service public / utilité publique (engagement de conservation + liste par décret) ; **4°** centres équestres de loisir ; **5°/6°** OIN / ZAC à équipements mis à la charge des constructeurs (dépend de la convention) ; **7°** projet urbain partenarial (convention) ; **8°** aménagements prescrits par un PPR (travaux prescrits, pas un projet). Les **exonérations FACULTATIVES** votées par délibération (CGI art. 1635 quater E) sont **signalées** dans l'outil (« à vérifier auprès de la commune ») mais **non appliquées** (aucune délibération d'exonération facultative en base).

**UI** : bloc « Nature du projet » (cases mutuellement exclusives) ; en **zone A**, la case « Locaux agricoles » est **proposée** (non cochée) avec la mention « les locaux agricoles y sont exonérés de plein droit ». Le PLAI est distinct de la case « Logement aidé » (PLUS/PLS → abattement 50 %).

**Témoins** (LIVE, endpoint, cf CAPTURES §2) : CO0322 hangar agricole 400 m² → **0 €** ; « 10 logements dont 3 PLAI » → les 3 (180 m²) exonérés, les 7 (420 m²) au barème (assiette 374 640). Écran : `apres-02-agricole-exonere-0.png`, `apres-03-nature-du-projet.png`.

---

## Point 2 — Redevance d'archéologie préventive (0,40 %)

**Avant** : absente de l'outil ; au Dossier financier, calculée **0,68 €/m² × SDP** — c'est le régime **au m²** (aménagements sans permis) et une **valeur périmée** (0,68 = 2025 ; 2026 = 0,69).

**Après** : `calculer()` chiffre la RAP = **0,40 % de la MÊME assiette** que la taxe d'aménagement (surface × valeur forfaitaire, **abattements ET exonérations inclus** — l'assiette exclut déjà les surfaces exonérées, donc la RAP les suit). Ligne **distincte** sous le total dans l'outil **et** au Financier.

**Source** : code du patrimoine art. **L524-7** (redevance due pour les travaux soumis à autorisation d'urbanisme, taux **0,40 %** assis sur l'assiette de la TA) ; assiette/abattements identiques à la TA (BOFiP / service-public). Le régime au m² (0,69 €/m² en 2026, arrêté du 23/12/2025) vise les aménagements SANS permis → **retiré** du Financier (qui modélise un programme de construction = permis) : il n'y avait pas d'usage réel de ce régime dans un bilan de promotion.

**Un seul calcul** : le Financier ne calcule plus rien lui-même — le `builder` chiffre la RAP via `calculer()` sur la SDP du projet (toujours, même si la taxe a été saisie à la main) et la passe en hypothèse `rap` ; `financier_bilan` la relaie (passe-plat, comme la taxe).

**Témoin** (LIVE) : CO0322 400 m² RP → assiette 312 200 → **RAP = 1 248,80 €**. Écran : `apres-05-taxe-RAP-resultat.png` (« Redevance d'archéologie préventive (0,4 %) 1 249 € »).

---

## Point 3 — Secteurs à taux majoré

**Avant** : écartés dès l'ingestion (`parcelle is null`) → calcul aveugle au taux général.

**Après** : la source **porte bien** les secteurs à taux majoré, au **grain PARCELLE** (colonnes `prefixe/section/parcelle` de DELTA). Un « secteur » y est une **liste de parcelles**. On les réingère (même chargeur DGFiP/DELTA) dans `taxe_amenagement_secteur` (clé = **IDU** reconstruit, 14 car.). La « géométrie » est l'**identité cadastrale exacte** (jointure sûre par IDU, pas une intersection approchée). Résolution `taux_parcelle(idu)` = **secteur si présent, sinon taux général** ; branchée dans le prefill, le calcul (paramètre `idu`), la fiche §7 et le Dossier financier. Le drapeau `secteur_majore` est **exposé et DIT** (outil : « secteur majoré » ; fiche : « Taux communal (secteur majoré) »).

**Source des taux majorés** : DGFiP / application DELTA, jeu ouvert `delta_deliberation_tam_17_01_23` (data.economie.gouv.fr), lignes `zone_application=Communale` **avec parcelle**. Relevé LIVE 24/09/2026 — **6 communes du 974** en ont : **Saint-Leu 14 %** (9 398 parcelles), **Trois-Bassins 20 %** (268), **Saint-Paul 10 %** (649), **Les Avirons 10 %** (189), **Entre-Deux 8,5 %** (121), **Le Port 5 %** (1 011). Les lignes sentinelles à **99 %** (données DELTA) sont écartées par les bornes `[0 ; 20]` (CGI art. 1635 quater E/F : jusqu'à 20 %).

**Preuve LIVE** (pipeline DELTA réel, transaction **annulée**, cf CAPTURES §3) : 649 secteurs Saint-Paul ingérés → `97415000CT2268` = **10 % (secteur majoré)** ; **CO0322 = 5 % (taux général, hors secteur)** — donc le total 23 415 € de l'audit reste juste. Les tests DB (`taux_parcelle`/ingestion) sont écrits (skippés faute de base de test ici). Un test **pur** couvre la reconstruction d'IDU.

**Reste ops** : lancer l'ingestion (`labuse ingest-taxe-amenagement`) en prod pour peupler la table — le code crée la table au schéma (`ensure_secteur_table`).

---

## Point 4 — Surface taxable ≠ SDP + taux départemental confirmé

**Surface taxable** : le champ (déjà nommé « Surface taxable ») porte désormais l'aide « **close et couverte > 1,80 m, garages et annexes INCLUS** (CGI art. **1635 quater H**) — ≠ SDP ». Le bouton « reprendre » devient « **Partir de la SDP du projet (à compléter : garages, annexes)** » : la SDP est un point de départ, pas la surface taxable (la surface taxable inclut garages/annexes que la SDP d'urbanisme déduit). Note de la fiche §Fiscalité alignée ; source du Dossier financier honnête (« surface taxable ≈ SDP du projet, garages/annexes non modélisés »).

> **Correction de citation** : le mandat citait « art. 1635 quater B » pour la définition de la surface. La bonne référence est **CGI art. 1635 quater H (1°)** (« somme des surfaces de plancher de chaque niveau clos et couvert, au nu intérieur des façades »), confirmée par **BOFiP BOI-IF-TU-10-30-10 §20** (caves § 240 et stationnements § 170-210 **inclus**, à la différence de la surface de plancher d'urbanisme, art. L.111-14 c. urb.).

**Taux départemental** : le « plafond légal 2,5 % — à confirmer » **codé en dur** dans l'outil devient « **2,5 % — confirmé (délibération départementale, source DGFiP/DELTA)** » quand la config le confirme (`part_departementale_confirmee_974`), comme la fiche. (Vérifié LIVE : le hint du champ lit « 2,5 % — confirmé ».)

Écran : `apres-04-surface-taxable-aide.png`, `apres-05-taxe-RAP-resultat.png`.

---

## Vérification

- **pytest** (taxe, ingestion, fiche, financier, exports, oracle, bilan) : **81 passed, 10 skipped** (skips = tests `db`, base de test absente de l'env ; logique DB prouvée en LIVE).
- **tests neufs par règle** : exonération agricole = 0 €, PLAI exonéré ≠ abattu, programme mixte 3 PLAI/10, reconstruction ; RAP 0,40 % de l'assiette + RAP suit l'exonération ; reconstruction d'IDU pure + ingestion/résolution secteur (DB) ; bilan lot 5 mis à jour (RAP passe-plat 2 832,99).
- **tsc -b** vert ; **vite build** vert ; **vitest 187/187**.
- **Captures** : `CAPTURES.md` (avant/après déterministe + endpoint LIVE + pipeline DELTA LIVE) et `apres-0*.png` (écran de l'outil).
- **App/navigateur arrêtés** avant de rendre la main (`lsof -ti :8445 :5645` → libre).

## Hors mandat (non fait)

Barème 2026 (juste, inchangé) · les 24 taux communaux (justes, inchangés) · les autres outils · aucun merge. Ingestion prod des secteurs = étape ops de Vic.
