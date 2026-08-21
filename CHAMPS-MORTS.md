# CHAMPS MORTS — diagnostic par champ (M125-D)

> Champs servis par `_q_v2_fiche` (`src/labuse/api/app.py:2375`) et rendus **nulle part**.
> Pour chacun : (1) mort au PDF seul, ou à l'écran aussi ? (2) cause exacte ; (3) recommandation.
> **Aucune suppression, aucun branchement effectué — rapport seul.**
>
> Vérifs base faites en lecture seule sur la base locale `labuse` (431 663 parcelles, seedée ;
> parcelle témoin `97402000AH1966` = Bras-Panon). « présent en base » = la table porte des lignes.

Légende cause : **DÉPRÉCIÉ** (retiré volontairement) · **MAL BRANCHÉ** (donnée présente en base,
jamais rendue) · **DOUBLON** (même donnée servie par un autre champ) · **ABSENT** (rien en base).

| Champ | Mort où ? | Présent en base ? (refresh) | Cause | Recommandation |
|---|---|---|---|---|
| `completeness_score` | **écran + PDF** | oui — `dryrun_parcel_evaluations.completeness_score` (2026-08-19) | **DÉPRÉCIÉ** : c'est de l'analyse (matrice M129-B éteinte) ; l'`icd` porte désormais la complétude affichée. Retiré du PDF en M124-A2. | **Supprimer** du contrat `_q_v2_fiche` (analyse, pas donnée ; déjà remplacé par `icd`). |
| `score_v` (vendabilité V1.3) | **écran + PDF** | oui — `parcel_v_score` (431 663 lignes, refresh 2026-08-09 ; témoin : `v_band='aucun'`) | **DÉPRÉCIÉ** : bloc UI retiré (`Fiche.tsx` commentaire « ALGO-1 item 2 — le bloc est RETIRÉ ») ; remplacé par `score_v2`. Donnée encore calculée/rafraîchie. | **Supprimer** du payload fiche. ⚠ Vérifier d'abord qu'aucun consommateur externe (API v1) ne le lit avant retrait du contrat. |
| `anru` (périmètre NPNRU parcellaire) | **écran + PDF** | oui — `spatial_layers` kind='anru' (8 périmètres ; 0 à ≤100 m du témoin) | **MAL BRANCHÉ** + **DOUBLON partiel** : calculé par parcelle (dans/adjacente <100 m) mais jamais rendu. Le PDF affiche déjà le NPNRU au niveau **commune** (`contexte_commune.anru`, via endpoint). | **Brancher** la proximité parcellaire (info utile : environnement d'un programme) **ou supprimer** si le grain commune suffit. Trancher le doublon. |
| `terrain` (dict brut : `pente_moy_deg`, `pente_max_deg`, `flag_terrassement_lourd`) | **écran + PDF** (dict brut) | oui — `parcel_terrain` (431 663 lignes, refresh 2026-08-13 ; témoin : pente 2,1°) | **DOUBLON** : la pente est déjà servie via `pente_terrain` (dérivé `pente_texte`) et la ligne cascade `pente`. Le dict brut est redondant. **MAL BRANCHÉ** pour `flag_terrassement_lourd` (jamais rendu). | **Supprimer** le dict brut redondant ; **brancher** `flag_terrassement_lourd` s'il est jugé utile (sinon supprimer aussi). |
| `coproprietes` (RNIC) | **écran + PDF** | oui — `rnic_coproprietes` (2 220 lignes, refresh 2026-07-10 ; 0 pour le témoin) | **MAL BRANCHÉ** : donnée RNIC réelle (cible bailleur / Mode B), jamais rendue. Distinct de `mode_b` (réhabilitation) qui, lui, est rendu. | **Brancher** (donnée réelle, cible copro/bailleur) **ou** confirmer hors périmètre fiche. |
| `marche_secteur` (`filosofi_carreaux_200m` + `rpls_commune`) | **écran + PDF** | oui — Filosofi 2021 (14 773 carreaux) + RPLS 2025 (24 communes) ; témoin : carreau présent + RPLS 1 679 logements | **MAL BRANCHÉ** + **DOUBLON de périmètre** : donnée socio-éco réelle, mais le marché AFFICHÉ vient d'une autre source (`marche_service`/onglet Faisabilité). | **Brancher** (contexte carreau/parc social) **ou supprimer** si redondant avec le marché déjà servi. |
| `parc_analysees` (compteur du run) | **écran + PDF** | n/a (compteur calculé) | **DÉPRÉCIÉ** : composant « N parcelles analysées » (TheatreCompteur) retiré (`Fiche.tsx` commentaire « M55-L point 6 »). | **Supprimer** du contrat. |
| `flags` (sous-ensemble de `lines`) | **écran + PDF** | dérivé de `lines` (weight ∈ {0, null} & result SOFT_FLAG/HARD_EXCLUDE/UNKNOWN) | **DOUBLON** : sous-ensemble de `lines`, déjà rendu via les lignes/tiroirs (`Fiche.tsx` commentaire « M55-O phase 2.2 — supprimé : redites »). Le PDF rend `lines`. | **Supprimer** du contrat (doublon de `lines`). |

## Constats transverses

- **Aucun champ mort n'est « ABSENT en base »** : tous ont soit une donnée réelle (mal branchée),
  soit un doublon, soit un statut déprécié assumé. La dette est de **branchement/contrat**, pas
  d'ingestion.
- **Répartition des causes** — DÉPRÉCIÉ : `completeness_score`, `score_v`, `parc_analysees` ·
  MAL BRANCHÉ (donnée réelle jamais rendue) : `anru`, `coproprietes`, `marche_secteur`,
  `terrain.flag_terrassement_lourd` · DOUBLON : `flags`, `terrain` (pente), `anru` (partiel).
- **Impact M125-A** : parmi ces morts, `terrain`, `marche_secteur`, `anru`, `coproprietes` portent
  de la **donnée** (pas de l'analyse) → candidats potentiels au PDF exhaustif (M125-A) **une fois
  branchés et validés**. `completeness_score`, `score_v`, `parc_analysees`, `flags` sont de
  l'analyse ou des doublons → **ne pas** les envoyer au PDF.

## Remontée (hors liste du mandat)

- **`depots`** : listé dans la cible M125-A, mais **n'est PAS un champ de `_q_v2_fiche`** — il est
  servi par une autre fonction de fiche (`app.py:3827`, fiche legacy/`_build_fiche`). Avant de
  l'ajouter au PDF premium (M125-A), il faut d'abord **le brancher dans `_q_v2_fiche`** (sinon le
  PDF premium n'y a pas accès). À arbitrer.

---

*Rapport M125-D. Ne modifie aucun comportement. Base d'arbitrage pour brancher/rafraîchir/supprimer.*
