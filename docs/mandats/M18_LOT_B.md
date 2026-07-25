# M18 — LOT B : parcours FLASH (PDF à l'unité, 79 €)

**Branche** `feat/m18-b-flash` (base `main`). Prouvé, **non mergé**. Stripe **hors périmètre** (pages
prêtes au branchement). Tunnel : `/flash` (arrivée) → `/flash?idu=…` (pré-paiement) → Stripe → `/flash/retour`
(« rapport prêt ») → `/flash/telecharger` (PDF).

## RG-FAV
Les pages Flash rendent via `coffre_ui.page()` → favicon LABUSE présent (PNG sur `main` ; le favicon SVG
buse ajouté en LOT A dans le `coffre_ui` partagé s'appliquera partout au merge).

## B1 — Écran d'arrivée plus vendeur
- **Bouton renommé** « Vérifier la parcelle → » → **« Voir ma parcelle → »** *(retenu ; écartés :
  « Analyser ma parcelle », « Préparer mon rapport »)*.
- **Tagline étoffée** « une parcelle · un PDF sourcé · 79 € » → « le dossier complet d'une parcelle, en
  PDF · 79 € » + **bloc valeur** : ce qu'il y a dans le PDF (zonage & règles calibrées, risques, marché
  DVF, permis voisins, potentiel de transformation), chaque donnée **avec sa source et sa fraîcheur**, et
  surtout **« ce que vous n'auriez pas trouvé seul »** (règles PLU traduites, potentiel constructible
  chiffré, signaux croisés — pas une simple fiche cadastrale).

## B2 — Pré-paiement attractif
Recap enrichi (« Dans votre PDF : … avec sa source et son millésime »), **3 lignes de réassurance**
(livré en quelques secondes / ce qu'une fiche cadastrale ne dit pas / paiement unique sans carte chez
LABUSE), prix « 79 € · paiement unique, sans abonnement », bouton **« Payer 79 € et recevoir mon rapport →»**.

## B3 — Post-paiement repensé (« rapport prêt » en vedette)
- La **vedette = « Votre rapport est prêt »** (hero, h1), « paiement reçu » relégué en sous-titre.
- État initial « Votre rapport arrive… · nous assemblons votre PDF » (spinner) → à la génération, coche ✓
  + hero « Votre rapport est prêt ».
- **Bouton PDF proéminent** : gros, rempli mint, ombré/glow (« ↓ Télécharger mon rapport PDF ») — l'action
  saute aux yeux. Unboxing valorisant.

## B4 — Le PDF Flash : inventaire + propositions (arbitrage Vic AVANT ajout)
PDF construit par `flash/report.py` + `flash/data.py` + `templates/rapport.html.j2` (WeasyPrint). HTML de
référence rendu et vérifié (`qa/m18/B/flash_sample.html`, parcelle 97413000CU1068).

### Inventaire des sections actuelles (véridiques, sourcées, traçables)
1. **Couverture** — « Rapport de faisabilité indicative » + adresse/réf. cadastrale + carte de situation + date + version.
2. **Identité parcellaire** — IDU, commune, section/numéro, surface, lat/lon, référence cadastrale.
3. **Constructibilité** — zonage du PLU, **règles calibrées LABUSE** (zone, emprise max, hauteur max, indice de confiance), prescriptions graphiques, potentiel indicatif si bâti, **Verdict + Score LABUSE (scoring v2, grille Q/A)**.
4. **Risques** — aléa Géorisques, PPR (DEAL), mouvement de terrain, cavité, sols pollués (SIS/CASIAS), bruit routier/PEB, trait de côte, 50 pas, **ICPE à proximité**.
5. **Patrimoine & environnement** — Monuments historiques / abords ABF (~500 m), ENS, Parc National, forêt publique, QPV, friche.
6. **Marché** — **comparables DVF récents anonymisés**, dernière mutation de la parcelle, médianes secteur.
7. **Dynamique locale** — permis autour (« plus gros projets autorisés »).
8. **Terrain** — ANC/assainissement, végétation (selon disponibilité).
9. **Sources** — chaque section listée avec **source + millésime** (traçabilité).

### Boussole — vérifié
✅ **Aucune identité de personne physique** dans le PDF : comparables **anonymisés**, aucune mention
nominative (grep « M./Mme/né le/prénom » = vide ; « propriétaire » n'apparaît que dans une note
méthodo générique « cycle de vie du propriétaire »). Cohérent et traçable.

### Propositions d'enrichissement (À ARBITRER par Vic — non ajoutées)
- **Fraîcheur en tête de chaque donnée** : afficher le millésime au plus près de la valeur (pas seulement
  dans la section Sources) — renforce la confiance.
- **Vélocité administrative** de la commune (délai médian d'instruction PC, déjà en base — outil M05) :
  un promoteur veut savoir « combien de temps pour un permis ici ».
- **Rareté du foncier / horizon ZAN** de la commune (outil O9) : contexte de tension foncière.
- **Contexte commune** (SRU/QPV/PLH/marché) déjà partiellement présent — pourrait être synthétisé en
  encadré « leviers » (TVA réduite, LLS) sans exposer de donnée sensible.
- **Solaire / potentiel PV** (parcel_solar) si pertinent pour la destination.
- ⚠ **Ne jamais** ajouter le **propriétaire** (personne physique) — même si la donnée existe en base.
  Personne morale (SCI/société) = à arbitrer, avec prudence RGPD.

## Preuve (`:8060`, `qa/m18/B/prove.mjs`)
B1 « Voir ma parcelle » + valeur étoffée ✓ ; B2 « Dans votre PDF » + réassurance + bouton « recevoir mon
rapport » ✓ ; B3 hero « VOTRE RAPPORT EST PRÊT » + bouton PDF proéminent ✓. Captures `b1_arrivee`,
`b2_prepaiement`, `b3_generation`, `b3_rapport_pret`. Inventaire PDF : `flash_sample.html`.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `:8060`). Zéro touche scoring.

## Décisions ouvertes
- **Libellé du bouton d'entrée Flash** : « Voir ma parcelle » retenu (alternatives consignées).
- **Enrichissement PDF** : liste ci-dessus à arbitrer par Vic avant tout ajout (skill `pdf` pour la mise
  en œuvre). Contrainte ferme : jamais d'identité de personne physique.
- **Stripe** : paiement non branché (hors périmètre) — pages prêtes.
