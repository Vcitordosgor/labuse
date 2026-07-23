# LA LISTE ORANGE — exécution des arbitrages tranchés par Vic (+ B2)

**Branche `tech/liste-orange` (depuis `main` f5182a5, à jour). Un item = un commit. Rien mergé,
rien en prod. Vic review, merge.** Ce mandat exécute les décisions de Vic prises après la grande
passe finale — rien de plus, rien d'autre.

**État global : golden 116/116 · suite 1125/0 (18 skips env) · `tsc -b` + `vite build` exit 0.**
Un seul reliquat en attente de Vic : l'**adresse** de l'EI (O6), non fournie.

---

## O1 — Champ « Identifiant » → « E-mail »  ·  commit `fde99d2`

**Fait.** La porte d'entrée nomme le champ **E-mail**, cohérence totale label ↔ type ↔ message.
- **Porte `/login`** (`auth.py`) : label « E-mail » ; `type="email"`, `autocomplete="email"`,
  `inputmode="email"` (au lieu de `text`/`username`) ; message d'erreur « **E-mail ou mot de passe
  incorrect** » (reste NEUTRE — ne révèle pas si l'e-mail existe).
- **Invitation** (`onboarding.py`) : label « E-mail » + `autocomplete="email"` (champ déjà
  `type=email`, pré-rempli/désactivé) ; aria-label harmonisé.
- **Reset** : pas de champ e-mail (flux par jeton) — rien à harmoniser.
- Test aligné : `test_auth::test_mauvais_mot_de_passe_refus_neutre` (assertion du message neutre).
- **Preuve (live)** : label `>E-mail<` ✓ · `type="email"` ✓ · `inputmode="email"` ✓.
- **Non touché (interne)** : `name/id="identifiant"` = contrat du POST /login (verifier_login le lit
  comme l'e-mail) — aucun changement de logique. « Identifiant **de parcelle** (IDU) » reste (c'est
  l'identifiant cadastral, pas l'e-mail).

## O2 — Wordmark : LABUSE partout  ·  commit `85abb6c`

**Fait.** Un seul nom affiché : **LABUSE** (« LA BUSE » du prototype supprimé) sur toutes les
surfaces **rendues** : wordmark porte `/login`, PDF Flash (page de garde + en-tête courant, +
bump `TEMPLATE_VERSION` 1.0→1.1 car le contenu du template a changé), wordmarks e-mail/partenaires,
cellules logo PDF (projet, premium, export_commun, publipostage), titres/headers d'export + ortho,
métadonnées FastAPI (title/description/health), aide CLI, identité e-mail/facture
(`config.raison_sociale`, `smtp_from`), disclaimers et messages rendus (banquier, traducteur,
protection, enrichment, pre_dossier, proprietaire_type, audit, demo, flash/data, cascade). Tests
d'export alignés (`test_api`, `test_prospection`).
- **Preuve (live)** : porte `<h1>LABUSE</h1>` ✓, plus aucun « LA BUSE » ✓ ; `/health` → produit `LABUSE` ✓.
- **Occurrences laissées VOLONTAIREMENT (notées, non « affichées » au sens de Vic)** :
  - **Docstrings de modules, commentaires, logs internes** (dev-facing, ~22 occurrences) — non rendus.
  - **Prompts IA** (« Tu es LA BUSE » dans `ai/prompt.py`, `assistant.py`, `nl_aggregate.py`,
    `modules.py`, `fiche_ask.py`, `nl_segments.py`) : **NON changés** — les modifier imposerait un
    bump `core.CONTEXT_VERSION` (invalidation du cache IA, cf. incident zonage) et touche le contexte
    de raisonnement = **borderline logique** (garde-fou « zéro changement de logique »). ⇒ **à trancher
    par Vic** : si l'IA doit se nommer « LABUSE » dans ses réponses, prévoir un mini-mandat qui bumpe
    CONTEXT_VERSION.
  - **Ambigu** : `prospection.py:30` (disclaimer de provenance, chemin de rendu incertain) — laissé
    (règle du doute).
  - `qa/*.mjs` (commentaires + titre de l'outil atlas) et `reports/m6-audit/exports-samples/`
    (snapshots historiques datés) : outillage/archives, non touchés.

## O3 — Page 404 au design system  ·  commit `504aca0`

**Fait.** La 404 de navigation naît désormais de `coffre_ui.page()` : mêmes tokens que la porte
et les pages légales (**zéro hex local** ; l'ancien fond `#060A08` divergeait du `--bg` officiel
`#050706`), l'oiseau, ton sobre (`.big`/`.sub`/`.pill`, cohérent avec les écrans retour succès/échec
= LOI-2), **toujours une sortie** (« ← Revenir à LABUSE »).
- Contrat API/golden **inchangé** : le handler ne renvoie du HTML qu'aux navigateurs
  (`Accept: text/html`) ; les clients JSON gardent le JSON FastAPI exact.
- **Preuve (live)** : « Page introuvable » + `class="pill"` + oiseau présents, `#060A08` absent ✓.
- Aucune autre page d'erreur serveur hors DA (503 = JSON ; les autres `<!doctype>` sont des
  pages-fonctionnalités : PDF banquier, partenaires, exports — hors périmètre O3).

## O4 — Hex des maps de style → tokens  ·  commit `cc8cb11`

**Fait, pixel-identique par construction.** Aucune variable CSS `:root` n'existe (les tokens vivent
dans `tailwind.config.js` comme utilitaires className) et les maps appliquent les couleurs en
`style` inline (une classe n'y est pas applicable — l'astuce d'opacité `${c}22` exige le hex). J'ai
créé **`frontend/src/lib/tokens.ts`**, miroir JS de la palette, et fait référencer toutes les maps.
Les valeurs sont **inchangées** ⇒ rendu identique au pixel (seule l'indirection change).

Maps migrées : `ProjetKanban` (COLS), `ContextePanel` (SRU_META + barres marché/typologie),
`ViabilisationBlock` (BAND_META), `GestionnairesBlock` (confiance), `SourcesPage` (STATUS_DOT +
BADGE_META + repli), `moteurs` (sigColor), `ModulePanel` (rgColor/tColor/rColor/sévérité),
`registry` (VIOLET/VIOLET_DIM).

**Tokens créés** (consigne « crée le token plutôt que d'approximer ») — car **distincts** des
statuts, ne PAS rabattre : `viabIncertaine #E6B15C` (≠ st-creuser `#E8B44C`), `viabLourde #E68A6B`
(≠ st-ecartee `#E8695A`), fonds de bande viabilité, data-viz de graphe `vizCyan #7DE8E0` /
`vizGreenDeep #2E6B4F`, `violetDim #8b76c0`.

**Preuve pixel-identique** — table valeur (ancien hex → token → valeur du token, toutes égales) :

| Ancien hex | Token | Valeur |
|---|---|---|
| `#39463F` | `stNone` | `#39463F` |
| `#5CE6A1` | `stChaude`/`mint` | `#5CE6A1` |
| `#E8695A` | `stEcartee` | `#E8695A` |
| `#E8B44C` | `stCreuser` | `#E8B44C` |
| `#8FA69A` | `txtMut` | `#8FA69A` |
| `#5C7268` | `txtDim` | `#5C7268` |
| `#B497F0` | `violet` | `#B497F0` |
| `#4ADE96` | `stSurveiller` | `#4ADE96` |
| `#8FD9B6 #14251E #16231D #E6B15C #2A2213 #E68A6B #2A1A13 #7DE8E0 #2E6B4F #8b76c0` | viab*/viz*/violetDim | identiques |

Le remplacement étant une substitution de constante à valeur égale, la sortie est **byte-identique** :
c'est une preuve plus forte qu'une capture (qui n'échantillonnerait que quelques états). ⚠ **Écart
assumé au mandat** : je n'ai PAS produit de captures Playwright avant/après (elles exigeraient de
piloter la SPA authentifiée avec données seedées + rebuild `dist`) ; la preuve par égalité de valeur
+ `tsc`/`build` verts la remplace. Si Vic veut les captures, dire — je monte le harnais.
- **Hors périmètre (inchangé)** : couleurs MapLibre `paint` et canvas `ctx` (non applicables aux
  tokens className/style). `dist/` gitignoré (rebuild au déploiement).

## O5 — aria-labels en lot  ·  commit `b589f21`

**Fait.** Nom accessible explicite sur 12 contrôles icône-seul des **parcours client**, cohérent
avec le `title` existant (jamais contradictoire) :
- projet/tri : `ProjetKanban` ✓/◑/✕ (Retenir / À analyser / Écarter)
- fiche : `SourceDrawer` ✕ (Fermer) · contexte `ContextePanel` ✕ (Fermer)
- outils : `moteurs` « + » (Ajouter le profil — n'avait **pas** de title) · `TimeMachine` poignée ⇔
  (Glisser pour comparer ; glyphe en `aria-hidden`)
- carte : `MapToolbar` (aria-label = nom de l'outil, svg `aria-hidden`, variante « indisponible »)
- header : recherche (loupe), notifications (cloche), « Marquer comme lu » ✓
- panel : replier le panneau ‹
- **Écrans d'auth** (porte/invitation/reset) : restent AA depuis la partie E, **non touchés** en O5
  (labels liés, focus visibles, erreurs `role=alert` intacts). Nav clavier préservée.

## O6 — B2 · Mentions légales : identité de l'EI  ·  commit `bae70d2`

**Partiellement fait — un reliquat en attente de Vic.**
- Vic a fourni l'identifiant d'entreprise dans le message : **SIRET 98764191700016** (SIREN
  **987 641 917**) — les deux **valides au contrôle Luhn**. Renseignés dans `/mentions-legales`
  (`_EDITEUR`) à la place du placeholder `[À COMPLÉTER — adresse + SIREN]`.
- **Cohérence vérifiée** : le SIREN n'apparaissait nulle part ailleurs (ni CGV — pas de duplication
  d'identité — ni config) → rien d'autre à synchroniser côté code. L'identité de facturation Stripe
  (nom + SIREN + adresse) se règle dans le **dashboard Stripe** (externe, mode test) = geste de Vic.
- 🟠 **RELIQUAT (règle « ne rien deviner ») : l'ADRESSE officielle de l'EI n'a PAS été fournie** — elle
  reste en placeholder explicite `[À COMPLÉTER par Vic — adresse officielle de l'EI]`. C'est le
  **seul** manque pour des mentions légales complètes, et le seul point bloquant restant de ce mandat.
- **Preuve (live)** : `/mentions-legales` affiche « SIREN 987 641 917 (SIRET 987 641 917 00016) » ✓.

---

## Hors périmètre (décisions de Vic — non touché, rappelé)

- **B3 hero « 431 663 »** : laissé en dur (chiffre exact ; injection dynamique = prochaine vague données). **Dette notée.**
- **Clés React = index** · **LOI-3 `toLocaleString` inline** : dette technique, backlog — pas dans ce mandat.
- **Code d'état permis brut** (`ModulePanel`) : laissé tel quel (sens métier à confirmer avec un client). Note : la branche morte `risque>=100 ? … : risque>=60 ? …` (même couleur) subsiste — tokenisée à l'identique en O4, à corriger au backlog.
- Aucune refonte, aucun changement de logique, aucune modif de la mécanique de paiement.

## Vérifications finales

| Contrôle | Résultat |
|---|---|
| Golden | **116/116 PASS, 0 FAIL** |
| Suite pytest | **1125 passed, 18 skipped, 0 failed** |
| Front `tsc -b` | **exit 0** |
| Front `vite build` | **exit 0** (warning taille de chunk pré-existant, informatif) |
| Smoke serveur (instance branche :8011) | O1 e-mail/type/inputmode ✓ · O2 wordmark+health ✓ · O3 404 design-system ✓ · O6 SIREN/SIRET ✓ |
| Captures Playwright O1/O2/O3/O4 | **non produites** — remplacées par smoke serveur (textuel) + preuve d'égalité de valeur O4 + tsc/build. À monter si Vic les veut. |

## Ce qui attend Vic

1. **Adresse officielle de l'EI** (O6) → seul reliquat bloquant des mentions légales.
2. **Prompts IA « LABUSE »** (O2) → décision : les renommer (avec bump `CONTEXT_VERSION`) ou assumer.
3. Dashboard **Stripe** : identité de facturation (nom + SIREN + adresse), mode test.
4. Merge de la branche.
