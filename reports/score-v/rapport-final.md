# Score V (Vendabilité) — rapport de fin de session

*Branche `feat/labuse-score-v` — barème v1 verrouillé (D1), seuil Brûlante = 50 (D3), run Q×A de référence `q_v2`.*

## 1. Signaux GO/NO-GO

| Signal / famille | Verdict | Détail |
|---|---|---|
| A — BODACC (LJ/RJ/sauvegarde/radiation/cession) | **GO** | 1418 annonces × SIREN cachées (569 SIREN à annonce ≥ 1, familles collective+radiation+vente) |
| B — RNE / recherche-entreprises (cessation, âge, SCI dormante) | **GO** | 9703/9730 SIREN enrichis (état administratif, dirigeants, siège) ; 731 gigognes INPI non résolues (429) sans signal âge |
| C — Détachement géographique | **GO** (via siège recherche-entreprises — pas d'adresse dans DGFiP PM) | |
| D — Dormance (friche, tenure, terrain nu) | **GO partiel** | `DVF_TENURE_12`/`_8` **NO-GO** (millésimes 2014-2020 retirés de la distribution DGFiP) → variante dégradée `DVF_TENURE_OBS5` 8 pts validée au GO Phase 0. Géo-DVF parcelle : 102551 lignes / 37868 parcelles (2021-2025) |
| E — DPE (pression réglementaire, calendrier DOM 2028/2031) | **GO best-effort** | base ADEME 974 intrinsèquement mince : 41 DPE F/G rattachés parcelle |

## 2. Stats matching (liens parcelle ↔ propriétaire)

- Liens DGFiP PM : **82066** — SIREN direct : **71964** (87.7 %), fallback dénomination : **314** (0.4 %).
- Lookups dénomination : 134 résolues, 104 ambiguës, 2412 introuvables.
- **Review queue : 208 lignes** (matchs ambigus, à arbitrer humainement).

## 3. Distribution V + Brûlantes 🔥

| Bande | Parcelles | % |
|---|---|---|
| Signal fort (50-100) | 315 `█` | 0.1 % |
| Signaux présents (25-49) | 11474 `█` | 2.7 % |
| Signal faible (1-24) | 341169 `████████████████████████████████████████` | 79.0 % |
| Aucun signal (0) | 30763 `████` | 7.1 % |
| N.A. (public/bailleur) | 47942 `██████` | 11.1 % |

**Brûlantes = 14** (chaude Q×A ∧ V ≥ 50, vue dynamique `v_parcelles_brulantes`).

⚠ **Garde-fou D3 : 14 Brûlantes hors de l'intervalle [30-120].** Le seuil n'a PAS été changé. **Proposition** (méthode top décile V des chaudes) : `V_BRULANTE_THRESHOLD = 41` → 86 Brûlantes. Décision Vic.

## 4. Coverage & type de propriétaire

- `full` (propriétaire PM matché, 5 familles) : **76040** (17.6 %) ; `partial` (familles D+E) : **355623**.

| owner_type | Parcelles |
|---|---|
| pp | 349597 |
| public | 36463 |
| pm | 33713 |
| bailleur | 11479 |
| copro | 411 |

## 5. Top 20 Brûlantes 🔥

| Parcelle | Commune | Q | A | V | Propriétaire | Signaux |
|---|---|---|---|---|---|---|
| `97414000CV0938` | Saint-Louis | 25 | 56 | **77** | JACKY UNION LUDGE ETHEVE | Liquidation judiciaire en cours · Cessation déclarée / mise en sommeil · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97414000CV0907` | Saint-Louis | 13 | 56 | **77** | JACKY UNION LUDGE ETHEVE | Liquidation judiciaire en cours · Cessation déclarée / mise en sommeil · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97414000CV0912` | Saint-Louis | 48 | 55 | **72** | JACKY UNION LUDGE ETHEVE | Liquidation judiciaire en cours · Cessation déclarée / mise en sommeil · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97411000BL0390` | Saint-Denis | 65 | 66 | **65** | SOCIETE TRANSPORTS MARCHANDISES | Redressement judiciaire en cours · Dirigeant ≥ 75 ans · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97416000ES2071` | Saint-Pierre | 91 | 57 | **61** | MOURGAPA SARL | Liquidation judiciaire en cours · Dirigeant 70–74 ans · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97416000ES2069` | Saint-Pierre | 60 | 55 | **61** | MOURGAPA SARL | Liquidation judiciaire en cours · Dirigeant 70–74 ans · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97411000BL0132` | Saint-Denis | 82 | 66 | **60** | SOCIETE TRANSPORTS MARCHANDISES | Redressement judiciaire en cours · Dirigeant ≥ 75 ans · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97414000EN1937` | Saint-Louis | 66 | 63 | **59** | SCI WYLDA MASCAREIGNES | Liquidation judiciaire en cours · Dirigeant 65–69 ans · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97412000BN0900` | Saint-Joseph | 50 | 64 | **59** | SCI WYLDA | Liquidation judiciaire en cours · Dirigeant 65–69 ans · Aucune mutation sur la fenêtre DVF observable (2021-2025) |
| `97413000CH0229` | Saint-Leu | 69 | 67 | **55** | ORANGE | Dirigeant ≥ 75 ans · Siège hors Réunion (métropole/étranger) · Cession de fonds de commerce < 12 mois |
| `97416000HV0607` | Saint-Pierre | 66 | 68 | **55** | ORANGE | Dirigeant ≥ 75 ans · Siège hors Réunion (métropole/étranger) · Cession de fonds de commerce < 12 mois |
| `97407000AS0156` | Le Port | 65 | 68 | **55** | ORANGE | Dirigeant ≥ 75 ans · Siège hors Réunion (métropole/étranger) · Cession de fonds de commerce < 12 mois |
| `97415000CX0797` | Saint-Paul | 83 | 66 | **52** | BATIPRO | Liquidation judiciaire en cours · Aucune mutation sur la fenêtre DVF observable (2021-2025) · Terrain nu détenu par PM hors construction/immobilier |
| `97412000BV0421` | Saint-Joseph | 84 | 70 | **51** | LITTORAL DE LA VALLEE | Dirigeant ≥ 75 ans · Friche recensée (Cartofriches) · Aucune mutation sur la fenêtre DVF observable (2021-2025) |

## 6. Backtest

Lift top décile : **1.36×** (cible ≥ 2×) — détail complet : [backtest.md](backtest.md) (+ CSV cohorte, graphe SVG).

🔴 **LIFT < 1.5× : poids à retravailler avant tout usage commercial du score.**

## 7. Screenshots (375 / 768 / 1440)

- [carte_badges_v_1440.png](screenshots/carte_badges_v_1440.png)
- [carte_badges_v_375.png](screenshots/carte_badges_v_375.png)
- [carte_badges_v_768.png](screenshots/carte_badges_v_768.png)
- [fiche_panneau_v_1440.png](screenshots/fiche_panneau_v_1440.png)
- [fiche_panneau_v_375.png](screenshots/fiche_panneau_v_375.png)
- [fiche_panneau_v_768.png](screenshots/fiche_panneau_v_768.png)
- [liste_triee_v_1440.png](screenshots/liste_triee_v_1440.png)
- [liste_triee_v_375.png](screenshots/liste_triee_v_375.png)
- [liste_triee_v_768.png](screenshots/liste_triee_v_768.png)

## 8. Caveats & dette (v1.1)

- **DVF 2014-2020 retirés** de la distribution officielle → tenure = fenêtre observable 5 ans (`DVF_TENURE_OBS5`, 8 pts, validé au GO). Un futur mandat data étendra `dvf_mutations_parcelle` (médianes €/m² par secteur) — ne rien jeter.
- **DGFiP PM millésime 2025** : fuite temporelle possible au backtest (l'acheteur peut déjà figurer au fichier) — documentée dans backtest.md.
- **SCI dormante** : proxy `date_mise_a_jour_rne` (pas d'historique d'événements RNE public).
- **731 gigognes INPI** non résolues (quota 429) → pas de signal âge ; reprendre `labuse ingest-inpi-gigogne` un autre jour.
- **Badges V sur carte** : mode commune (GeoJSON) seulement — les tuiles MVT île ne portent pas encore v_score (régénération des tuiles à planifier).
- **Grands groupes nationaux** (ex. ORANGE dans le top Brûlantes : « dirigeant ≥ 75 ans » d'un conseil d'administration + cession d'une boutique) : signaux techniquement exacts mais non pertinents pour un foncier stratégique — filtre catégorie d'entreprise (GE/ETI) à prévoir avec le raffinement D5.
- v1.1 : raffinement PM promoteurs/marchands de biens (D5), diff quotidien BODACC, LOVAC.

---
*Aucun merge effectué — validation visuelle puis merge `--no-ff` par Vic.*