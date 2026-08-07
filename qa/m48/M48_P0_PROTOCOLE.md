# M48 — PHASE 0 · PROTOCOLE de l'audit de cohérence (« LABUSE ne dit jamais deux choses »)

**Branche** `m48-coherence-globale`, base `origin/main` `e91b46ea` (post-merge M47). **Lecture
seule.** Run servi `q_v8_calibre` (lu de `config/served_run.txt`). Extraction **OUTILLÉE** (script
qui interroge l'API live + les tables matérialisées), jamais à l'œil.

## 1. Échantillon stratifié — `select_sample.py` → `echantillon.csv` (26 parcelles, 13 communes)

Déterministe (aucun aléa). Couvre :
- **Les 11 tiers servis** (brûlante, chaude, à creuser, potentiel long terme/`reserve_fonciere`,
  les 6 déclassées, écartée) — 1 à 2 par tier, communes variées.
- **Cas spéciaux** : locatif M44 (`score_e`), société M43 (`parcelle_personne_morale`),
  Renouvellement M47, RNU Saint-Philippe (97417), dépôt permis M38 (`sitadel_permits`),
  sans adresse (absente de `adresses`), commune sous radar M41 (97413).
- **Témoins récurrents** : `97418000AT2542` (brûlante), `97419000AL1154` (fourchette/piscine),
  `97422000CY0197` (bâti marginal divisible), `97411000EP0228` (piscine M39/M40),
  `97404000AZ0004` (Renouvellement rang 1).

## 2. La grille — `audit_grid.py` → `grille.csv` / `divergences.csv` / `pieges_latents.csv`

Pour chaque parcelle, extrait de CHAQUE surface les grandeurs comparables et compare :

| Grandeur | Surfaces interrogées | Point de calcul unique attendu |
|---|---|---|
| **tier effectif** | fiche V2, fiche legacy, carte (tuile), export md, one-pager, DB | `parcel_p_score_v2.tier` (via `verdict_servi`/`tier_v2` — règle étage0→ecartee) |
| **rang** | fiche V2, legacy, tuile, DB | `parcel_p_score_v2.rang` |
| **mult ×N** | fiche V2, tuile, DB | `parcel_p_score_v2.mult_base` |
| **CA (central)** | module faisabilité, fiche legacy | `compute_bilan` (`bilan.ca.central`) |
| **charge foncière (central)** | module faisabilité, fiche legacy | `compute_bilan` (`bilan.charge_fonciere.central`) |
| **prix probable / marge (score_e)** | fiche legacy | `score_e` |
| **mode B dispo** | fiche V2, legacy, endpoint mode-b | `compute_mode_b` |
| **SDP résiduelle** | fiche V2, tuile, DB `parcel_residuel` | `parcel_residuel.sdp_residuelle_m2` |
| **vigilances (SOFT)** | fiche V2 (`lines`), tuile | `dryrun_cascade_results` SOFT_FLAG (+abf/UNKNOWN) |
| **étiquette source/millésime** | présence par surface | doctrine boussole |

**Surfaces = endpoints réels** :
- fiche V2 (premium, ce que le front charge) : `GET /parcels/{idu}?source=q_v8_calibre` (`_q_v2_fiche`)
- fiche legacy (exports, `/parcels` sans source) : `GET /parcels/{idu}` (`_build_fiche` → `verdict_servi`)
- export markdown : `GET /parcels/{idu}/export?format=md`
- one-pager comité : `GET /parcels/{idu}/export?format=onepager`
- bilan/CA : `GET /modules/faisabilite/{idu}`
- mode B : `GET /parcels/{idu}/mode-b`
- carte (tuiles matérialisées) : DB `mvt_parcels`
- vérité de classement : DB `parcel_p_score_v2` (run servi)

**Gravités** (règle du mandat) :
- **G1** contradiction (deux valeurs différentes pour la même grandeur)
- **G2** précision/format (arrondi : écart ≤ 1 % sur un montant, ± 1 m² sur une surface)
- **G3** asymétrie d'information (une surface tait ce qu'une autre montre)
- **G4** étiquette/millésime manquant ou divergent

**Piège latent** : le champ mort `statut`/`status` (matrice_statut v1, éteinte M37) N'EST PAS le
tier. S'il diffère du tier effectif, c'est consigné à part (`pieges_latents.csv`) — pas un G1
client tant qu'aucune surface ne le SERT comme verdict.

## 3. Points méthodo (constatés, pour ne pas produire de faux positifs)

- Le **tier client** suit la règle front `verdictMeta` (étage 0 → `ecartee`, sinon `tier_v2`) —
  comparer le champ brut `statut` produirait de faux G1.
- Les **vigilances client** sont la cascade complète (`lines`), pas le champ partiel `flags`.
- Le **rate-limiting** (60/min) est désactivé pour l'extraction via `LABUSE_DEV_MODE=1` (sinon
  des réponses tronquées « défi » polluent la grille).

**Enchaînement direct sur la Phase 1** (le protocole suit le cadre du mandat — pas de STOP ici).
