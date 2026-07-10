# Score V (Vendabilité) — rapport de fin de session

*Branche `feat/labuse-score-v` — barème v1 verrouillé (D1), seuil Brûlante = 34 (D3), run Q×A de référence `q_v2`.*

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
| Signal fort (50-100) | 169 `█` | 0.0 % |
| Signaux présents (25-49) | 8880 `█` | 2.1 % |
| Signal faible (1-24) | 10958 `█` | 2.5 % |
| Aucun signal (0) | 363714 `████████████████████████████████████████` | 84.3 % |
| N.A. (public/bailleur) | 47942 `█████` | 11.1 % |

**Brûlantes = 93** (chaude Q×A ∧ V ≥ 34, vue dynamique `v_parcelles_brulantes`).

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
| `97414000CV0938` | Saint-Louis | 25 | 56 | **77** | JACKY UNION LUDGE ETHEVE | Liquidation judiciaire en cours · Cessation déclarée / mise en sommeil · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97414000CV0907` | Saint-Louis | 13 | 56 | **77** | JACKY UNION LUDGE ETHEVE | Liquidation judiciaire en cours · Cessation déclarée / mise en sommeil · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97414000CV0912` | Saint-Louis | 48 | 55 | **72** | JACKY UNION LUDGE ETHEVE | Liquidation judiciaire en cours · Cessation déclarée / mise en sommeil · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97411000BL0390` | Saint-Denis | 65 | 66 | **65** | SOCIETE TRANSPORTS MARCHANDISES | Redressement judiciaire en cours · Dirigeant ≥ 75 ans · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97416000ES2071` | Saint-Pierre | 91 | 57 | **61** | MOURGAPA SARL | Liquidation judiciaire en cours · Dirigeant 70–74 ans · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97416000ES2069` | Saint-Pierre | 60 | 55 | **61** | MOURGAPA SARL | Liquidation judiciaire en cours · Dirigeant 70–74 ans · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97411000BL0132` | Saint-Denis | 82 | 66 | **60** | SOCIETE TRANSPORTS MARCHANDISES | Redressement judiciaire en cours · Dirigeant ≥ 75 ans · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97414000EN1937` | Saint-Louis | 66 | 63 | **59** | SCI WYLDA MASCAREIGNES | Liquidation judiciaire en cours · Dirigeant 65–69 ans · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97412000BN0900` | Saint-Joseph | 50 | 64 | **59** | SCI WYLDA | Liquidation judiciaire en cours · Dirigeant 65–69 ans · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97415000CX0797` | Saint-Paul | 83 | 66 | **52** | BATIPRO | Liquidation judiciaire en cours · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux · Terrain nu détenu par PM hors construction/immobilier |
| `97412000BV0421` | Saint-Joseph | 84 | 70 | **51** | LITTORAL DE LA VALLEE | Dirigeant ≥ 75 ans · Friche recensée (Cartofriches) · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97416000CS1391` | Saint-Pierre | 44 | 58 | **50** | DERECA | Liquidation judiciaire en cours · Siège hors Réunion (métropole/étranger) |
| `97413000DC0543` | Saint-Leu | 93 | 69 | **47** | SCI DU SUD OUEST 974 | Radiation < 36 mois · Dirigeant ≥ 75 ans |
| `97416000CR0616` | Saint-Pierre | 79 | 50 | **47** | CEDRES PROMOTION | Liquidation judiciaire en cours · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux · Siège Réunion, autre commune que la parcelle |
| `97416000CR0605` | Saint-Pierre | 73 | 50 | **47** | CEDRES PROMOTION | Liquidation judiciaire en cours · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux · Siège Réunion, autre commune que la parcelle |
| `97413000DC0561` | Saint-Leu | 71 | 68 | **47** | SCI DU SUD OUEST 974 | Radiation < 36 mois · Dirigeant ≥ 75 ans |
| `97413000DC0542` | Saint-Leu | 66 | 68 | **47** | SCI DU SUD OUEST 974 | Radiation < 36 mois · Dirigeant ≥ 75 ans |
| `97416000IM0019` | Saint-Pierre | 93 | 69 | **45** | PROMOTION CREATION D ENTREPRISES TRIPOLI | Dirigeant ≥ 75 ans · Siège hors Réunion (métropole/étranger) · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97422000AH0351` | Le Tampon | 84 | 64 | **45** | CARRARE | Dirigeant ≥ 75 ans · Siège hors Réunion (métropole/étranger) · Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux |
| `97415000AB0369` | Saint-Paul | 69 | 61 | **45** | PLDC  PLATEFORME LOGISTIQUE DE CORNU | Dirigeant 70–74 ans · Friche recensée (Cartofriches) · Terrain nu détenu par PM hors construction/immobilier |

## 6. Backtest

Lift top décile : **1.41×** (cible ≥ 2×) — détail complet : [backtest.md](backtest.md) (+ CSV cohorte, graphe SVG).

🔴 **LIFT < 1.5× : poids à retravailler avant tout usage commercial du score.**

## 6bis. Comparatif v1 → v1.1

*v1.1 = tenure conditionnelle (jamais seule) + malus achat récent neutralisé + filtre grands groupes GE/ETI (familles B/C) + seuil Brûlante re-dérivé (top décile V des chaudes).*

| Métrique | v1 | v1.1 |
|---|---|---|
| Lift top décile | 1.36× | **1.41×** |
| Lift bande V ≥ 50 (fort) | 0.64× (n=54) | **0.83×** (n=30) |
| Lift bande V 25-49 (présents) | 1.01× (n=2342) | **1.02×** (n=1692) |
| Lift bande V 9-24 | 2.13× (n=3298) | **2.26×** (n=3019) |
| Lift bande V = 8 (tenure seule) | 0.89× (n=81217) | **0.83×** (n=6) |
| Lift bande V 0-7 | 2.04× (n=4880) | **0.96×** (n=87044) |
| Brûlantes 🔥 | 14 (seuil 50, garde-fou déclenché) | **93** (seuil 34 = top décile V des chaudes) |
| Distribution « fort » | 315 | **169** |
| Distribution « présents » | 11474 | **8880** |
| Distribution « faible » | 341169 | **10958** |
| Distribution « aucun » | 30763 | **363714** |
| Distribution « N.A. » | 47942 | **47942** |
| Top Brûlantes v1 conservées dans le top 20 v1.1 | — | **11/14** (les 3 parcelles ORANGE sortent : filtre grands groupes) |

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