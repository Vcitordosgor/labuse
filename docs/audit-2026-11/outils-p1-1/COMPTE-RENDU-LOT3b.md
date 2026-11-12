# OUTILS-P1-1 — Lot 3, dernières retouches

Étape 0 OK : `pwd`=labuse-outils, branche `fix/outils-p1-1`, arbre propre. Pas de merge.
Captures `lot3b-<outil>-avant/apres.png`.

## Les 6 points — fait / non fait

| # | Point | État |
|---|-------|------|
| 1 | Permis : « Donnée Sitadel au 2026-08-31 » → « 31/08/2026 » ; aucune date AAAA-MM-JJ à l'écran | **Fait** — `fmtDateNum` appliqué partout dans Permis : date Sitadel du bloc total, dates des lignes de permis, « Sitadel au … » du résultat parcelle, et les dates de la bulle permis (dépôt / autorisation / achèvement DAACT). Vérifié : 0 date AAAA-MM-JJ à l'écran. |
| 2 | Permis : « depuis 90 jours » compté depuis aujourd'hui ou depuis la donnée ? | **Réponse + fix.** C'est **depuis la DONNÉE**, pas aujourd'hui : le back ancre la fenêtre sur `dmax = max(date)` de `sitadel_permits` (`date >= dmax − 3 mois`), pas sur `now()` — par honnêteté, le flux Sitadel s'arrête avant aujourd'hui (dmax = 31/08/2026, pas 12/11/2026). Le libellé le dit désormais : **« Récents · autorisés, 90 derniers jours de la donnée »**. |
| 3 | Successions : « plancher restant » → le libellé exact de la fiche | **Fait** — la fiche appelle cette valeur (`sdp_residuelle_m2`) **« SDP restante »** (`<ChiffreDissous l="SDP restante">`). Le grand chiffre et le tri reprennent ce libellé : « SDP restante » + « Triées par SDP restante estimée… ». |
| 4 | Successions : les 59 parcelles A/N au potentiel positif — à cheval vs entièrement A/N | **Réponse + fix.** Toutes les 59 intersectent **au moins un liseré** d'une zone constructible (part constructible de 0,2 % à 58,4 %) : **strictement 0 sont à 100 % en A/N**. Par la règle exacte de la fiche (« à cheval » = aucune zone n'atteint 90 % de la surface) : **43 à cheval** (la fiche montre la composition bizone) · **16 résumées par leur zone A/N dominante** (≥ 90 % ; le résiduel vient d'un petit liseré U/AU < 10 %). **Fix** : pour les parcelles à cheval, la ligne de zone dit la composition **au format de la fiche** (ex. AY1281 → « A 75 % · UE 25 % »), calculée en un seul passage géométrique sur `spatial_layers` (même source que `zone_dominante`). Les 16 « résumées A/N » gardent leur zone dominante (comme la fiche) — aucun correctif, IDU ci-dessous. |
| 5 | Scan : capture CBO Territoria = 210 blocs, rapport = 460. Même propriétaire ? | **Réponse : NON, deux propriétaires différents.** Mon rapport du lot précédent a utilisé le SIREN **310 863 592**, qui est la **SOCIÉTÉ IMMOBILIÈRE DÉPARTEMENT RÉUNION (SIDR)** → **460 blocs** — pas CBO Territoria. **CBO TERRITORIA = SIREN 452 038 805 → 210 blocs** (cohérent avec ta capture). L'erreur : « 310 863 592 » est l'exemple « SIREN » du Scan, que j'ai pris à tort pour CBO Territoria (l'exemple « nom » CBO Territoria et l'exemple « SIREN » sont deux entités distinctes). |
| 6 | Scan : pied de liste au format commun (« N / M affichés · Voir 200 de plus ») | **Fait** — le bouton « Voir plus (448 de plus) » est remplacé par `ListPaginationFooter` (composant commun) : « 12 / 210 affichées · Voir 198 de plus », par paquets de 200 (`PAGE_SIZE`). Le plafond serveur `blocs_limit` grandit d'un paquet par clic. |

### Point 4 — les 16 parcelles « résumées par leur zone A/N dominante » (dominante ≥ 90 %, aucun correctif)
```
97410000BW0538  97410000BW1099  97410000BW1100  97411000CM0169
97411000CT1613  97412000AM1532  97412000CD0299  97414000ER0741
97415000AD0027  97415000DV0441  97418000AO0749  97418000AO1045
97418000AO2083  97418000BL0030  97420000AM0004  97420000AM0006
```
(Pour celles-ci la fiche affiche la seule zone dominante A/N ; le potentiel positif vient d'un liseré
constructible < 10 % de la surface. Rien n'est corrigé, comme demandé.)

## Vérification
- tsc 0 · vitest **326** · secrets · DB successions/permis/patrimoine **22 passed** · pytest unitaires · cohérence 12 témoins.
- Backend : `_successions_zones_a_cheval` (nouveau) — passage géométrique batché sur les seules lignes A/N
  de la page, mémoïsé avec l'endpoint ; param `patrimoine(blocs_limit)` réutilisé par le pied commun.
