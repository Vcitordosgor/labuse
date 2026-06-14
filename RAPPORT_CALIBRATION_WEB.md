# RAPPORT — Calibration WEB du bilan promoteur (socle de démarrage sourcé)

> Objectif : faire disparaître le bandeau « non fiable » en pré-remplissant les paramètres du bilan
> (1.C) avec des valeurs **réelles trouvées en ligne**, chacune **sourcée** ou **estimée**. Socle de
> DÉPART défendable — **à affiner avec un promoteur**. Recherche du **2026-06-14**.
>
> Injection : table `bilan_params`, secteur global `*`, colonne `provenance` (`sourcee`/`estimee`),
> `is_placeholder=false`. Idempotent et **non destructif** (`ON CONFLICT DO NOTHING` → un override
> saisi par Vic n'est jamais écrasé). Code : `faisabilite/bilan_calibration.py`.

## Tableau des valeurs retenues

| Paramètre | Valeur | Provenance | Source (URL) · date | Raisonnement |
|---|---|---|---|---|
| `prix_m2_neuf` | **4 900 €/m²** | sourcée | [consortium-immobilier · Saint-Paul](https://www.consortium-immobilier.fr/prix/saint-paul-97460.html) (neuf 2024 ≈ 4 922 €/m²) ; corroboré [SeLoger](https://www.seloger.com/prix-de-l-immo/vente/departements-d-outre-mer/la-reunion/saint-paul/974415.htm) / [PAP](https://www.pap.fr/vendeur/prix-m2/saint-paul-974-g53014) (appart. ancien ~5 200 €/m²) | Prix neuf appartement Saint-Paul 2024 ≈ 4 922 €/m² (était 5 582 en 2023). Programmes réels jusqu'à 6 627 €/m² (balnéaire). Retenu **4 900** (moyenne commune). ⚠ **À différencier par secteur** (balnéaire Saint-Gilles/Cap ↑ ~5 800, Hauts ↓ ~3 800). |
| `cout_construction_m2_sdp` | **2 100 €/m² SDP** | estimée ★ | [Banque des Territoires Éclairages n°33](https://www.banquedesterritoires.fr/sites/default/files/2025-01/Exe%20brochure%20Eclairages%2033%20A4%202024%20vdef.pdf) (prix de revient social 2 300→2 550 €/m² SU, national, **tout compris**) ; collectif métropole **bâti seul** 1 340–1 480 €/m² ([plan-immobilier](https://www.plan-immobilier.fr/actualites-immobilieres/une-baisse-des-prix-de-vente-dans-la-construction-neuve), [rénovation-et-travaux](https://www.renovationettravaux.fr/cout-construction-immeuble)) | Le param = **construction seule** (le foncier est la sortie). Métropole collectif standard 1 340–1 480 + **surcoût DOM** (transport matériaux, normes parasismiques/cycloniques, +25–40 %) → ~1 700–2 050 ; aligné à la fourchette prudente YAML (1 800–2 200). Retenu **2 100**. **★ paramètre à affiner en priorité** (pas de publication directe « collectif bâti Réunion »). |
| `prix_m2_lls` | **2 900 €/m²** | estimée | dérivé du prix de revient social DOM ([Banque des Territoires Éclairages n°33](https://www.banquedesterritoires.fr/sites/default/files/2025-01/Exe%20brochure%20Eclairages%2033%20A4%202024%20vdef.pdf), ~2 550 €/m² SU) ; jeu [Région ODS — coût logements sociaux Réunion](https://data.regionreunion.com/explore/dataset/financement-et-cout-des-logements-sociaux-construits-a-la-reunion/) | Prix de cession VEFA→bailleur ~ prix de revient social + petite marge. Retenu **2 900**. À confirmer sur les conventions bailleurs (SHLMR/SODEGIS/SEMADER). |
| `marge_cible_pct` | **16 % du CA** | estimée ★ | [crédit mutuel](https://www.creditmutuel-immobilier.fr/fr/actualites/quelle-est-la-marge-d-un-promoteur-immobilier.html), [modelesdebusinessplan](https://modelesdebusinessplan.com/blogs/infos/marge-promoteur-immobilier) | Marge **brute** 20–40 % du CA, **nette** 7–15 % après frais de structure. La marge-cible du bilan = marge retenue (les honoraires sont séparés) → cible brute conservatrice **16 %**. **★ à affiner** (sensibilité forte). |
| `honoraires_pct` | **12 % du CA** | estimée | [coût construction collectif](https://www.renovationettravaux.fr/cout-construction-immeuble) (archi 7–15 %, BET/contrôle/DO 2–3 % chacun) | Honoraires techniques + commercialisation (~5–6 % du CA) regroupés ≈ **12 % du CA**. Standard métier. |
| `frais_financiers_pct` | **3 % du CA** | estimée | ordre de grandeur portage promoteur (taux crédit 2026) | Coût de portage (crédit + GFA) ~2–4 % du CA selon durée/taux. Retenu **3 %**. |
| `cout_vrd_base` | **90 €/m² terrain** | estimée | ordre de grandeur VRD collectif | Voirie + réseaux divers de base ~50–120 €/m² terrain. Retenu **90**. |
| `majoration_vrd_pente_pct` | **30 %** | estimée | lien 2.A (pente) | Surcoût terrassement/soutènement pente forte ~+20–40 %. |
| `majoration_vrd_assainissement_pct` | **25 %** | estimée | lien 2.E (assainissement autonome) | Surcoût filière autonome (dispersion, perméabilité) ~+15–30 %. |
| `ratio_vendable` | **0,80** | estimée | standard promotion | SDP brute → habitable vendable (murs, communs, circulations déduits) 0,78–0,85. |
| `bonus_vue_mer_pct` | **15 %** | estimée | lien 2.B (vue mer) | Prime vue mer dégagée balnéaire ~+10–25 %. |

## Ventilation du prix neuf PAR SECTEUR (bassins PLU existants)

Découpage = les **bassins PLU déjà dans l'app** (override par secteur, résolution défaut ← global ←
secteur). Aucun découpage inventé. Chaque prix est sourcé sur un observatoire du quartier ; un
secteur non couvert retombe sur le **socle commun 4 900 €/m²**.

| Bassin PLU | Prix neuf retenu | Provenance | Source (URL) · date | Solidité · note |
|---|---|---|---|---|
| **Saint-Gilles** (U2*) | **5 800 €/m²** | sourcée | [SeLoger 974455](https://www.seloger.com/prix-de-l-immo/vente/departements-d-outre-mer/la-reunion/saint-gilles-les-bains/974455.htm) — médiane appart **6 029 €/m²** (11/2025) | 🟢 **solide** (balnéaire, marché actif). Retenu sous la médiane (la médiane inclut le front de mer ultra-premium). |
| **La Saline** (U5*) | **6 000 €/m²** | sourcée | [immo-diffusion 97434](https://www.immo-diffusion.fr/fr/dom-tom/la-reunion/97434/estimation-prixm2-la-saline-les-bains) — moy. appart **6 632 €/m²** (10/2025) ; [Superimmo](https://www.superimmo.com/prix-immobilier/dom-tom/la-reunion/saint-paul-97411/la-saline-les-bains-97434) | 🟢 **solide** (balnéaire l'Hermitage/Saline). Conservateur sous la moyenne. |
| **Plateau Caillou** (U3*) | **3 500 €/m²** | sourcée | [SeLoger 974436](https://www.seloger.com/prix-de-l-immo/vente/departements-d-outre-mer/la-reunion/plateau-caillou/974436.htm) — moy. appart **3 417 €/m²** (11/2025) | 🟢 **solide** (intérieur). Léger premium neuf. |
| **La Plaine-Bois de Nèfles** (U4*) | **3 400 €/m²** | sourcée | [consortium 97411](https://www.consortium-immobilier.fr/prix/bois-de-nefles-saint-paul-97411.html) ; [SeLoger 974440](https://www.seloger.com/prix-de-l-immo/vente/departements-d-outre-mer/la-reunion/bois-de-nefles-saint-paul/974440.htm) — appart **~3 100-3 700 €/m²** (2025) | 🟡 **moyen** (Hauts, peu de collectif). |
| **Le Guillaume** (U…) | **3 900 €/m²** | **estimée — à affiner** | [av-transaction 97423](https://av-transaction.immo/estimation/la-reunion-04/la-reunion-974/saint-paul-97423/) — appart 5 284 €/m² **mais maison 3 973 €/m²** (12/2025) | 🔴 **fragile** : échantillon **appartement non fiable** (Hauts à dominante maisons). Retenu ~niveau maison ; **à confirmer**. |
| **Saint-Paul Centre** (U1*) | *4 900 €/m²* (socle commun) | sourcée | [consortium 97460](https://www.consortium-immobilier.fr/prix/saint-paul-97460.html) — neuf 2024 **4 922 €/m²** | 🟢 **solide**. Couvert par le socle commun (pas d'override séparé). |
| *multi / hors-U* | *4 900 €/m²* (fallback) | — | — | Zones sans bassin unique → socle commun. |

**Couverture du référentiel (3 000 parcelles)** : concentré sur **Saint-Paul Centre (2 497)** et
**Le Guillaume (198)** ; les bassins balnéaires (Saint-Gilles, La Saline) et Plateau Caillou ont peu
ou pas de parcelles dans le référentiel actuel — leur override est en place et **se déclenchera** dès
qu'une parcelle de ces bassins est auditée/ingérée. Recette `pytest tests/test_calibration.py` :
résolution par secteur + fallback commun vérifiés.

## Effet sur le bandeau
- **Hard « non fiable »** (`uncalibrated_critical`) : levé — le seul paramètre **critique** (`cout_construction_m2_sdp`) a désormais une valeur. Recette vérifiée sur 3 parcelles Saint-Paul (`97415000BO0845`, `BV1431`, `BV0912`) → **« non_fiable : AUCUN »**, prix de sortie **fiable**, charge foncière chiffrée.
- **Soft « à affiner »** (`estimated_to_refine`) : sous-bandeau info présent → « Coût de construction, Marge cible promoteur » (les deux paramètres estimés les plus sensibles).

## ⚠ Paramètres à affiner EN PRIORITÉ avec un vrai promoteur
1. **`cout_construction_m2_sdp`** (coût bâti collectif réel Réunion) — aucune publication directe ; impact n°1 sur la charge foncière. *Question promoteur : « ton coût de construction au m² SDP, collectif R+3/R+4, à Saint-Paul, hors foncier ? »*
2. **`marge_cible_pct`** (marge réellement visée selon le risque opération).
3. **`prix_m2_neuf` PAR SECTEUR** — la valeur unique 4 900 € sous-évalue le balnéaire (Saint-Gilles/Cap) et surévalue les Hauts ; à ventiler via les overrides de secteur (bassins PLU) déjà en place.

## Non trouvés / laissés en l'état
Aucun paramètre n'est resté « non calibré » : tous ont au moins un ordre de grandeur sourcé ou
estimé. Les valeurs `estimée` restent **visibles comme « indicatif »** dans le panneau de calibration
(badge gris) ; les `sourcée` portent un badge vert. Vic peut tout écraser par secteur en session terrain.
