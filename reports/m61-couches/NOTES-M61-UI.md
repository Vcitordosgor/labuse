# M6.1 — items 3 / 4 / 5 (UI hors carte) — notes de livraison

Branche `feat/m61-couches` (rebased sur main) · 14/07/2026 · app d'audit :8010 · aucun commit, aucune écriture en base.
QA Playwright : `node qa/m61_ui.mjs` → **17/17 PASS** (captures dans `captures-ui/`).

## Item 3 — navigation outils

**Livré.** En tête de chaque panneau d'outil : fil d'Ariane `← OUTILS › <NOM>` (`data-module-breadcrumb`).

- `← Outils` (`data-module-retour`) ferme le panneau et rouvre le menu Outils (`toggleOutils` du store — aucun nouvel état) : on change d'outil sans repasser par le rail.
- **Échap ferme le panneau**, avec priorité aux surfaces au-dessus : fiche ouverte / tiroir source / outil carte → Échap ferme D'ABORD celles-ci, le module reste ; un second Échap ferme le module. Vérifié par `3.echap-priorite-fiche` + `3.echap-puis-module`.
- Correctif de robustesse au passage : le listener du panneau est en **phase capture** (`addEventListener(…, true)`). Sans ça, si la fiche était montée avant le panneau, son handler (bulle, `Fiche.tsx:683`) faisait `select(null)` en premier et le panneau — lisant l'état zustand déjà mis à jour, synchrone — se fermait dans le même appui : un seul Échap fermait tout.
- Le `✕` reste (tooltip « Fermer le module (Échap) ») ; le label `OUTIL` violet est remplacé par le fil d'Ariane (même couleur), l'intitulé métier + bénéfice sont inchangés.

Captures : `item3-panneau-fil-ariane.png`, `item3-retour-menu-outils.png`.

## Item 4 — page Sources : badges de fraîcheur

**Livré.** `source_checks` est vide (0 ligne) → le badge est calculé sur la **date de donnée réelle** (`majReelle` existante : max de `last_sync_at` / dernière ingestion tracée) croisée avec la **cadence documentée du producteur**.

- Référentiel prudent `CADENCE_PAR_SOURCE` (12 entrées, uniquement des cadences publiées) : DVF semestriel (184 j), Sitadel mensuel (31 j), BODACC quotidien (marge 4 j ouvrés), cadastre PCI/Etalab semestriel, BD TOPO trimestriel, DPE hebdo (marge 10 j), BPE / Filosofi / RP / Fichiers fonciers annuels, RGE ALTI ponctuel (pas de verdict). Marges volontaires : le badge juge le **retard**, pas l'heure de publication.
- Badges : **À JOUR** (vert), **MAJ ATTENDUE** (orange), **À VÉRIFIER** (gris = cadence non documentée OU aucune date tracée — jamais un vert de complaisance). Légende en tête de page (`data-sources-legende`).
- « prochaine MAJ attendue : <date> » calculée ; « — » si cadence inconnue (rien d'inventé). Date en orange quand elle est dépassée.
- « vérifié le » ne vient QUE de `source_checks` ; table vide → mention discrète « *jamais vérifiée* » (italique, opacité réduite) sur chaque ligne.
- État constaté au 14/07 : 52 sources → 4 vertes (DPE, Sitadel, RP 2023, Cadastre Etalab), 1 orange (BODACC, donnée du 05/07 pour une cadence quotidienne — vrai retard à rattraper), 47 grises. **DVF est grise** : cadence documentée mais aucune date de donnée tracée (`last_sync_at` nul) — c'est honnête ; elle passera verte/orange dès que le job posera sa date.

Captures : `item4-sources-badges.png` (tête + légende), `item4-sources-badges-detail.png` (vert/orange/gris + dates).

## Item 5 — bloc P v2 en fiche : fin du silent-fail

**Livré.** `ScoreV2Block` ne disparaît plus en silence :

- **Erreur réseau / 5xx** → même gabarit que le bloc nominal, badge « indisponible », texte « Score momentanément indisponible — le reste de la fiche n'est pas affecté », bouton **Réessayer** (`refetch`, état « Nouvel essai… » pendant la requête). Vérifié : la panne affichée puis, réseau revenu, Réessayer **remet le bloc nominal**.
- **404** (parcelle absente du run v2) → état honnête « non scorée » : « Parcelle absente du dernier run du modèle v2 — copropriété ou hors périmètre du scoring », **sans** bouton réessayer (re-demander ne changera rien).
- Cas nominal strictement inchangé (×N, percentile, rang, tier, 5 contributions).

Attributs QA : `data-score-v2` (nominal) / `="non-scoree"` / `="erreur"`.

**Note QA importante** : au run courant (`m36-l2f-2026-2026-07-14`), le périmètre est 100 % scoré (431 663/431 663 parcelles de `parcels`, copros incluses avec badge) — il n'existe **aucun** IDU avec fiche renvoyant un vrai 404. Le test 5b simule donc le 404 **au niveau réseau** (Playwright `route.fulfill` 404, même corps que l'API) : le front ne voit aucune différence. `NONSCORED_IDU=<idu>` permet de rejouer le cas réel s'il réapparaît. Autre piège couvert : le cache react-query (staleTime 5 min) ne refait aucun appel pour un IDU déjà chargé → le QA utilise **3 IDU distincts** (nominal / 404 / panne), pris sur le run courant via `/v2/liste` (jamais en dur).

Captures : `item5-bloc-nominal.png`, `item5-non-scoree.png`, `item5-erreur-reessayer.png`, `item5-apres-reessayer.png`.

## Fichiers touchés (items 3/4/5)

- `frontend/src/components/outils/ModulePanel.tsx` — fil d'Ariane, retour menu, Échap (capture)
- `frontend/src/components/sources/SourcesPage.tsx` — cadences producteur, badges, prochaine MAJ, « jamais vérifiée », légende
- `frontend/src/components/fiche/ScoreV2Block.tsx` — états erreur / non scorée + Réessayer
- `qa/m61_ui.mjs` — QA Playwright des 3 items (17 checks)

(Le store/`status.ts`/`api.ts`/`MapView`/`tiles.py` portent aussi le WIP couches des items 1-2 — hors périmètre de ces notes.)

## QA — résultat du 14/07

```
IDU run courant (m36-l2f-2026-2026-07-14) : nominal 97423000AB1908 · 404 97408000AP1647 · panne 97408000AP1610
PASS  3.fil-ariane / 3.retour-menu / 3.echap-ferme / 3.echap-priorite-fiche / 3.echap-puis-module
PASS  4.badge-sur-chaque-ligne (52/52) / 4.trois-etats-presents (4·1·47) / 4.prochaine-maj-honnete
PASS  4.jamais-verifiee (52/52) / 4.legende / 4.dpe-hebdo-a-jour / 4.bodacc-retard-orange
PASS  5.nominal-inchange / 5.404-non-scoree / 5.erreur-visible / 5.erreur-meme-gabarit / 5.reessayer-recupere
OK — M6.1 items 3/4/5 vérifiés
```

Aléa d'environnement pendant la passe : 8010 a redémarré (relance par l'agent couches) et son startup est resté bloqué le temps qu'un `build-mvt` libère ses verrous Postgres — premier run QA interrompu sur l'item 4, sans lien avec le code ; run complet vert ensuite.

## Reste / points ouverts

- `source_checks` toujours vide : le circuit « vérifié le » est branché mais n'affichera une date qu'après le premier audit data qui peuple la table (backlog audit data, cf. décision produit Vues).
- BODACC en retard réel (donnée du 05/07, cadence quotidienne) : rafraîchissement à relancer — le badge orange fait exactement son travail.
- DVF sans `last_sync_at` : poser la date dans le job d'ingestion pour que la ligne sorte du gris.
- Référentiel de cadences = 12 sources ; extension possible source par source, uniquement sur cadence documentée.
