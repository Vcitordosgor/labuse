# RECETTE-3 — rapport

**Branche** : `feat/recette-3` (depuis `feat/recette-2`). **Worktree** : `~/Desktop/labuse-recette3`.
**Run servi** : `q_v11_m137` (inchangé — aucun rescoring, aucune bascule). **Aucun merge.**
**Règle de preuve** : chaque « corrigé » a été constaté dans un vrai navigateur (Playwright) contre le
backend réel (uvicorn :8021 + front vite :5176). Preuves visuelles : `RECETTE-3-preuves/`.

## Étape 0
`pwd` = worktree · branche `feat/recette-3` · arbre propre · `.env` présent (DB `labuse` locale).
Mandat + maquette validée archivés dans le dépôt : `MANDAT-RECETTE-3.md`, `maquette-apporteur-v3.html`.

---

## Tableau des 14 points

| # | Point | État | Constaté au navigateur | Preuve |
|---|-------|------|------------------------|--------|
| **T1** | Brief apporteur — version validée (maquette v3) | ✅ Fait | Page 1 : **un seul bandeau** (confidentiel + non-mandat fusionnés) ; **plan de situation** ortho réel (contour parcelle mint + voisines) ; ligne **« À côté »** (voisines même propriétaire, Blocs fonciers, réf. CW 1036/0662/…) ; **« Dernière vente »** datée+chiffrée (février 2021 …), omise si inconnue (S8) ; « à jour du GPU »/« plomberie » **absents du brief** (vérifiés inexistants). Pages 2-4 : **contact en 1re question** (L'ESSENTIEL), **3 questions « l'essentiel »** (contact + prix + bail/voisines), photos **par message en citant la référence** (« n'imprimez rien »), une phrase sous chaque section. | `apporteur_p1.png`, `apporteur_q.png`, `apporteur_photos.png` · `tests/test_exports2_lot6.py` (13) |
| **T2** | Supprimer le document Résumé | ✅ Fait | `/resume/{idu}.pdf` → **404** ; dossier/financier/apporteur → 200 ; `/parcels/{idu}/export.pdf` → **308 → /dossier** (repointé, ex-cible /resume). Bloc, route, bouton front, proxy, préfixe numéro, tests : retirés. Aucun autre document ne dépendait du bloc (`api/resume.py` métier conservé, distinct). | curl routes (404/200/308) · `test_exports2_lot1`, `test_non_contradiction` MAJ |
| **T3** | Tri par défaut du listing factuel | ✅ Fait | Défaut factuel = **« Potentiel »** (adressées d'abord → SDP résiduelle → surface), pill Surface conservée. Top des lignes **toutes adressées**, réparties (Saint-Paul, Sainte-Marie, Le Tampon, Saint-Pierre…) — fini les emprises géantes sans adresse. Justification mesurée ci-dessous. | `T3_factuel_potentiel.png` · perf 0,87 s |
| **T4** | Segmentation du listing d'analyse | ✅ Fait | 4 segments **repliables**, ordre fixe, **compteurs exacts** servis par `/filtre` : **Un professionnel a déposé un permis 518** · Terrain nu constructible 67 016 · Bâti à densifier 109 855 · Le reste 108 392. Chaque carte garde son palier (chips Priorité/…). Chevrons togglent (repli vérifié). | `T4_segments.png` |
| **T5** | Servitudes de Pièges et risques (kinds manquants) | ✅ Fait | 6 couches remontées et décodées sur parcelles témoins : **DPU** (« la commune peut se substituer à l'acquéreur »), **DPF** ravines/reculs (« Bras des Chevrettes — marge de recul »), **Zone humide**, **Espace naturel protégé** (« Etang de Saint-Paul »), **PEB remis** (aérodrome Roland Garros), **EBC** (« inconstructible ») + **ER** (« terrain grevé — préemption/expropriation ») via `plu_gpu_prescription` (filtré aux typepsc 01/05). PEB retiré du « non couvert ». | fetch `/servitudes-invisibles/{idu}` sur 7 parcelles · `test_servitudes.py` (14) |
| **T6** | Message IA — crédits Anthropic épuisés | ✅ Fait (déjà conforme) | Texte servi au client (copilote) : « … solde de crédits Anthropic épuisé … (recharger le compte / facturation). Ce n'est pas passager … Inutile de réessayer dans l'immédiat … ». **Ne dit plus « réessayez dans un instant »** et **dit quoi faire**. Cas « plus de crédits » = structurel (core.py:86 → answering.py). | preuve déterministe (simulation BadRequestError 400 « credit balance ») |
| T7 | Tableau des 22 sources | ⏳ Lot 2 | — | — |
| T8 | Les orphelines | ⏳ Lot 2 | — | — |
| T9 | Les trois surfaces à couvrir | ⏳ Lot 2 | — | — |
| T10 | Rendre compte et s'arrêter | ⏳ Lot 2 | — | — |
| T11 | Financier de bout en bout (S2/S3) | ⛔ Lot 3 — hors périmètre de cette session | — | — |
| T12 | Courrier propriétaire sans champ vide | ⛔ Lot 3 | — | — |
| T13 | Points RECETTE-2 « à recetter à l'œil » | ⛔ Lot 3 | — | — |
| T14 | Maquette apporteur archivée | ✅ Fait (anticipé) | `maquette-apporteur-v3.html` archivée à côté de ce rapport (référence T1). | dépôt |

> La session livre **Lot 1 (T1-T6)** puis **Lot 2 (T7-T10, lecture seule)** et **s'arrête**. Lot 3 (T11-T14) n'est pas traité.

---

## T3 — justification du tri (mesure sur les 30 premières lignes)

Périmètre : univers d'analyse servi `q_v11_m137`, hors étage 0, surface ≥ 2 m² (le listing factuel).

| Tri candidat | avec adresse /30 | avec potentiel (SDP>0) /30 | communes | surface moyenne |
|---|---|---|---|---|
| **A. Surface ↓ (ancien défaut)** | 16 | 4 | 8 | **253 568 m²** (≈ 25 ha, max 96 ha) |
| B. Commune (alphabétique) | 20 | 5 | **1** (une seule commune) | 25 780 m² |
| C. Potentiel seul (SDP ↓) | 24 | 30 | 9 | 90 187 m² |
| **D. Retenu — adresse puis SDP puis surface** | **30** | **30** | **10** | 75 149 m² |

Le tri **A** remonte des emprises géantes **sans adresse et à SDP nulle** (ex. `97416000CR1231`, 96 ha,
0 plancher restant) — inutiles pour un promoteur ou un agent. **B** entasse tout dans une commune
arbitraire. **D** (« Potentiel ») met **toutes les lignes adressées d'abord**, puis celles où il **reste
le plus de plancher à bâtir** : 30/30 adressées, 30/30 avec potentiel réel, sur 10 communes. C'est
celui qui sert le mieux. Coût mesuré : **0,87 s** sur l'île (< budget 1,5 s). Clé serveur `potentiel`
(`_Q_V2_ORDERS`), défaut du mode factuel côté front (`ResultsSection`), tri client identique en mode commune.

## T4 — le signal « un professionnel a déposé un permis »

C'est **exactement** le feature q_v14 `pc_pm_sur_parcelle_pp_36m` : un permis de construire à
pétitionnaire **SIREN** (professionnel) autorisé dans les **36 mois**, **sur une parcelle de personne
physique** (`owner_type = pp`). Live dans l'univers servi : **518** parcelles (le « ~88 » du mandat était
le sous-ensemble monté en *Priorité* par q_v14, pas la taille du segment). Le signal est calculé au vol
(Sitadel), exposé au listing île (`_q_v2_list`) et à la carte commune (geojson), gardé si les tables
Sitadel existent (sinon `permis_pro=False`, jamais une 500). Les compteurs des 4 segments sont servis
exacts par `/filtre` (`_q_v2_stats.segments`, hors étage 0) — leur somme = 285 781 = l'univers retenu.

## T5 — couches ajoutées à `_KINDS` (toutes peuplées en base, vérifié)

`dpu` (202) · `dpf` (281) · `zone_humide` (3 122) · `ens` (84) · `plu_gpu_prescription` (10 490, filtré
EBC/ER = typepsc 01/05) · `peb` (4, aérodrome Roland Garros). Le PEB avait été retiré à M137-T quand la
couche était **vide** ; elle est **peuplée depuis** → remis dans `_KINDS` et sorti du « non couvert »
(règle anti-« couvert-vide » respectée : on ne déclare que des couches réellement peuplées).

## Tests
- Backend (zones touchées) : `test_servitudes` 14, `test_exports2_lot6` 13, `test_exports2_lot1`,
  `test_exports2_lot4`, `test_api`, `test_p_v2_api`, `test_m45_filtres`, `test_filtres_cumul`,
  `test_etage0_filtre_dur`, `test_signaux_vie`, `test_retours14/16_carte` — **verts** (≈ 125 tests).
- Front : `tsc -b` propre · `vitest run` **198/198**.
- Routes documents contre backend réel : /resume 404 · dossier/financier/apporteur 200 · export.pdf 308→/dossier.

*Suite du rapport : Lot 2 (tableau des 22 sources) ci-dessous, après commit du Lot 1.*
