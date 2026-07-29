# M19 — PHASE 4 : vérification post-merge (main mergée)

Exécutée sur **`main`** après merge des 4 branches M19 (`audit/m19-inventaire`, `design/m19-maquettes`,
`feat/m19-fiche`, `feat/m19-fusion-onglets`) — commits de merge `c49cbb5 · 60a5595 · 8ff735b · 171a87f`.
**Non poussé** (Vic valide et pousse).

## Intégrité du merge
- Aucun marqueur de conflit dans `Fiche.tsx`. `tsc -b && vite build` : **0 erreur**.
- La fiche mergée = la version « référence » de `feat/m19-fusion-onglets` (RefDrawer, carte verdict, micro-preuves,
  7 tiroirs, IA en bas, actions segmentées). Capturée sur main : `qa/m19/phase4/P4_fiche_fermee.png` — **identique**
  à la branche.

## Golden (main mergée, `LABUSE_DEV_MODE=1`, API :8000)
```
Bilan: 116/116 PASS, 0 FAIL, 0 parcelle(s) avec incohérence base↔API (runtime)
```

## R1 — échantillonnage : 15 infos de `M19_INVENTAIRE_FICHE.md`, **toutes retrouvables** dans la fiche
Preuve = dump du texte rendu, tous tiroirs + toggles ouverts (`qa/m19/phase4/fiche_texte_complet.txt`).

| # | Info inventoriée (section) | Où dans la nouvelle fiche | Retrouvée |
|---|---|---|---|
| 1 | Adresse postale BAN (A) | en-tête (« 204 Rue de l'égalité, 97438 Sainte-Marie ») | ✅ |
| 2 | Surface m² (A) | en-tête (« 274 m² ») | ✅ |
| 3 | rang N verdict (A) | carte VERDICT (« rang 11 ») | ✅ |
| 4 | Badge signaux vendeur N/100 (A/E) | tiroir Propriétaire → « Signaux vendeur / 18 » | ✅ |
| 5 | Confiance données ICD (E) | tiroir Confiance et données (« 90 % », bande « confiance haute ») | ✅ |
| 6 | Signal vendeur « Cession de fonds de commerce < 12 mois » + source BODACC (E) | tiroir Propriétaire → Signaux vendeur → « Pourquoi ce score » | ✅ |
| 7 | age_dirigeant « Gérant âgé (81 ans) » (F proprio) | tiroir Propriétaire (ligne + pastille verdict) | ✅ |
| 8 | Potentiel de transformation — sous-densité / surélévation (E) | tiroir Règles d'urbanisme (TransformationBlock) | ✅ |
| 9 | Règlement PLU — Géoportail Urbanisme, disclaimer (E) | tiroir Règles d'urbanisme (ReglementPluBlock) | ✅ |
| 10 | Viabilisation — PV S3REnR / assainissement (E) | tiroir Viabilisation et réseaux (ViabilisationBlock) | ✅ |
| 11 | Gestionnaires — EDF SEI / CISE / CINOR (E) | tiroir Viabilisation et réseaux (GestionnairesBlock) | ✅ |
| 12 | Équipements ortho — Pente (E) | tiroir Viabilisation et réseaux (EquipementsBadges) | ✅ |
| 13 | Traducteur PLU « Traduire ma zone en français courant » (F) | tiroir Règles d'urbanisme (TraducteurBloc) | ✅ |
| 14 | Risques — couche ABF (F) | tiroir Risques (ligne « Hors périmètre ABF ») | ✅ |
| 15 | Faisabilité — calcul étape par étape (G) | tiroir Faisabilité et bilan (steps) | ✅ |

**15/15.** Rien n'a été perdu entre les 4 branches (R1). Les 3 items initialement « non trouvés » par le grep
(4, 5, 6) l'étaient par un artefact de recherche (chaîne trop littérale « 18/100 » ; double-clic refermant le
panneau « Pourquoi ce score ») — reconfirmés présents par ouverture ciblée : « Cession de fonds de commerce »,
« Détention longue », « BODACC », « Signal faible » tous FOUND.

## Non-régression (interactions testées sur main, 0 erreur console)
| Contrôle | État |
|---|---|
| **+ Pipeline** | ✅ présent (bouton, rangée 1) |
| **+ Projet** | ✅ présent (menu M15-C3) |
| **Export PDF** | ✅ tuile segmentée (reflète la charge foncière si calculette active) |
| **Export Dossier** | ✅ tuile |
| **Export Financier** (ex-Banquier) | ✅ tuile (async prepare/statut préservé) |
| **Export 1950** | ✅ tuile (comparateur temporel M08) |
| **Export Cadastre** | ✅ tuile (Géoportail Parcellaire Express) |
| **Export Maps** | ✅ tuile (Google Maps) |
| **IA** | ✅ la carte IA (bas de pile) ouvre l'AskBar déplié (`data-askbar`) |
| **Calculette** | ✅ présente (`data-calculette`) dans le tiroir Faisabilité — composant M15-C2 partagé, non dupliqué |
| **Cloche de suivi** | ✅ en-tête (titre « Suivre »/« Suivie », état réel via toggleWatch) |

Captures : `qa/m19/phase4/P4_fiche_fermee.png`, `P4_ia_ouverte.png`, `P4_calculette.png`.

## Verdict PHASE 4
Merge propre, golden 116/116, non-régression complète (11/11 contrôles), R1 prouvé (15/15). **Prêt.**
Réserve inchangée : 6ᵉ tuile = « Maps » là où la référence montrait « Courrier » (fonction préservée, aucune
fonction courrier câblée — arbitrage Vic).
