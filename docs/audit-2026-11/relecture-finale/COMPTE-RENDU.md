# Relecture finale — Étude de faisabilité réellement générée (branche `fix/gabarit-3d-3`)

Deux parcelles en cause : **BI0351** = `97408000BI0351` (La Possession) · **HT0538** = `97416000HT0538`
(Saint-Pierre). Documents régénérés in-process (TestClient + WeasyPrint, base locale, 0 prod) par
`scripts/relecture_finale_docs.py` → `docs/audit-2026-11/relecture-finale/*.pdf` + `.txt`. **Règle B** :
chaque correction est citée depuis le PDF régénéré.

---

## 1. Comparatif BI0351 — les 31 % de zone rouge remis dans les contraintes — **FAIT**

La colonne « Contraintes relevées » tronquait à 4 contraintes et évinçait la PPR zone rouge. Désormais elle
est **prioritaire** (jamais tronquée) et **sans** « pas d'exclusion automatique » (`_compare_row`, app.py).

> PDF régénéré `comparatif_BI0351.txt` : « Contraintes relevées … **PPR zone rouge sur 31 % de la surface** »
> (BI0351) · « PPR zone rouge sur 11 % de la surface » (BI0346) · « Exclue : PPR zone rouge » (AC2749).

## 2. Analyse BI0351 — plus de commentaire zone rouge sur l'aléa faible — **FAIT**

Le classement « zone rouge » du PPR était appliqué à CHAQUE aléa avec sa propre part. Un aléa de niveau
**faible** (part = la portion HORS zone rouge, ~69 %) ne porte plus « Zone rouge » ni son commentaire
(`pige/api.py`, `_risques_rows`).

> `analyse_BI0351.txt` — avant : « Mouvement de terrain · Faible · **Zone rouge · 69 %** · Zone rouge du PPR… ».
> Après : « Inondation · Fort · **Zone rouge · 31 %** · Zone rouge du PPR… » **et** « Mouvement de terrain ·
> Faible · **69 % de la parcelle** · Aléa signalé (Géorisques), **hors zonage PPR** ».

## 3. PLU de La Possession — 17/12/2025 = approbation, pas publication — **FAIT**

La date du document GPU (« horizon », 17/12/2025) était dite « publiée au Géoportail ». C'est la date
d'**approbation de la version en vigueur** (millésime du document opposable) — libellé corrigé
(`miroir.py`, `_r_statut_plu`).

> `dossier_BI0351.txt` : « PLU approuvé le 12/06/2019 — **version en vigueur approuvée le 17/12/2025**
> (document opposable au Géoportail de l'urbanisme). »

## 4. Ventes du neuf à Saint-Pierre — une seule période (5 ans) — **FAIT (à la source)**

La couche VEFA annonçait « 36 mois » codé en dur (`cascade/layers/fiche_couches4.py`) alors qu'elle est
ingérée sur **5 ans** (`NEUF_VEFA_FENETRE_ANS`), la MÊME fenêtre que le Dossier. Corrigé → « 5 ans ».

> `dossier_HT0538.txt` : « Neuf VEFA — commune … 158 ventes (commune, **5 ans**) ». La mention « 36 mois »
> n'apparaît dans AUCUN PDF (elle vivait dans le repère servi de l'outil Comparer, lu depuis
> `dryrun_cascade_results`) : la correction est à la source ; le repère servi s'aligne au prochain calcul,
> le Dossier affiche déjà 5 ans en direct. Même valeur (158 ventes), une seule période.

## 5. Droit de préemption à Saint-Pierre — une seule formule, celle du Dossier — **FAIT**

L'Étude signalait « DPU sur le terrain » dès que le bloc DPU existait. Or son état est **« non_determinee »**
(périmètre NON publié au GPU — délégataire EPF Réunion) ; le Dossier le range dans « **hors périmètre de
préemption urbaine publié** » (rien à signaler). L'enrichissement de l'Étude ne signale plus le DPU dans ce
cas (`modules.py`, `_attach_contraintes_signalees`).

> `etude_HT0538.txt` : plus aucune ligne « Droit de préemption urbain (DPU) » dans les contraintes.
> `dossier_HT0538.txt` : « Hors périmètre de préemption urbaine publié. »

## 6. Étude de faisabilité HT0538 — garde-fous d'honnêteté (sans toucher au moteur) — **FAIT**

**a. 888 m² « exploitable » vs 614 m² de la fiche.** Garde-fou de rendu (`rendu_etude`) : quand le plancher
de l'Étude dépasse la SDP maximale réglementaire de la fiche (`capacite_fiche_sdp_m2`, attachée depuis
`_potentiel_transformation_block`, la même valeur que Dossier/Comparatif/pré-dossier), l'étude n'est jamais
dite « exploitable » → **« À vérifier »**, écrit en clair.

> `etude_HT0538.txt` : « **À vérifier, pas « exploitable »** : le plancher de cette étude (≈ 888 m²) dépasse
> la surface de plancher maximale réglementaire de la fiche (≈ 614 m², reprise du Dossier, du Comparatif et
> du pré-dossier) … » · « Votre projet … **À vérifier** ».

**b. Stationnement.** Barème du PLU indisponible (art. —, `ratio_par_logement = None`,
`etat = « document manquant »`) → plus de « 0 place selon la règle du PLU » : **« Stationnement non vérifié »**,
et la conclusion n'est pas « exploitable » (`_stationnement_3lignes` + garde-fou de verdict).

> `etude_HT0538.txt` : « **Stationnement non vérifié** — le barème du PLU de cette commune n'est pas
> disponible : LABUSE n'a pas dessiné de places réglementaires. »

**c. Risques de la fiche.** L'Étude porte maintenant, comme le Dossier §5, le **système d'endiguement** et la
**zone inondable extrême (TRI)** (lues dans les lignes servies, `_attach_contraintes_signalees`).

> `etude_HT0538.txt` : « Système d'endiguement — inondation résiduelle… » · « **Zone inondable (TRI, scénario
> extrême)** ».

**d. Plan — section cadastrale.** « AW 538 » était codé en dur près du contour. La section vient maintenant de
l'identifiant de la parcelle (`idu[8:10]`), comme le cartouche (`implantation/planche.py`).

> `etude_HT0538.txt` : « **HT 538** » près du contour **et** « Parcelles HT 538 » au cartouche (plus aucun
> « AW 538 »).

---

## 7. Diagnostic (lecture seule) — pourquoi 888 contre 614 ? Lequel a raison ?

**Deux moteurs, deux nombres, pour la même parcelle HT0538 (zone Ud, contenance 510 m²).** Ils lisent les
**mêmes règles du PLU** : emprise au sol (CES) **60 %** (Ud3.4), hauteur à l'égout **15 m** → **R+4** (Ud3.5),
pleine terre **20 %** (Ud5.1).

| | **Fiche / Dossier / Comparatif / pré-dossier** | **Étude de faisabilité** |
|---|---|---|
| Nombre | **614 m²** | **888 m²** (887,5) |
| Moteur | `faisabilite` (fourchette), `potentiel_transformation` | `implantation` (plan masse) |
| Méthode | **enveloppe réglementaire** : emprise constructible insetée des reculs (**273 m²**) × niveaux, bornée par le **plafond d'emprise au sol** (`etape_limitante`) | **plan masse dessiné** : une **barre R+4, 10 logements** posée dans la zone d'implantation (265,5 m²), SDP = somme des planchers réellement dessinés |
| Hauteur utilisée pour la SDP | niveaux réglementaires appliqués à l'emprise plafond (résultat ≈ 2,25 niveaux effectifs sur 273 m²) | **R+4 plein** (5 niveaux) sur une emprise dessinée plus petite (~178 m²/niveau) |
| Facteur limitant | l'**emprise au sol** (CES) | la **hauteur** (R+4), l'emprise dessinée restant sous le CES |

**Où est la divergence.** La fourchette (614) plafonne la SDP par **l'emprise au sol réglementaire** extrudée ;
l'implantation (888) exploite **toute la hauteur R+4** sur une emprise dessinée plus petite — elle atteint donc
**plus** de plancher. Les deux respectent le CES et la hauteur pris séparément, mais **combinent emprise et
niveaux différemment** : la fourchette borne par l'emprise, l'implantation borne par la hauteur.

**Lequel a raison.** Pour « ce qu'on peut **réglementairement** construire », le **614 m² de la fiche est la
référence** — c'est la SDP maximale réglementaire, servie **à l'identique** par le Dossier, le Comparatif et le
pré-dossier. Le **888 m² de l'Étude est optimiste** : un plan masse qui **dépasse** ce majorant réglementaire ;
il ne doit donc pas être vendu comme « exploitable » tant que la contradiction n'est pas levée — d'où le
garde-fou « À vérifier » ci-dessus (point 6a). **La vraie réconciliation** (pourquoi l'implantation atteint 888
quand la fourchette plafonne à 614) est un **écart de MOTEUR** : soit la fourchette sous-estime la SDP
atteignable en hauteur, soit l'implantation sur-dessine au-delà de l'emprise réglementaire. **Non corrigé dans
cette branche** (aucune touche au moteur demandée) : à trancher dans une branche dédiée, en fixant **une seule
définition** de la SDP maximale partagée par les deux moteurs.

---

Hook vert, branche poussée, pas de merge.
