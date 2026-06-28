# LABUSE — Quick wins UI/UX premium (5 corrections)

> Application des **5 corrections prioritaires** de l'audit UI/UX, sans refonte lourde, sans toucher
> DB / scoring / verdicts / données métier. Frontend uniquement. Rédigé le 2026-06-28 sur `be82805`.
> DB métier vérifiée inchangée (`431663 / 9103 / parcel_enrichment 27`). QA verte, 0 erreur console.

## Corrections faites (5/5)

| # | Correction | Avant | Après |
|---|---|---|---|
| **1** | Empty-state commune non évaluée | « Vos filtres masquent les 4 160 parcelles » + CTA « Réinitialiser les filtres / Afficher toutes » (inopérants) | **« Commune non encore évaluée »** + explication « recalcul prévu » + **un seul** bouton **« Choisir une commune »** (CTA filtres morts retirés) |
| **2** | Contraste « à creuser » sur fond sombre | brun `#C88422`, opacité 0,18 → quasi invisible (Cilaos) | **orange `#E59A3C`**, opacité 0,34 → **clairement lisible** (sémantique inchangée : toujours « à creuser », Opportunité reste le héros) |
| **3** | Bloc décisionnel en tête de fiche | Radar Mutation **tout en bas** (après la longue synthèse IA) | Radar **remonté juste sous l'essentiel** (verdict + score + contrainte + action) → **verdict 63 / Radar 100 côte à côte en tête** : les 2 axes compris en 5 s |
| **4** | Actions rapides compactes / shortlist | « Actions rapides » en grille 2×2 (4 cartes) → shortlist sous la ligne de flottaison | **3 cartes en 1 rangée compacte** (desktop) → shortlist **remontée d'~80 px** : ~3,5 sujets visibles au-dessus du fold (vs ~1,5). Mobile/tablette : 2 colonnes conservées |
| **5** | Wording « dev/démo » | « Démo guidée · 8 cas » (carte + bouton 🎬), « Analyse IA enrichie… (clé API côté serveur) » | « Démo guidée » **retirée** ; jargon → **« analyse assistée sécurisée »** |

## Vérifications (QA Playwright)

- #1 : `title = "Commune non encore évaluée"`, `hasPickCommune = True`, `hasFilterCta = False`.
- #2 : `COLORS.a_creuser = #E59A3C` ; carte Saint-Paul/Cilaos nettement plus lisible (screenshots).
- #3 : `Radar AVANT synthèse IA = True` ; fiche `AB0492` : malus −15 toujours affiché.
- #4 : `qa-grid = 3 colonnes / 3 boutons` (desktop), `2 colonnes` (768/390) ; « Démo guidée » absent.
- #5 : `'clé API' présent = False`, `'analyse assistée' = True`.
- **Multi-commune** : Saint-Denis (GOLD), Cilaos (PARTIELLE), Saint-Philippe (NON ÉVALUÉE) — anti-stale OK.
- **Responsive** 1440 / 768 / 390 : **0 overflow**, **0 pageerror**. **Console locale : 0 erreur.**

## Fichiers modifiés (frontend only)

- `src/labuse/api/web/app.js` — #1 (updateEmptyState + handler js-pick-commune), #2 (COLORS + styleFor),
  #3 (mut-block remonté), #5 (wording « analyse assistée »).
- `src/labuse/api/web/index.html` — #5 (suppression boutons « Démo guidée » 🎬 + carte d'action).
- `src/labuse/api/web/styles.css` — #4 (qa-grid 3 col desktop / 2 col mobile, cartes plus compactes).

## Ce qui n'a PAS été touché

- **DB, scoring, verdicts, valeurs Radar Mutation, données métier** : strictement inchangés.
- Sémantique des couleurs de verdict (seule la **teinte** « à creuser » est éclaircie, pas le sens).
- Logique fiche/cascade/multi-commune (juste un **ré-ordonnancement** du bloc Radar).
- Aucun autre point de l'audit (P3 restants) ni refonte légère/premium — hors périmètre de ce lot.

## Screenshots (avant / après)

- `01_home_1440.png` → `after_01_home_1440.png` : « à creuser » lisible + shortlist remontée + actions compactes.
- `08_saint_philippe_vide.png` → `after_08_saint_philippe.png` : empty-state premium « Commune non encore évaluée ».
- `07_cilaos_partielle.png` → `after_07_cilaos.png` : contraste « à creuser ».
- `after_04_fiche_radar.png` : Radar remonté en tête de fiche.
- `after_768.png` / `after_390.png` : responsive (qa-grid 2 col, 0 overflow).

## DB inchangée

`parcels = 431 663` · `opportunités = 9 103` · `parcel_enrichment = 27` (intact — `/enrichment` aborté
en QA). Aucune écriture, aucune migration, aucun re-cascade.

## Limites restantes (backlog, hors lot)

- **P1 audit** : dépendance au fond de carte (carte sombre/vide sans tuiles) ; **rupture de thème
  fiche** (claire dans app sombre) — non traité (refonte légère, séparé).
- **P2/P3 audit** : surcharge couleurs avec calques cumulés, contrôles carte dispersés, double légende,
  bloc décisionnel « fiche » qui pourrait devenir un vrai composant synthétique (ici : ré-ordonnancement).
- Ces points sont documentés dans `UI_UX_AUDIT_LABUSE_PREMIUM.md` (plan refonte légère / premium).

## Conclusion

> Les **5 quick wins** sont livrés : empty-state premium, carte lisible, fiche décisionnelle en tête,
> shortlist remontée, wording client. **Gain de perception premium réel** pour un effort S/M, **sans
> aucun risque** (frontend, DB/scoring/verdicts intacts, QA verte, 0 erreur console). Les chantiers de
> refonte légère (carte-héros, cohérence de thème fiche) restent ouverts en backlog.
