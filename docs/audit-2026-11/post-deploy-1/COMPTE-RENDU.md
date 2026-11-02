# POST-DEPLOY-1 — compte-rendu

**Branche** `fix/post-deploy-1` · worktree `~/Desktop/labuse-post1` · ports 9460/6660 · Opus.
**Pas de merge, aucun accès prod.** Base locale = run servi `q_v20` (seq 17), identique prod.
À lire d'abord : `reports/DEPLOY-FINAL.md` (les 4 chantiers sortent de ses *findings* et de la
décision Vic sur le compte pilote).

> **Bilan.** Les quatre chantiers du mandat sont faits et prouvés localement : (1) le compte
> « pilote » partagé est **supprimé** (route, variables, TOTP, textes, tests) — seuls les comptes
> nominatifs + 2FA restent ; (2) `docs_coherence` passe à **0 écart** sur les 3 témoins (les 2
> divergences du doc « Estimer un bien » corrigées **à la source**) ; (3) Estimer écrit **« Prix
> estimé au m² »** partout, jamais « médiane » — et le **251 000 €** de IE0241 est **l'effet voulu**
> des comparables pondérés (chiffré ci-dessous), pas un bug ; (4) le **Pilotage** passe de ~1,6–10,7 s
> à **~5 ms à chaud**, réponse **identique**.

---

## 1. Suppression du compte « pilote » partagé (décision Vic)

**Avant.** Un POST `/login` SANS identifiant authentifiait contre un **mot de passe PARTAGÉ**
(`LABUSE_AUTH_PASSWORD`) puis un **TOTP PARTAGÉ** (`LABUSE_PILOTE_TOTP_SECRET`, uid sentinelle 0),
le tout gardé par un interrupteur `LABUSE_LOGIN_PILOTE_ACTIF`. Une voie admin sans compte nominatif.

**Après.** `/login` n'accepte QUE le couple **nominatif** (email + argon2id + 2FA TOTP **par compte**).
Un POST sans identifiant (l'ancienne voie partagée) → **401 neutre**, aucune session, aucune trace de
la voie. Supprimés **à la source** :

| Élément supprimé | Où |
|---|---|
| Branche de login pilote (mot de passe partagé → défi) | `api/app.py` POST `/login` |
| Défi/vérif 2FA pilote (uid sentinelle, secret de config) | `api/app.py` GET+POST `/login/2fa` |
| `PILOTE_2FA_UID`, `pilote_2fa_exige()`, `password_ok()` | `api/auth.py` |
| `login_pilote_actif`, `pilote_totp_secret` (→ `LABUSE_LOGIN_PILOTE_ACTIF`, `LABUSE_PILOTE_TOTP_SECRET`) | `config.py` |
| Textes/exemples (env, déploiement) | `.env.example`, `.env.pilot.example`, `docs/DEPLOYMENT_OVH_VPS.md` |
| Tests du login pilote | `tests/test_auth.py`, `tests/test_2fa.py`, `tests/test_cloisonnement_1.py` |

**Ce qui RESTE (et pourquoi).**
- `LABUSE_AUTH_PASSWORD` n'est **plus une identité** : c'est l'**interrupteur** qui active l'auth
  (présent / env ≠ local → routes métier gardées ; absent hors local → 503 fail-closed). Documenté
  comme tel dans `config.py` et les `.env.example`.
- Le jeton signé `v1.…` (`auth.make_token`) reste, **frappé EN-PROCESS** par les trois bancs/golden
  (`chasse_banc`, `verite_terrain`, `verite_sources` via `TestClient` + hôte réservé) pour franchir
  l'auth de prod **sans login**. Ce n'est **pas** le compte pilote (aucune route HTTP ne l'émet,
  aucun mot de passe) : il est renommé « session banc en-process » partout (`exiger_admin` renvoie
  `role: "banc"`, plus `"pilote"`). Zéro route de connexion ne le produit.

**Recette.** `grep -rn 'login_pilote|pilote_totp|pilote_2fa|PILOTE_2FA|password_ok' src/` → **vide**.
`tests/test_auth.py` + `tests/test_2fa.py` + `tests/test_cloisonnement_1.py` : **42 passés**, dont
`test_login_pilote_partage_supprime` / `test_login_pilote_supprime` (POST sans identifiant → 401
neutre, 0 session ; login nominatif toujours vivant) et le flux admin nominatif 2FA complet
(enrôlement → session). La connexion « pilote » est **impossible et sans trace dans le code**.

---

## 2. `docs_coherence` → 0 écart (document = écran, à la source)

`scripts/docs_coherence.py` confronte 9 documents d'une même parcelle. Avant : BY0083 & IE0241
portaient **2 écarts chacun, isolés au doc « Estimer un bien »**. Les deux sont corrigés **à la
source** (le doc disait autre chose que l'écran parcelle + les 8 autres documents) :

### a) Hauteur à l'égout — `9/?` → `9/6`
La règle d'urbanisme « Hauteur maximale » du doc Estimer ne servait que le **faîtage**
(`f"{hf} m"`), là où le Dossier/Gabarit/Faisa servent « **9 m au faîtage · 6 m à l'égout** ». Le
`ZoneRules` porte pourtant `hf_m` **et** `he_m`. Correctif **à la source** (`pige/api._regles_zone`) :
la hauteur réglementaire est désormais la chaîne UNIFORME « N m au faîtage · M m à l'égout » (même
voix que `plu_reglement`). → Estimer dit `9/6` (BY0083) et `10/7` (IE0241), comme tous les documents.

### b) Prix du terrain — `501` (médiane commune) → aligné sur le secteur (`250`)
Le doc Estimer affichait DEUX prix de terrain pour une seule parcelle : la **« Lecture foncière ·
secteur »** (250 €/m², le repère réellement utilisé pour la valorisation — identique à l'écran, au
Dossier et au Comparatif) ET, en page 2 « Le marché », une **« Terrain nu, médiane » COMMUNALE**
(501 €/m², notion plus large, **absente de l'écran parcelle**). `docs_coherence` extrayait la médiane
communale et la confrontait au secteur des autres docs. Correctif **à la source**
(`exports/blocs/annonce._marche`, variante PARCELLE) : la ligne « Terrain nu, médiane » communale est
retirée du doc parcelle (elle reste dans la variante **LIEN**, `_la_commune`, où l'écran la montre —
donc « document = écran » par variante). Le repère foncier du doc parcelle redevient **unique** (le
secteur), identique partout. Les médianes BÂTIES (maison/appartement) restent : contexte marché, sans
collision.

**Recette** (`python -m scripts.docs_coherence 97415000BY0083 97408000BL0020 97411000IE0241`) :
**0 écart(s)** sur chacun des trois témoins (avant : 2 / 0 / 2).

---

## 3. Estimer — « prix estimé au m² » partout, et le 251 000 € de IE0241

### a) Libellé (écran · PDF · Doc)
Le prix au m² d'Estimer est une **estimation pondérée**, jamais une médiane. Vérifié sur les trois
surfaces : écran `AnalyserAnnonce.tsx:200` et PDF/Doc `exports/blocs/annonce.py:237` → **« Prix
estimé au m² »**. Le mot « médian(e) » n'apparaît QUE pour le bloc marché distinct (`marche_dvf_
commune` : « Prix médian maison », etc.) — notion volontairement séparée. **Rien à corriger.**

### b) IE0241 : 251 000 € = effet VOULU des comparables pondérés (pas un bug)
Mesuré en direct (run servi) : IE0241 = maison, surface bâtie DVF **63 m²** (vente 2024), **« Prix
estimé au m² » = 3 990 €/m²** → total **251 000 €**, fiabilité **« Moyenne ±26 % »**, fourchette
**186 000 – 317 000 €**.

| | €/m² | surface | total | fiabilité |
|---|---|---|---|---|
| ESTIMER-2 (médiane plate) | 3 485 | 63 m² | **220 000 €** | Élevée ±18 % |
| ESTIMER-PRECISION-1 (**servi**) | **3 990** | 63 m² | **251 000 €** | Moyenne ±26 % |

La surface (63 m²) est **inchangée** entre les deux. L'écart vient **uniquement du €/m²** :
ESTIMER-PRECISION-1 a remplacé la médiane plate par des **comparables pondérés** (distance, surface,
demi-vie d'âge) **re-calés sur l'état de marché courant** (drift géométrique de commune). Sur IE0241 :
médiane BRUTE des 8 comparables ≈ 3 251 €/m² → après pondération + drift **3 990 €/m²** (**+14,5 %**
vs les 3 485 de ESTIMER-2) → **220 k → 251 k**. C'est **exactement** le résultat documenté dans
`docs/audit-2026-11/estimer-precision-1/COMPTE-RENDU.md` (ligne 128 : « 3 990 / 251 000 € / Moyenne
±26 % »). La vente réelle 2024 était **205 000 €** : 251 k tombe **dans** la bande de fiabilité
annoncée (±26 %), et la fiabilité est honnêtement passée de « Élevée » à « Moyenne » (le plancher de
précision maison ~27 % est assumé par ESTIMER-PRECISION-1). **Effet voulu, chiffré — aucune
correction.**

---

## 4. Pilotage à chaud < 1 s (réponse identique)

**Avant.** `/admin/pilotage` agrège ~13 lectures/sondes (listes de sources, relevés Radar, sonde
métier, circuit, etc.) : **~10,7 s à froid, ~1,6 s à chaud** (sous-caches partiels) — jamais < 1 s.

**Après.** Le dict COMPLET est mémorisé (TTL 90 s) et **rafraîchi EN FOND** (même doctrine que
l'aperçu Stripe, VITESSE-3) ; le corps de calcul est extrait dans `_pilotage_calculer()`
(indépendant de la requête — les chiffres sont globaux). Le worker de **réchauffage** le pré-calcule
au boot (placé AVANT le contexte des 24 communes, lent ~12 min, dont il ne dépend pas) → le premier
admin tape déjà chaud. **Sous pytest le cache est court-circuité** (calcul frais à chaque appel) :
aucune fuite inter-tests, l'état réel de la base est toujours vu.

**Mesuré** (serveur local, warm actif) : try 1 `2,34 s` (calcul + mise en cache), **try 2 `0,011 s`,
try 3 `0,004 s`**. **Réponse identique** : comparaison de la réponse HTTP à chaud vs un
`_pilotage_calculer()` frais → **mêmes clés top-level, tous les champs métier identiques** (seuls les
horodatages/âges du snapshot diffèrent par l'instant de capture, attendu).

---

## Fichiers touchés
`src/labuse/api/{app,auth,dashboard}.py`, `src/labuse/config.py`,
`src/labuse/exports/blocs/annonce.py`, `src/labuse/pige/api.py`,
`src/labuse/{chasse_banc,verite_sources,verite_terrain}.py`,
`tests/{test_auth,test_2fa,test_cloisonnement_1}.py`,
`.env.example`, `.env.pilot.example`, `docs/DEPLOYMENT_OVH_VPS.md`.

## Recette (locale)
- `docs_coherence` BY0083 / BL0020 / IE0241 → **0 / 0 / 0 écart**.
- Connexion « pilote » impossible + sans trace (`grep` vide ; tests de suppression verts).
- Suite de **cohérence** (`scripts/ci/coherence_run.sh`) : **6 passés, 0 écart**.
- Front : **tsc -b 0**, **vitest 301/301**.
- Banc complet Python (`pytest tests/`, base réelle) : **4376 passés, 88 skipped, 0 rouge, 0 erreur**
  (35 min). Inclut les familles `db` / `local` / `reel`.
- Pilotage à chaud **~5 ms**, réponse identique.

### Recette banc
`pytest tests/ -q` sur la base réelle locale (run servi `q_v20`) → **4376 passed, 88 skipped, 0
failed, 0 error** en 2133 s. Scan de secrets propre. Les 88 skips sont les gardes pré-existantes
(base de test non réaliste, réseau/ML absents) — aucun n'est introduit par ce mandat.
