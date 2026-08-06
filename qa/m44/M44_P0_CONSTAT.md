# M44 — PHASE 0 · CONSTAT FISCAL & DONNÉES (sortie locative du mode B)

**Branche** `m44-sortie-locative-defisc` · base `main` 61659b0b (M42 mergé) · **STOP obligatoire.**
**Nature : LECTURE SEULE** (hors Lot 0, déjà commité). **RÈGLE FISCALE tenue** : aucune affirmation
d'éligibilité, aucun dispositif servi que je n'établis pas en vigueur 2026 sur pièce.

---

## Lot 0 (déjà soldé, commit `[M44-Lot0]`) — rappel

- **score_e** était réellement bâti sur **q_v7_defisc** (run mort) : 77 718 lignes = non-écartée de
  q_v7, pas q_v8 (77 308) ; **428 parcelles servies avec marge estimée alors qu'écartées en q_v8**.
  Défaut aligné sur `Q_A_RUN_LABEL` (point de vérité) + rebuild sur q_v8 → 77 308, **0 écartée**.
- **pc_caducs** : constat sur pièces — `_SELECT_RAW` **ne référence AUCUN run** (permis + `parcels`,
  pas `parcel_p_score_v2`). La note M31 « run servi q_v7_defisc » était **fausse** (doctrine : une
  note n'est pas une source). **Effet de l'alignement de run = 0.** (Un refresh source a bougé
  2 164→2 161 : dérive de fraîcheur des permis, pas le run.) Golden 117/117 · 0 tier.

---

## 1. Dispositifs 2026 — sur pièces (ce qui n'est pas établi = ABSENT)

| Dispositif | En vigueur 2026 | Source | Objectivable PARCELLE |
|---|---|---|---|
| **Pinel / Pinel+ Outre-mer** | **NON** — fin **31/12/2024** (non renouvelé) | LF (fin actée) | — → **ABSENT, ne pas servir** |
| **Denormandie Outre-mer** (réhab. ancien **locatif** avec travaux) | **OUI, jusqu'au 31/12/2027** | **CGI art. 199 novovicies** ; BOFiP plafonds 2026 | **commune éligible** (ORT / Action Cœur de Ville) — liste **à confirmer sur pièce officielle** |
| **Plafonds de loyer 2026 DOM** (le socle « noble ») | OUI | **BOFiP BOI-BAREME-000017-20260310** (10/03/2026) | **100 % Sourçable** (plafond réglementaire €/m²) |
| Girardin logement social (CGI 199 undecies C) | à confirmer | CGI | **opérateur-dépendant** (bailleur) → **PAS** objectivable côté propriétaire → hors v1 |
| LLI (logement locatif intermédiaire) | plafonds 2026 publiés | CGI/BOFiP | zone + opérateur → partiel |
| Loc'Avantages (conventionnement Anah) | **non établi ce tour** | — | → **ABSENT tant que non établi** |

**Chiffres officiels 2026 (BOFiP BOI-BAREME-000017, socle sourçable)** :
- Plafond loyer **DOM base 12,21 €/m²/mois** ; **secteur intermédiaire 12,71 €/m²** ;
- **coefficient de surface** réglementaire : **0,7 + 19/S, plafonné à 1,2** (S = surface habitable) ;
- taux de réduction OM (Denormandie) : 23 % (6 ans) / 29 % (9 ans) / 32 % (12 ans) — informatif,
  **dépend de l'opérateur et de l'engagement, PAS objectivable par parcelle → jamais servi comme fait**.

**Communes La Réunion en périmètre Denormandie (secondaire, à confirmer arrêté/ORT)** : Bras-Panon,
La Plaine-des-Palmistes, Le Port, Saint-André, Saint-Benoît, Saint-Joseph, Saint-Pierre, Sainte-Rose,
Salazie. **Non servi comme « éligible » tant que la liste n'est pas sur pièce officielle** (sinon on
affirme une éligibilité — interdit). En v1, c'est un CONTEXTE (« commune en périmètre ORT — à valider »),
jamais un badge d'éligibilité.

## 2. Les loyers — architecture recommandée

Il n'existe pas de DVF des loyers. Deux voies, **je recommande (a) par défaut + (b) en curseur** :

- **(a) PLAFOND RÉGLEMENTAIRE Sourcé (défaut, voie noble)** : le bilan est calculé « **sous hypothèse
  du plafond réglementaire X** » (BOFiP 2026 : 12,71 €/m² intermédiaire DOM × coef surface). **100 %
  sourçable, dispositif-AGNOSTIQUE** — le produit dit « bilan locatif au plafond réglementaire
  intermédiaire », **jamais** « éligible Girardin/Denormandie ». C'est ce qui respecte la règle fiscale.
- **(b) LOYER DE MARCHÉ en paramètre CLIENT (Estimé)** : curseur, comme le coût travaux M33.
  Héritage d'étiquette M33 : un bilan avec loyer Estimé est **Estimé** ; au plafond Sourcé + travaux
  Estimé → l'ensemble reste **Estimé** (travaux = Estimé).

**Insight clé** : on sert le **BILAN AU PLAFOND**, pas l'ÉLIGIBILITÉ. Le plafond est un fait
réglementaire sourçable ; l'éligibilité dépend de l'opérateur/du montage → à valider par un conseil.

## 3. Population / périmètre

**Mode B (réhabilitation, 33 958) seul en v1** — homogénéité d'abord (mon a priori, confirmé). Le
locatif NEUF (mode A) est **hors mandat v1** : il ouvrirait la question éligibilité-neuf (Pinel mort,
Girardin opérateur) sans socle réhab clair. Recommandé : mode B v1, mode A en dette si valeur prouvée.

## 4. Mention conseil-fiscal proposée (→ dossier avocat CGU/CGV de Vic)

> « Hypothèses fiscales indicatives — le dispositif, l'éligibilité de la parcelle et les plafonds
> applicables sont à valider avec un conseil fiscal. Ce bilan locatif est un calcul paramétré au
> plafond réglementaire affiché ; il ne vaut ni conseil fiscal, ni promesse d'éligibilité. »

---

## STOP — arbitrages Vic

- **A. Dispositifs retenus v1** : je recommande de **ne servir AUCUN badge de dispositif** et de
  calculer le bilan **au plafond réglementaire Sourcé** (BOFiP 2026), dispositif-agnostique. D'accord ?
  (Alternative : servir « commune en périmètre Denormandie » comme contexte, si tu obtiens la liste
  officielle — mais jamais « éligible ».)
- **B. Architecture loyers** : (a) plafond réglementaire Sourcé par défaut + (b) curseur marché Estimé.
  Le plafond intermédiaire DOM 12,71 €/m² × coef surface est-il le bon défaut, ou le base 12,21 ?
- **C. Périmètre** : mode B seul v1 — confirmé ?
- **D. Mention fiscale** : la formulation ci-dessus te convient-elle pour le dossier avocat ?
- **E. Sources** : BOFiP BOI-BAREME-000017 (plafonds 2026) est la pièce officielle ; la LISTE des
  communes Denormandie et le statut Loc'Avantages/Girardin restent **à établir sur pièce** avant tout
  service — d'ici là : ABSENT. OK pour cette prudence ?

**Ma recommandation synthèse** : bilan locatif **au plafond réglementaire Sourcé (12,71 €/m²
intermédiaire × coef 0,7+19/S)** + curseur marché Estimé, **mode B seul**, **zéro badge d'éligibilité**,
mention conseil-fiscal partout. Tout paramètre en `config/calibrage/defisc_2026.yaml` sourcé/daté/linté.

## Annexes
- `qa/m44/dispositifs_2026_p0.csv` (table sourcée) · `qa/m44/plafonds_2026_p0.csv` · `_global.txt`.
- Sources : bofip.impots.gouv.fr (BOI-BAREME-000017-20260310) ; CGI art. 199 novovicies (Denormandie).
