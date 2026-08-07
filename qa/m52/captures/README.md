# M52 · L1 — captures écran réel (avant / après)

Lisibilité du score, carte VERDICT de la fiche parcelle. **Présentation seule — 0 tier,
0 changement de calcul.** Tout chiffre affiché vient d'un calcul existant (`parcel_p_score_v2`,
run servi `q_v8_calibre`).

## Méthode

- **Avant** = commit parent `7c7cb61c` (maquette P0, front encore sans L1).
- **Après** = `046ab315` (L1 livré).
- Pour chaque état : `npm run build` du front réel → API dev `LABUSE_DEV_MODE=1` sur :8000
  (sert la fiche premium `?source=q_v8_calibre`) → Playwright (`capture.mjs`) ouvre la fiche
  via l'omnibox (IDU → loupe) et capture la carte `[data-verdict-card]` + le panneau `aside`.
- Rendu 2×, viewport 1480×1000. Navigateur : chromium headless-shell 1228 du cache
  (`executablePath` explicite — Playwright 1.62 ne fournit plus de build pour Darwin 22 arm64).

## 3 parcelles réelles

| IDU | commune | tier | ×N | rang | percentile |
|-----|---------|------|-----|------|-----------|
| `97418000AT2379` | Sainte-Marie | brûlante | ×22,1 | 7 | 100,0 |
| `97416000EY1406` | Saint-Pierre | déclassée — bâti révélé | ×13,2 | 20 | 100,0 |
| `97416000IL0307` | Saint-Pierre | écartée | ×1,3 | 44245 | 89,67 |

## Ce que L1 ajoute (visible avant→après)

- **Vocab** : « plus probable **de muter** » → « plus probable **d'être vendue** ».
- **Mot d'échelle** sous le ×N (bandes de ×N) : « très forte probabilité relative » /
  « proche de la moyenne ». + **ⓘ** (définition : probabilité *relative*, backtest DVF, ni
  garantie ni prix).
- **Réglette** de position (percentile) — SANS note /100, SANS étoiles (doctrine).
- **Fréquence mesurée par tier**, source DITE à l'écran (« ~20 sur 100 vendues en 2 ans
  contre ~1,5 » + ⓘ « ventes de l'année en cours pas encore toutes publiées », honnêteté M38).
  Affichée seulement pour les tiers fiables (gate-IC) → absente sur déclassée/écartée.
- **« Pourquoi ce score »** : top-5 contributions traduites en FR ; déplié d'office
  brûlante/chaude, replié sinon.

## Fichiers

`L1_{avant,apres}_{brulante_AT2379,declasseB_EY1406,ecartee_IL0307}__{verdict,panel}.png`
(6 avant + 6 après). Script : `capture.mjs`.

## Corrections L1 validées par Vic (repliées dans le geste L2)

L1 validé sur brûlante + écartée. Deux corrections appliquées, re-capturées
`L1_apres_L1corr_*` :

1. **Déclassée/écartée à signal fort (EY1406) — cadrage « signal brut ».** « Déclassée » +
   « très forte probabilité relative » côte à côte = contradiction famille M48 (statut mort
   à côté d'une promesse). Corrigé : hors tiers servables (`verdict.tier == null`) ET ×N ≥ 2,
   le ×N devient **« signal brut »** (teinte terre éteinte), le mot passe **atténué** avec
   « · écartée », et un encadré dit « la parcelle porte un signal fort (×N) **mais elle est
   écartée** : [motif] — l'écartement prime. La fréquence par tier ne s'affiche pas. » + ⓘ
   doctrine étage 0 (M5). « Pourquoi ce signal (avant l'écart) » ouvert. La fréquence reste
   absente (correct). L'écartée simple ×1,3 (< 2) NE déclenche PAS ce cadrage — reste sobre.

2. **Réglette sur ×N (échelle LOG), plus le percentile rang.** Le percentile rang plaçait
   l'écartée ×1,3 à ~89,7 % (« très forte ») car mieux classée que ~90 % des parcelles —
   contradiction avec « proche de la moyenne ». Corrigé : `verbal.reglette_pct` =
   log10(×N / 1) / log10(25 / 1) × 100, bornée [1, 99], ancres en config
   (`echelle_verbale_score.yaml` → `reglette`). Résultat : IL0307 ×1,3 → **8,6 %** (près de
   « moyenne ») ; EY1406 ×13,2 → 80,0 % ; AT2379 ×22,1 → 96,2 %.

## L2 — Hiérarchie

Ordre des tuiles réordonné à la séquence de décision promoteur. **Preuve = dump DOM réel**
`L2_ordre_tuiles.txt` (+ panneaux `L2_apres_*__panel.png`) :

- **Servable (brûlante)** : ① VERDICT (en tête, hors scroll) → théâtre → ② droit du sol
  (`regles`, **ouvert**) → ③ économie (`faisabilite` **ouvert**, marché/viabilisation repliés)
  → ④ contexte (historique + voisinage, sorti de `regles`) → ⑤ propriété → ⑥ risques →
  [pourquoi pas] → ⑧ **Les données** (`confiance`). ⑦ outils = barre d'actions en pied.
- **Déclassée à signal fort (EY1406)** : le **Mode B remonte en 2** (juste après le verdict),
  **ouvert** ; le reste replié.
- **Écartée simple (IL0307)** : seul le verdict est ouvert ; toutes les tuiles repliées.

Détails L2 : `états dépliés` pilotés par `servable` (tier servable) et `signalEcarte` ;
théâtre « **431 663 parcelles analysées** » (compte GELÉ `p_score_v2_runs.n_parcelles`, jamais
un COUNT par fiche, jamais inventé) — s'incrémente 0→N en ~700 ms puis fige, une ligne sobre.
**Nuance assumée** : les « outils » (⑦) restent la barre d'actions de pied (CTA persistants
pipeline/projet/PDF/annuaire) — placés APRÈS « Les données » plutôt qu'avant, pour ne pas
enterrer les CTA. L'ordre des tuiles de CONTENU respecte la séquence validée.

## L3 — « Les données » (fin de fiche)

Le dernier tiroir devient **« Les données »** (`L3_apres_*__confiance.png`) :
- **Sources utilisées sur cette fiche** = distinct RÉEL des couches cascade jointes à
  `data_sources` (nom · fournisseur · millésime · fiabilité). Backend `_data_sources_fiche`
  (requête begin_nested). Millésime affiché seulement si date propre (AAAA/AAAA-MM) — les
  notes longues (GPU) cassaient la ligne, retirées.
- **Données absentes** — DITES, jamais approximées, dérivées de nuls RÉELS : « Année de
  construction — non disponible en open data (ABSENTE) » (universel) ; « Adresse postale »
  si non rattachée ; « Identité du propriétaire » si personne physique. Dynamique par parcelle.
- ICD + score P « pourquoi » conservés dessous. **Zéro nouvelle donnée.**

## L4 — Qualité par commune, DITE

Mesure réelle GELÉE : `config/qualite_commune.yaml` (généré depuis `qa/audit-rr/b_commune_rr.md`,
fold 2025 OOS). Backend `_qualite_commune` sur l'INSEE de la parcelle → RR intra, échantillon,
drapeau « fragile » (<5 positifs), phrase honnête.
- **Encart** dans « Les données » (`L3_apres_brulante_AT2379__confiance.png`) : « QUALITÉ DE LA
  MESURE · Sainte-Marie / échantillon limité / RR intra 6,7 · île 6,73 / 16 646 parcelles /
  base 1,32 % » + phrase. Saint-Pierre : « robuste » (RR 9,3, n 42 045).
- **Rappel discret en fiche parcelle** quand `degradee` (`L4_apres_brulante_AT2379__panel.png`) :
  « ◐ Sainte-Marie : marché peu actif — le classement reste fiable, la fréquence exacte est
  indicative (échantillon limité) ». N'apparaît PAS sur une commune robuste (Saint-Pierre).
- Ajouté aussi à `/communes/{c}/contexte` (`qualite`) pour l'encart fiche commune.
- Mesure SEULE : aucun tier, aucun seuil, aucun modèle.

## L5 — Vues sauvegardées (reste M45)

Contrôle **« Mes vues »** dans la barre de filtres (`L5_apres_mes_vues.png` +
`…_rename.png`) : nom + combinaison de filtres courante, **stockage côté compte**
(`saved_searches`, compte-scopé, jamais partagé). **Appliquer** (clic sur le nom →
`filtersFromHash` → setFilters/setZone) · **renommer** (✎, inline) · **supprimer** (×).
Backend : `PATCH /events/searches/{id}` ajouté (SEC-IDOR compte-scopé) ; réutilise
save/list/delete existants. CRUD vérifié bout-à-bout (save→list→rename→delete). **Une vue
nommée EST aussi une veille** (même objet `saved_searches`) — unifié, pas dupliqué.
