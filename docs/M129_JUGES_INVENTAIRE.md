# M129 P3 — LA MORT DES JUGES : L'INVENTAIRE COMPLET (avant suppression)

*Règle du mandat : chaque suppression = consommateurs AVANT (grep), migration, preuve APRÈS
(golden). Cet inventaire est le « AVANT » exhaustif — l'exécution suit (session dédiée si
nécessaire, cf. STOP).*

## 1. LA MATRICE (q_score / a_score / matrice_statut — colonnes de dryrun_parcel_evaluations)

**Producteur unique** : `scoring/dryrun.py:15 compute_matrice` (UPDATE :67) + CLI `dryrun-matrice`
(`cli.py:710`). **Mort structurelle immédiate : la matrice N'EST PAS construite pour q_v10_m129**
(colonnes NULL) — le run unique ne la produit plus.

**Consommateurs (grep complet, à migrer/supprimer)** :
| Où | Usage | Migration |
|---|---|---|
| `app.py:910` | filtre `score_min` lit `d.q_score` | MEURT (jargon interdit ; la proba/rang remplace) + front `api.ts:66`/`MapView.tsx:104` (`scoreMin`→prop q_score) + `filters.test.ts` |
| `app.py:1328-1342` | export CSV : colonnes statut_matrice/q_score/a_score | colonnes retirées de l'export |
| `app.py:1591`, `:1936`, `:2111` | `matrice_statut AS status` servi (liste, geojson) | → `d.status` (cascade, la seule vérité) |
| `app.py:2278-2281` | stats par matrice_statut | → stats par tier v2/étage 0 |
| `tiles.py:157`, `:348` | q/a bakés dans les tuiles | props retirées au build-mvt |
| `events.py:352-356` | diff de bascule par matrice_statut | → diff par status cascade + tier |
| `moteurs.py:61-298` | Copilote outils : affiche/ordonne par q_score | → ordonner par `s2.rang`, afficher mult_v2 |
| `partners.py:490-497` | API v1 : filtre/tri q_score (CONTRAT EXTERNE) | alimenter par `opportunity_score` (produit par tout run) — clé de payload conservée, dit au rapport |
| `flash/data.py:206` | SELECT q/a MORT (grille retirée M-P, seul etage0 sert) | trim du SELECT (sans effet servi) |
| front : `ParcoursTinder.tsx:166` (« Qualité »), `Kanban.tsx:100` (chip), `ModulePanel.tsx:538`, `App.tsx:189` (fallback) | affichages q_score | → mult_v2/rang (App.tsx a déjà le fallback) |
| `arene.py`, `score_v.py:568` | outil d'analyse / commentaire | arene : à migrer sur opportunity ; score_v : commentaire seul |

## 2. LE TIER COMME STATUT D'ÉCARTEMENT (`tier='ecartee'`, 354 355)

Les filtres carte définissent DÉJÀ « écartée » par l'étage 0 (`app.py:899-902`, M122) — le tier
'ecartee' n'y est qu'un opt-in d'affichage. **Meurt comme STATUT** : `verdict_servi.py` (labels),
`statuts.py assign_tiers` (ne plus produire 'ecartee' — l'étage 0 cascade suffit), exports
(`app.py:1337` « ecartee si etage0 » — déjà étage0-first ✓). **Les tiers de PRÉSENTATION restent**
(brûlante/chaude/a_creuser/réserve, top ~1150 par rang).

## 3. q_score (le nom)

Meurt AVEC la matrice (c'est sa colonne). Jargon interdit à l'écran (P5) — les 4 lectures front
ci-dessus sont la liste exacte.

## Vérité de séquence

Ces suppressions changent des PAYLOADS SERVIS (export CSV, geojson props, tuiles, API partenaires,
chips front) : elles sont **couplées à la bascule** (le golden bouge — chaque diff sera dit au
rapport d'impact, P6.4). La mort STRUCTURELLE (matrice non produite pour q_v10) est effective dès
le run unique.
