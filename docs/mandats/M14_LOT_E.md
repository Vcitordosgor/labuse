# M14 — LOT E : Sources, fraîcheur honnête

**Branche** : `fix/m14-e-sources` · **Base** : `main` · **Dépend de** : LOT A. Build 0 erreur. Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuve : `qa/m14/E/e1_sources_deux_regimes.png`.

## Contexte (issu de A1)
Le contrôle automatique **existe** = le **radar** (`source_radar`, sonde métadonnées, dernier passage 2026-07-22), mais **hebdomadaire** et limité aux **9 sources sondables**. `source_checks` (contrôle manuel) est vide et **supprimé de l'affichage** (acté Vic — M13-F1 l'affichait « — »).

## E1 — Affichage à deux régimes (`components/sources/SourcesPage.tsx`)
- **Source sondable** (`radar.statut !== 'non_sondable'`) → version en service **+ « Dernier contrôle : vérifié il y a X »**, où X est calculé depuis `source_radar.derniere_verif` (date **réelle** du radar). Ex. « vérifié il y a 2 jours » (radar du 22/07, aujourd'hui 24/07).
- **Source non sondable** (INSEE, SAFER, Géorisques… 43 sources) → version en service **+ « Cadence producteur : … »** (cadence connue du producteur via `radar.cadence`), **aucune date de contrôle** (techniquement impossible, pas d'URL datée).
- **Plus jamais de « — » nu** : le champ de contrôle n'apparaît que sous une des deux formes réelles ; il disparaît si aucune n'est disponible.

Vérifié à l'écran (Playwright) : « vérifié il y a X » **présent**, « Cadence producteur » **présent**, « Dernier contrôle : — » **absent**.

## E2 — Remplir « Version en service » manquante
- **Filosofi INSEE (carreaux 200 m)** → **« millésime 2021 »** (directive M14, ajouté à `MILLESIME_VERIFIE`).
- **BPE INSEE**, **Zonage SAFER (DAAF)** : `last_sync_at` NULL en base locale, pas de millésime tracé, pas d'année dans le nom → **millésime non tracé en base localement**. Conformément à la boussole (« ne jamais afficher une donnée qu'on ne possède pas »), **je n'invente pas** : repli honnête « millésime non tracé en base » (jamais un « — » nu). À renseigner quand la donnée sera tracée / en prod.

## E3 — Le mécanisme de recheck 48 h
**Il existe déjà (le radar) et couvre les sources sondables** — donc **branché à E1** (les 9 sondables affichent leur `derniere_verif` réelle). **Il tourne toutefois HEBDO, pas 48 h.**
- **Passer à 48 h = modifier la fréquence du cron** `deploy/cron.d/radar` (`40 2 * * 1` → p.ex. `40 2 */2 * *`). C'est une **modification d'infra** (hors code applicatif de ce lot) — **non faite ici**, consignée.
- Le radar ne couvrira **jamais** les 43 sources non sondables (pas d'URL datée) : pour elles, le « 48 h » est **techniquement impossible**. On n'a **rien simulé** : version + cadence producteur seulement.
- **Honnêteté** : l'écran ne promet aucun contrôle 48 h fictif. Le pied de page dit la vérité (« radar hebdomadaire, couvre les sources à date interrogeable »).

## Décisions / réversibilité
| Point | Choix | Alternative | Revenir |
|---|---|---|---|
| Régime contrôle | 2 régimes selon `radar.statut` | Date manuelle (supprimée) | — |
| Filosofi | « millésime 2021 » (Vic) | Laisser vide | retirer de `MILLESIME_VERIFIE` |
| BPE/SAFER | Repli honnête « non tracé » | Inventer un millésime (refusé, boussole) | renseigner quand tracé |
| Cron 48 h | **Non fait** (infra) — consigné | Le fabriquer ici (hors périmètre) | éditer `deploy/cron.d/radar` |

## Non fait / bloqué
- **Recheck 48 h** : le mécanisme (radar) existe mais tourne **hebdo** ; le passage à 48 h est une **édition de cron** (infra), non faite dans ce lot par prudence. Estimation : trivial (1 ligne de cron) — mais à décider par Vic, et sans effet sur les 43 non sondables.
