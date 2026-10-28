# ANNONCE-1 — « Analyser une annonce » : compte-rendu de construction

**Branche** `feat/annonce-1` (depuis `origin/main`) · worktree `~/Desktop/labuse-annonce1` · ports API 8920 / Vite 6120
**Statut** construit, testé, recette navigateur faite. **Aucun merge, rien de servi touché, aucun accès prod.**
**Date** 2026-10-28 · **Modèle** Opus

---

## Ce qui a été construit

Un nouvel outil **« Analyser une annonce »** dans le menu Outils (16ᵉ carte, groupe « Comprendre le marché »). Un écran d'entrée, **deux entrées** :

- **Entrée 1 — une adresse** (omnibox standard `Adresse, IDU ou référence (BW0917)` + « ou cliquez une parcelle sur la carte ») → **rapport parcelle** : 6 tuiles (surface, zone PLU, SDP restante, classement LABUSE, risques, exposition) + « Estimation du prix » (comparateur DVF de la fiche, débloqué par l'idu) + « Le foncier » (règles de zone, SDP, lien « Ouvrir la fiche parcelle → »). Parcelle **zoomée + contour surligné** sur la carte.
- **Entrée 2 — un lien Leboncoin** (fetch one-shot + parseur détail existants) → **rapport commune** : « Ce que dit l'annonce » (champs **présents seulement**, « non précisé dans l'annonce » sinon), « Prix face au marché » (écart % au repère commune du bon type, **fiabilité limitée**, texte seul **sans bouton**), « La commune » (données communales existantes, lien « Fiche commune → »). Carte **centrée sur la commune, sans parcelle**.

Conforme à la maquette pour la **structure** (panneau gauche + carte, ordre des sections, tuiles/encarts) et à la **DA de l'app** pour le style (composants `components/ui/` — Bouton, Retour, Badge, Chip ; omnibox 40 px, contrôles 32 px, rayons 4/6/pilule ; couleurs de l'app). **Aucune nouvelle couleur, aucun nouveau composant.**

---

## Fichiers (5 modifiés/créés)

| Fichier | Nature | Rôle |
|---|---|---|
| `frontend/src/components/outils/AnalyserAnnonce.tsx` | **nouveau** | l'outil : 3 écrans, en-tête maison (1 Retour/écran), 2 rapports, pilotage carte. |
| `frontend/src/components/outils/registry.ts` | modifié | 16ᵉ entrée `analyser-annonce` (num `N1`, groupe `marche`). |
| `frontend/src/components/outils/ModulePanel.tsx` | modifié | import + `COMPONENTS['analyser-annonce']` + rendu **« bare »** (l'outil porte son propre en-tête). |
| `frontend/src/lib/api.ts` | modifié | client `analyserAnnonce(url)` + types `AnnonceAnalyse`/`AnnonceLue`/`AnnonceMarche`. |
| `frontend/src/components/outils/EtudeDocs.test.tsx` | modifié | garde du nombre de tuiles : 15 → **16** (ajout de la carte). |
| `src/labuse/pige/api.py` | modifié | **un seul** nouvel endpoint `POST /radar/annonce/analyser`. |

### Le seul morceau de back vraiment neuf
`POST /radar/annonce/analyser` (sous `/radar`, **déjà proxifié** en dev — aucune ligne ajoutée à `apiPaths`, garde-fou `test_proxy_dev_couvre_routes_api` **vert**). Il **compose de l'existant**, sans rien réimplémenter :
`_fetch_page_oneshot(url)` (lecture one-shot, 8 s, aucun retry — la même garde que le dépôt agence) → `html_next.extraire_page_annonce(html)` (parseur `props.pageProps.ad`) → `signaux._referentiel(…)` + `signaux._badge(…)` (le moteur de prix du Radar) pour l'écart au repère commune du bon type. Renvoie `{ok, annonce, marche}` ou `{ok:false, erreur, motif}`.

### Entrée 1 : zéro nouveau back
Tout est **lu** sur des endpoints existants (rien de recalculé) :
- `GET /parcels/at` (clic carte / coords) + l'omnibox pour l'idu ;
- `GET /parcels/{idu}` (fiche servie) → `surface_m2`, `reglement_plu.zones[0].zone`, `potentiel_transformation.sdp_residuelle_m2`, `score_v2` (classement), `aleas.n`, et **`prix_ancien`** (le comparateur DVF : médiane €/m², p25/p75, N, rayon, période, fiabilité) ;
- `GET /parcels/{idu}/exposition` (orientation du versant).

Entrée 2, encart « La commune » : `GET /communes/{commune}/contexte` (existant) pour PLU + aléas.

---

## Garde-fous (tous respectés)

- **Échec d'extraction** (page changée, captcha/DataDome, lien invalide) → message d'erreur **propre**, affiché sous le bouton, **sans rapport partiel** (l'écran reste à l'entrée). Prouvé en navigateur (cf. recette, écran 4 : un vrai lien Leboncoin → « le portail bloque la lecture automatique (HTTP 403) »).
- **Source & échelle de toute estimation** affichées : entrée 1 = « bâti ancien, secteur, N ventes · rayon · période, fiabilité » ; entrée 2 = « repère à l'échelle de la commune », fiabilité **limitée**, + le texte imposé « L'annonce ne donne pas d'adresse précise… ».
- **Champs absents jamais devinés** : « non précisé dans l'annonce » + « Seules les informations présentes dans l'annonce sont affichées. »
- **Un seul « Retour » par écran** : « ← Outils » à l'entrée (rouvre le menu), « ← Retour » dans un rapport (revient à l'entrée). La croix ✕ ferme l'outil (ce n'est pas un retour).
- **T1 (changer d'outil vide tout)** : `setModule` (store) remet à zéro ; l'état local de l'outil (étape, saisies) repart à zéro au remontage.
- **Formats français**, pas de défilement horizontal, pas de texte tronqué (vérifié à l'écran).
- **Mandat respecté** : pas de pont V2 (aucun rattachement annonce→parcelle), pas de SeLoger/Bien'ici (« à venir »), pas de DPE.

---

## Écarts assumés vs la maquette (la maquette = structure ; la DA et l'honnêteté des chiffres priment)

1. **« Estimation du prix » en €/m², pas en total €.** La maquette invente un total (« 338 000 € ») pour une parcelle ; or la valeur en euros d'un bien dépend de sa surface **et de son état**, inconnus pour une parcelle nue. On affiche donc le **comparateur DVF réel** (`prix_ancien` de la fiche) en €/m² : repère = médiane, fourchette = p25–p75, + N ventes · rayon · période · fiabilité. C'est exactement « le comparateur DVF existant débloqué par l'idu », sans fabriquer une surface. (Démo : `97411000AB0767` → **2 696 €/m²**, de 2 500 à 3 062, fiabilité élevée, 54 ventes · rayon 500 m · 2022–2025.)
2. **PLU** affiché via `plu_statut.statut` (« à jour ») plutôt que le libellé technique interne (« approuvee_probable »).
3. **« Ventes (12 mois) »** → on affiche le N et la **vraie période** du référentiel DVF (p. ex. « 2022–2025 »), jamais un « 12 mois » faux (le baromètre DVF n'a pas de fenêtre glissante).

---

## Recette — constats navigateur (preuves)

App lancée : API `:8920` (base Mac `labuse`, `env=local`) + Vite `:6120` (proxy → 8920). Captures dans `captures/` (git-ignoré par convention `**/captures/` du dépôt — artefacts locaux) :

| Capture | Constat |
|---|---|
| `annonce-01-entree.png` / `-panel.png` | Écran d'entrée : « ← Outils », titre, sous-titre, omnibox + invite carte, « OU », champ lien + bouton « Analyser l'annonce », mention portails. Carte à droite. |
| `annonce-02-parcelle.png` / `-panel.png` | Entrée 1 sur `97411000AB0767` (Saint-Denis) : 6 tuiles réelles, estimation €/m², « Le foncier », **parcelle zoomée + contour surligné**. |
| `annonce-03-annonce.png` / `-panel.png` | Entrée 2 sur une vraie annonce Leboncoin (terrain, Saint-Denis) : « Ce que dit l'annonce » (Pièces = non précisé), « Prix face au marché » **−31,2 %** vs repère 482 €/m², fiabilité limitée, « La commune ». **Carte centrée commune, sans parcelle**. |
| `annonce-04-echec.png` | Entrée 2 sur un **vrai lien Leboncoin live** → message propre « le portail bloque la lecture automatique (HTTP 403) », **aucun rapport partiel**. |
| `maquette-annonce-reference.png` | La maquette rendue (référence de structure). |

**Note sur la capture « succès » de l'entrée 2.** La récupération serveur live de Leboncoin est bloquée (DataDome — c'est le cas d'échec, écran 4). Pour prouver le **rendu du rapport** sur une **vraie** annonce, le fixture d'annonce réel `qa/radar-terrains/T-camelias.html` (déjà au dépôt, page Leboncoin `pageProps.ad` authentique) a été servi en local à une URL contenant `leboncoin.` — le même chemin de code (fetch one-shot → parseur détail → repère commune) s'exécute sans aucun contournement du code servi. En production, l'entrée se fait via l'extension Radar (cf. mandat).

---

## Vérifications

- **tsc** (`tsc -b`) : **0 erreur**.
- **vitest** : **299/299** (62 fichiers), dont la garde de nombre de tuiles mise à 16. *(⚠ au premier run, 8 fichiers `outils/` « échouaient » à cause d'un `node_modules` symlinké — garde fs de Vitest sur le worker maplibre ; après un vrai `npm ci` dans le worktree, tout est vert.)*
- **vite build** (`npm run build`) : **OK**.
- **Garde proxy dev** `tests/test_proxy_dev_couvre_routes_api.py` : **3/3**.
- **Endpoint** : succès (annonce + écart), `url_bloquee` (HTTP 403 live), `url_invalide` — vérifiés au curl.
- **Back parseur/ingest/signaux** `tests/test_pige_depot2.py` : **15 passés / 1 échec `test_d5_copros`** — **identique à `origin/main`** (échec pré-existant, dépendant des données, **sans lien avec ce lot** ; aucune ligne du parseur/ingest/signaux n'a été touchée).

---

## Pour relancer / reprendre

```bash
# API (worktree src + base Mac)
PYTHONPATH=~/Desktop/labuse-annonce1/src LABUSE_DATABASE_URL="postgresql+psycopg:///labuse" \
  ~/Desktop/labuse/.venv/bin/uvicorn labuse.api.app:app --port 8920 --host 127.0.0.1

# Front (proxy vers l'API ci-dessus)
cd ~/Desktop/labuse-annonce1/frontend && LABUSE_API_DEV=http://127.0.0.1:8920 npm run dev -- --port 6120
# → http://127.0.0.1:6120/socle/ · Outils → « Analyser une annonce »

# Tests de ce lot
cd ~/Desktop/labuse-annonce1/frontend && npm run build && npx vitest run
LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse_test" \
  PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python3 -m pytest tests/test_proxy_dev_couvre_routes_api.py tests/test_pige_depot2.py -q
```

**Merge = geste de Vic après recette.**

---

# ANNONCE-1-FIX — reprise (3 points)

**Date** 2026-10-28 · même branche/worktree. Aucun merge, rien de servi touché, aucun accès prod.

## 1 — Classement LABUSE : vrai libellé de bande du run servi
**D'où venait « proche de la moyenne »** : la tuile lisait `score_v2.verbal.mot` — le **phrasé de percentile du Signal de mutation** (« nettement/proche de la moyenne »), **pas** un classement. C'est une donnée du Signal, jamais une bande.
**Correctif** : la tuile lit maintenant la **bande du run SERVI** (`score_labuse`, run courant) et affiche le **vocabulaire client gravé** — **source unique `config/score_labuse.yaml` → `vocabulaire_client`** via la fonction canonique `score_labuse.libelle_client_bande` (aucune table de traduction côté front). Nouveau endpoint lecture seule `GET /radar/annonce/classement/{idu}` → `{bande, libelle}`. Vérifié sur une parcelle par bande : **A · Excellente · B · Bonne · C · À étudier · D · Faible · 0 · Non retenue** (et NC · Analyse incomplète — + cause). *(La parcelle de démo précédente `…AB0767` était en réalité **0 · Non retenue** — SDP résiduelle nulle.)*

## 2 — Message d'échec : une phrase, aucun code
Le message affichait `… (HTTP 403)` (code brut, redondant). Désormais : **le détail technique part en LOG** côté back (`log.warning` dans `/radar/annonce/analyser`, le payload ne porte plus de `motif`), et l'écran affiche **une seule phrase** choisie sur le code d'erreur. Cas « portail bloque » = le texte imposé :
> « Leboncoin bloque la lecture automatique de cette annonce. Entrez l'adresse du bien pour l'analyser. »
Aucun code HTTP ni jargon à l'écran. (Les autres cas — lien invalide, page illisible — ont aussi leur phrase propre, sans jargon.)

## 3 — Champs non applicables au type
« non précisé dans l'annonce » est désormais **réservé aux champs attendus pour ce type et absents**. La liste des lignes de « Ce que dit l'annonce » est **pilotée par le type** :
- **terrain** : Prix · Type · **Surface du terrain** (plus de ligne « Pièces », plus de doublon « Terrain ») ;
- **appartement** : Prix · Type · Surface · Pièces (pas de « Terrain ») ;
- **maison** : Prix · Type · Surface · Pièces · Terrain (NP si attendu-mais-absent) ;
- type inconnu : on ne montre que ce qui est réellement présent (aucun attendu affirmé).

## Fichiers touchés par la reprise
`src/labuse/pige/api.py` (+ endpoint `classement`, log du détail d'échec, payload d'erreur sans `motif`) · `frontend/src/lib/api.ts` (`getAnnonceClassement`) · `frontend/src/components/outils/AnalyserAnnonce.tsx` (tuile classement via endpoint, messages d'erreur par code, lignes « Ce que dit l'annonce » pilotées par type).

## Recette (captures)
`annonce-fix-01-classement.png` / `-full.png` (tuile **A · Excellente**, vraie bande du run servi) · `annonce-fix-02-echec.png` (message corrigé, une phrase sans code) · `annonce-fix-03-terrain-sans-pieces.png` (Terrain **sans ligne Pièces**).

## Vérifications (reprise)
tsc **0** · vitest **299/299** · vite build **OK** · garde proxy **3/3** · endpoint `classement` vérifié par bande (A/B/C/D/0) · échec `/analyser` → payload **sans** code HTTP, détail en **log** (`WARNING labuse.pige.api … HTTP 403`).

**Merge = geste de Vic après recette.**

---

# ANNONCE-1-TESTS — suite pytest remise au vert après merge dans `main`

Le hook `pre-push` (`scripts/git-hooks/pre-push`, famille `not db and not local and not reel and not network`) refusait l'envoi : 7 tests rouges après le merge d'ANNONCE-1. Diagnostic d'abord, correction ensuite, **uniquement sur `feat/annonce-1`**.

## 1 — Horloge naïve (`test_orfevre1_point3_tz`) — VRAIE régression ANNONCE-1, corrigée
`test_garde_de_classe_aucune_horloge_naive_dans_src_labuse` balaie tout `src/labuse` et casse sur le moindre « aujourd'hui » au fuseau du process. ANNONCE-1 avait introduit `date.today().isoformat()` à **`pige/api.py:1107`** (champ `releve_le` du rapport-annonce par lien). **Corrigé** : import local `from ..tz import today_reunion` (pige est sous `labuse.pige`, donc `..tz`) + `today_reunion().isoformat()` — le jour du relevé est désormais le jour **Réunion**, comme partout ailleurs (ORF-17, cf. `ops_alertes.py`, `verite_terrain_plu_toutes.py`). L'import `from datetime import date` devenu inutile a été retiré (aucun autre usage de `date` dans la fonction).

## 2 — Verrou du nombre d'outils (`test_v5f_vert_sur_les_15_outils`) — outil VOULU, verrou mis à 16
ANNONCE-1 ajoute « Analyser une annonce » (`analyser-annonce`, N1) au menu → 16 outils au menu, le verrou V5f en attendait 15. L'outil est **voulu** (mandat ANNONCE-1). Reprise en deux temps :
- Test renommé `test_v5f_vert_sur_les_15_outils` → **`_16_`** (la convention suit le décompte : 18→17→16→15, la cible 16 avait déjà porté ce nom, cf. `docs/audit-2026-09/piscines-2/PISCINES-DENSIFIER.md`). Compte passé à **16**, ligne de traçabilité ajoutée au docstring dans la même forme que les décomptes précédents (« ANNONCE-1 : … → 15 → 16 ») + assertion `"analyser-annonce" in cles`.
- Le verrou V5f ne se contente pas du décompte : il exige que **chaque outil du menu ait son robinet au registre** (`verrou_outils_registre` → `OUTIL_ROBINET_MENU`). ANNONCE-1 avait ajouté l'entrée de menu **sans déclarer de robinet** → le verrou restait « cassé » (« outil analyser-annonce au menu sans robinet au registre »). Déclaré donc **`outil_analyser_annonce`** dans `registre/robinets.py` + mappé dans `circuit_verrous.OUTIL_ROBINET_MENU`.
  - Chiffres déclarés (tous déjà au registre, l'outil **ne crée aucun chiffre neuf**, il réutilise le moteur de prix du Radar et la fiche) : `prix_ancien_median_eur_m2` (repère DVF, estimation adresse + repère lien), `prix_demande_median_eur_m2` (€/m² demandé de l'annonce), `ecart_demande_acte_pct` (écart au repère), `sdp_residuelle_m2` (SDP restante de l'estimation adresse). Les 4 sont dans `NON_SONDES` → **V5c reste vert** (134 couples raisonnés, aucun couple silencieux).

## 3 — Les 4 getsource (`test_retours11f2/f3`) — PAS ANNONCE-1, cause environnementale, RIEN touché
Diagnostic demandé avant toute action. Faits établis :
- **ANNONCE-1 n'a pas touché `app.py`** : `git show b35284715 --stat` ne liste pas `src/labuse/api/app.py` (0 ligne). Ces tests passaient sur `main` juste avant le merge.
- Rejoués seuls **avec le `src` du worktree sur `PYTHONPATH`** : ils **passent** (`test_retours11f2` + `test_retours11f3` → 26 passed / 1 skip).
- Cause identifiée (précédent connu : « le `.venv` qui chargeait le mauvais code ») : les deux venvs du poste (`~/Desktop/labuse/.venv` et `~/Desktop/labuse-main/.venv`) sont installés en editable **vers `/Users/openclaw/Desktop/labuse/src`**, PAS vers le worktree. Ce dépôt-là est sur un **HEAD détaché `d9c1b23a0`** dont `app.py` **diffère** de celui du worktree. Quand pytest tourne sans forcer le `src` du worktree, `inspect.getsource(app._pm_block)` lit le `app.py` périmé → les bornes de lignes tombent sur **une autre fonction** (`_pm_block`→`_pm_dirigeant`, `_proximites_block`→`_depots_block`). Le hook, lui, lance `PYTHONPATH=src` (worktree) → avec le bon `src`, ces 4 tests sont verts.
- **Conclusion : aucune modification de `app.py` ni de ces tests.** Le rouge getsource est un artefact du `src` editable périmé, pas une régression ANNONCE-1.

## 4 — Note d'environnement (base de test)
Le défaut du hook (`postgresql+psycopg://labuse:labuse@localhost:5432/labuse`) suppose un rôle `labuse` ; sur ce poste le rôle est **`openclaw`** et les bases `labuse`/`labuse_test` existent. Pour jouer la suite localement : `LABUSE_DATABASE_URL`/`LABUSE_TEST_DATABASE_URL` = `postgresql+psycopg://openclaw@localhost:5432/{labuse,labuse_test}` (URL **avec hôte TCP** : un DSN socket `postgresql+psycopg:///labuse` fait échouer `test_boot_sans_verrou_sur_tables_chaudes`, qui résout l'hôte — artefact de DSN, pas de code). Ceci ne concerne que l'exécution locale, pas le code.

## Vérifications
Famille du hook (`not db and not local and not reel and not network`), `PYTHONPATH=src`, venv `~/Desktop/labuse/.venv`, URL openclaw : **2684 passed, 47 skipped, 0 failed** (les skips = base applicative/SIRENE absentes, gated par l'environnement). V5f **ok** (16 outils, tous avec robinet ; 64 chiffres servis). V5c **ok**. Front non touché (0 fichier `frontend/` modifié) — tsc/vitest/build restent ceux validés plus haut.

## Fichiers touchés par ANNONCE-1-TESTS
`src/labuse/pige/api.py` (horloge Réunion) · `tests/verrous/test_lot5_concepts.py` (verrou 15→16 + assertion) · `src/labuse/registre/robinets.py` (robinet `outil_analyser_annonce`) · `src/labuse/circuit_verrous.py` (mapping `analyser-annonce`→robinet). **Pas de merge, pas de push.**
