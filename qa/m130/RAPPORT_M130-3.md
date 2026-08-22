# M130-3 — PDF projet : rapports A.1, A.3, D.1 (avant correctif)

Branche `feat/m130-pdf-projet`. Ne pas merger.

---

## A.1 — Les deux chemins (pourquoi une A/N reçoit tantôt une SDP, tantôt « non constructible »)

Le document affiche **deux informations résolues séparément**, sur **deux zones
différentes** de la même parcelle :

1. **La SDP + la cause** viennent du cache `parcel_residuel`, écrit par
   `compute_residuel` / le moteur de faisabilité (`faisabilite/engine.py`). Le
   moteur résout la zone via `parcel_context` et calcule sur **UNE** zone. Pour
   une zone A/N, `resolve_zone` renvoie `constructible_neuf=False` → le moteur
   marque non constructible → `cause = zone_non_constructible:<zone>`, SDP = 0.
2. **La zone AFFICHÉE** vient d'une lecture **indépendante** dans
   `_shortlist_pdf` : la zone `plu_gpu_zone` **dominante par surface
   d'intersection** (`spatial_layers`).

**Le défaut** : quand une parcelle **chevauche** une zone A/N ET une zone
constructible (U/AU), le moteur calcule le résiduel sur la **sous-zone
constructible** (SDP > 0, `cause = NULL`), tandis que l'affichage retient la
zone **A/N dominante par surface**. Résultat : « 2 149 m² sur du Nco ».

**Preuve** : compté sur toute l'île par la zone **du moteur**
(`parcel_residuel_bati.zone`), les parcelles A/N avec SDP chiffrée = **0**. Le
moteur ne construit **jamais** sur une A/N. La divergence est donc **100 %
d'affichage** : zone dominante (surface) ≠ zone du moteur. C'est aussi pourquoi
deux parcelles A voisines diffèrent (`CV0474` a une `cause`, `CX1483` n'en a pas)
— l'affichage se cale sur la **présence d'un champ `cause`**, pas sur la famille
de zone (d'où le §A.4 : c'est la famille qui doit décider).

---

## A.3 — Combien de parcelles A/N portent une SDP chiffrée

| Périmètre | Parcelles | A/N (zone dominante affichée) + SDP chiffrée |
|---|---|---|
| Projets existants (`projet_parcelles`, 290 parcelles) | 290 | **1** — `97418000AT1356`, zone **A**, **13 687 m²** |
| Cadrage test P2 (Le Tampon ≥ 3 000 m²) | 60 | **2** — `BV2471` Nco 638 m², `CL1113` Nco 2 149 m² |
| Cadrages test P1, P3 | 60 + 60 | 0 |
| Île entière, par la zone **du moteur** (`parcel_residuel_bati.zone`) | — | **0** |

**Faible en nombre, sévère en ampleur** : un faux droit à bâtir de **13 687 m²
sur une zone A** (agricole) dans un projet réel. Le correctif famille (A.2/A.4)
les supprime **tous**, de façon déterministe et indépendante du cache résiduel.

---

## D.1 — Le plafond de 60

- **60 = `shortlist_defaut`** (`config/projets.yaml` : « taille servie sans
  demande explicite »). Plafond absolu = **`shortlist_max: 200`**.
- Écrit au figeage par `_figer_shortlist` (`limit=None` depuis proposer/rejeu →
  60).
- **Critère des 60** : le commentaire de config le dit — « la shortlist figée
  d'un projet est un **TOP-N best-first (classé par probabilité de mutation)** ».
  `_run_cadrage` → `_q_v2_list` `ORDER BY rang` = **rang P** (proba de mutation).

**Donc** : depuis M130-2 l'**ordre d'affichage** est géographique, mais
l'**appartenance** des 60 (quelles 60 sur N) reste un **rang de proba de
mutation caché**. → à divulguer (§D.2), avec le décompte du vivier et une
alternative neutre proposée.

---

## Correctifs A → F appliqués (résumé)

- **A** — la **famille de zone** décide : zone A/N (agricole/naturelle) → jamais
  de SDP chiffrée, « aucune (zone non constructible) ». Indépendant du cache.
- **B** — ligne **Hauteur PLU toujours présente** avec état explicite : PLU
  calibré / estimation générique / « règlement non outillé pour cette zone » /
  « non applicable — zone non constructible ». Jamais d'omission.
- **C** — section limites **adaptée à l'absence** de shortlist (P4) : pas de date
  à trou.
- **D** — plafond **dit** : « N figées sur ~V retenues par le cadrage (à ce
  jour), sélectionnées par probabilité de mutation » + alternative neutre.
- **E** — libellés qui **nomment la contrainte** : « résiduel constructible nul
  après reculs » (ex-terrain_exigu), « capacité annulée par les modulations
  (risque/pente/servitude) » (ex-redhibitoire), « logement non admis au
  règlement de la zone » (ex-habitat_interdit).
- **F** — surface parcelle affichée (Sourcé — cadastre) ; décimales en
  **virgule** (3,5 m) ; « ~ 0 m² (Estimé) » → « aucune » ; **via renvoi** :
  affiché quand `resolve_zone.via_renvoi` est renseigné.

### Note d'arbitrage sur F.4 (« via renvoi »)

L'incohérence citée (`AU3a` cite « Zone U3a » sans le mentionner, alors que
`1AUc`/`1AUb` le portent) est **au niveau des données**, pas de l'affichage : la
mention « via renvoi » vit dans les **chaînes source** des YAML PLU calibrés
(`Art. Uc10.2, p.46 **via renvoi** (ZONE AUindicée, p.83)` pour `1AUc` ; absente
pour d'autres). Le champ structuré `via_renvoi` de `resolve_zone` est `None` pour
ces zones — l'info n'est portée que par le texte source. Le PDF affiche la source
**fidèlement** (verbatim) + `via_renvoi` quand il est renseigné ; **harmoniser
réellement** suppose une passe de normalisation des `*_src` dans
`config/plu_<commune>.yaml` — un **mandat data** distinct, pas un correctif
d'affichage. Signalé pour arbitrage.
