# PARCOURS-FIX-1 — corriger PARCOURS-CLIENT-1, puis rejouer le parcours sur le BUILD DE PRODUCTION

**Branche** `fix/parcours-1` · base = origin/main `a110f52f` · worktree `~/Desktop/labuse-parcoursfix`
· API single-origin (build servi sous `/socle`) sur `:6005` · Opus · corrections + parcours REJOUÉ.

## Verdict en une ligne
**OUI — un promoteur va de l'invitation à l'usage sans aide, sur le build de PRODUCTION.** La page
blanche est corrigée (le build s'ouvre, 0 « t is not a function »), le dry-run mail est désormais
**étanche** (aucun mail réel ne peut partir en local), et les six frictions gênantes sont levées.
Les 40 étapes rejouées (37 ordinateur + 3 mobile) sont **toutes ✅ OK** — planche : `PARCOURS.html`.

> Ouvrir la planche : `open docs/audit-2026-10/PARCOURS-FIX-1/PARCOURS.html`

---

## Lot 1 — les deux bloquants

### 1.1 — Build de production : la page blanche est CORRIGÉE 🔴→✅
**Cause** (identique à MAPLIBRE-1 `9cc198cb`) : le groupe de chunk manuel `vendor`
(`frontend/vite.config.ts`) isolait React (module CommonJS) dans un chunk séparé ; sous Rolldown
(vite 8), le helper d'interop CJS `__commonJSMin` n'était pas co-localisé → `TypeError: t is not a
function` à l'init du vendor → React ne montait jamais → **écran blanc**. **Fix** : suppression du
groupe `vendor` (React reste dans l'entrée, avec son helper) ; le groupe `maplibre` est **conservé**
(ESM, sans helper CJS) ; **maplibre 4 conservé**, rien d'autre de la branche maplibre.

**Preuve** : `npm run build` OK ; l'app servie par l'API du worktree (`/socle/`) s'ouvre après login
— `window.__labuse` = object, `#root` ≈ 31 000 caractères rendus, **0 erreur « t is not a function »**
(capture `captures/desktop/01-app-build-rendu.png`, + mobile `captures/mobile/03-app-accueil.png`).

**Test de fumée automatique** « le build servi s'ouvre » : `deploy/scripts/smoke_build.mjs` (Playwright :
login → `/socle/` → vérifie que l'app monte et qu'aucune erreur fatale de bundle n'apparaît ; échoue
sur une page blanche). **Branché** dans `deploy/scripts/smoke_test.sh` (étape 9, bloquant s'il tourne
et échoue, SKIP non bloquant si node/playwright absents). Vérifié vert contre le build servi.

### 1.2 — Dry-run mail ÉTANCHE 🟠→✅ (préalable prouvé AVANT tout geste)
**Cause** (incident PARCOURS-CLIENT-1 G1) : `config.py:34 load_dotenv(.env)` réinjecte `BREVO_API_KEY`
dans le process → en « testant en local » la 1ʳᵉ invitation est partie **pour de vrai**. **Fix** :
garde unique `config.envoi_reel_autorise()` — en **local**, l'envoi réseau (SMTP **et** Brevo) exige
le drapeau explicite `LABUSE_MAIL_REEL=1` ; sans lui, transport **`.eml`** (fichier,
`LABUSE_MAIL_DRYRUN_DIR`), **0 appel réseau, quoi que contienne le `.env`**. En **pilote/production**
l'envoi réel reste actif (la config VPS porte les secrets ET pose le drapeau) — jamais un mail client
avalé en prod.

**Test** (`tests/test_parcours_fix1_dryrun.py`, 6 verts) : avec une **vraie clé Brevo dans
l'environnement** et sans le drapeau, `brevo.envoyer_template` fait **0 appel réseau** (httpx.post
monkeypatché pour échouer si appelé) et écrit un `.eml` ; idem SMTP (`smtplib.SMTP` interdit). Le
parcours a tourné avec une **fausse `BREVO_API_KEY` posée exprès** dans `run-api.sh` : preuve que la
garde tient.

**Mail réellement parti pendant l'audit PARCOURS-CLIENT-1** : la **1ʳᵉ invitation `essai`** de leur
session (passée en `etat='recu'`, envoi Brevo réel vers un domaine inexistant → bounce). **Aucun autre**
n'était parti (le reste de la session était déjà en file `a_rejouer`). Cette classe d'incident ne peut
plus se reproduire : en local, 0 envoi réseau sans drapeau.

**Preuve sur CE parcours** : tous les mails du cycle de vie sont en file `a_rejouer`
(`mdp_oublie`, `mdp_modifie`, `suspension`, `retablissement`) avec **`message_id` NULL** (0 envoi Brevo
pour `@cabinet-parcours.re`) ; 4 fichiers `.eml` écrits dans `mails/eml/`.

---

## Lot 2 — les six gênants (tous ✅)

### 2.3 — Page « choix du mot de passe » (invitation)
`src/labuse/api/onboarding.py` + `_PARCOURS_JS` : **champ de confirmation** ajouté ; la **règle (10
caractères + confirmation identique + CGV)** pilote l'état du bouton (éteint `.off` tant qu'elle n'est
pas tenue, message clair ; jamais `disabled` → le submit natif + le serveur restent le filet) ; pour un
**ESSAI**, le bouton dit **« Commencer mon essai »** (plus « Continuer vers le paiement ») et la page ne
parle ni de paiement ni de Stripe. Filet serveur : confirmation ≠ → refus propre.
Captures `invitation-mdp-page` / `-regle-courte` / `-confirmation-differente` / `-pret`.

### 2.4 — « Se souvenir de moi » sur `/login`
`auth.py` + `app.py` : case **« Se souvenir de moi »** ; cochée → session **30 jours**
(`session_hours_souvenir`), décochée → **12 h** (défaut). Appliqué au cookie **et** à la session en base
(pilote : token signé ; client : `creer_session(heures=…)`). Mesuré : cookie `labuse_session` à **≈30 j**.
(Le chemin ADMIN à double authentification garde le défaut — hors parcours.) Capture `login-souvenir`.

### 2.5 — Lien d'invitation copiable depuis la fiche compte
Backend `/admin/licences/{id}/lien-invitation` (ré-émet un token frais, renvoie le lien EN CLAIR ; 409
si le client a déjà activé) ; front `Licences.tsx` : bouton **« Copier le lien d'invitation »** +
champ en lecture seule sélectionnable + bouton **Copier** (visible tant que le client n'est jamais
entré). Captures `fiche-bouton-lien` / `fiche-lien-affiche`.

### 2.6 — Mails
- **Désabonnement** : l'**alerte de veille** (`radar_alerte`, template 13) part désormais avec un en-tête
  **`List-Unsubscribe` un-clic (RFC 8058)** — `brevo.envoyer_template` le pose dès qu'un `LIEN_DESABO`
  est fourni (`pige/digests.py`). Le **digest Radar** réel (`digest_quotidien`, HTML construit côté code)
  **avait déjà** lien désabo + `List-Unsubscribe` (le template Brevo 12 « à tous les comptes » est RETIRÉ).
  *À faire côté Brevo (contenu, 1 ligne)* : ajouter `{{ params.LIEN_DESABO }}` dans le template 13 pour un
  lien VISIBLE dans le corps — l'en-tête un-clic fonctionne déjà sans.
- **Suspension / rétablissement** : les gestes admin **déclenchent** maintenant leur mail (`suspension`
  template 10, `retablissement` template 11), en best-effort par la file (jamais casser le geste).
  Preuve : après Suspendre/Rétablir, la file porte `suspension:a_rejouer` et `retablissement:a_rejouer`.
- **« le le »** : `_params_licence` normalise `DATE_FIN_ACCES` (retire un « le » en tête — les sujets
  disent déjà « …prend fin le … ») ; défense unique, idempotente, pour tout appelant.
- **Relecture des 16** : scan des mails CONSTRUITS côté code (`emails.py`, `pige/digests.py`) → **0
  coquille de mots doublés**. Les 16 templates Brevo (hébergés) : la seule coquille relevée par
  PARCOURS-CLIENT-1 (« le le ») est corrigée ; une re-lecture LIVE des 16 se rejoue avec la vraie clé
  via `pytest -m local` (`test_apercu_seize_rendus_sans_reste_brut`).

### 2.7 — `/retours` 405
`dashboard.py` : ajout d'un **GET `/retours`** qui **redirige** un humain (qui tape l'URL) vers l'app
(`/socle/`, 303) au lieu d'un 405 nu. Mesuré en session authentifiée : **303** (plus de 405).

---

## Lot 3 — le parcours COMPLET, rejoué sur le build de PRODUCTION

Harnais rejouable `scripts/` (API `run-api.sh` sur `:6005`, `parcours_fix1.mjs`, `make_planche.mjs`,
`purge_verify.py`). **40 étapes, toutes ✅ OK** (37 ordinateur + 3 mobile). Détail : `PARCOURS.csv`.

- **A → D** rejoués : Vic crée un essai → fiche + **copie du lien** → le client ouvre l'invitation →
  **mot de passe (confirmation, règle, CTA essai)** → accès ouvert → connexion **« se souvenir »** →
  **les 20 gestes du step 7** (recherche, PLU, Gabarit, Taxe d'aménagement, Assemblage, Faisabilité,
  Calculette, Comparer, Communes, Risques, Étude de zone, Mon secteur, Patrimoine, Permis, Baromètre,
  Radar, Copilote, Documents, Veille, Remonter le temps) → **mot de passe oublié** (bout en bout :
  demande → lien de la file → nouveau mot de passe → reconnexion) → Vic **suspend / rétablit** (mails) →
  **fin d'essai forcée** (« abonnement à régulariser », données intactes).
- **Mobile 390×844** : connexion (avec « se souvenir »), page d'invitation, app (build) ouverte.
- **Clics / temps / « comprend-il ? »** : portés par vignette dans `PARCOURS.html` ; chaque écran est
  lisible et autoporteur (verdict par étape dans la planche).

### Safari — les 8 gestes à faire à la main par Vic (webkit indisponible sur macOS 13)
Playwright 1.62 ne peut pas installer `webkit` sur mac13-arm64 ; tout a tourné sous chromium-1217. À
rejouer dans **Safari** (desktop + iOS) :
1. Ouvrir un **lien d'invitation** → la page « Créer votre accès » s'affiche (oiseau, champs, CGV).
2. Taper un mot de passe court puis sa **confirmation** : vérifier que le bouton reste **éteint**, puis
   s'allume quand tout est bon (« **Commencer mon essai** »).
3. **Activer** le compte et atterrir dans l'app (carte visible, pas de page blanche).
4. **Se connecter** en cochant **« Se souvenir de moi »** ; fermer/rouvrir Safari → toujours connecté.
5. Ouvrir une **fiche parcelle** (recherche d'adresse) et vérifier qu'elle s'affiche en entier.
6. Générer un **PDF** (Dossier ou Gabarit) et vérifier l'ouverture dans l'aperçu Safari/iOS.
7. Poser **une question au Copilote** et lire la réponse.
8. **Mot de passe oublié** : demander le lien, poser un nouveau mot de passe, se reconnecter.

---

## Non-régressions
- `pytest` ciblé (mail/compte/onboarding/auth/dashboard/cloisonnement/veille) : **verts**, sauf **1
  échec d'ENVIRONNEMENT non lié** (`test_copilote_..._cloison` : la route Copilote appelle l'API
  Anthropic, « credit balance too low » — hors code) et le test « Brevo non configuré » **mis à jour**
  pour poser le drapeau d'envoi réel (la garde dry-run court-circuite sinon en local).
- `tsc --noEmit` : **0 erreur** ; `npm run build` : OK ; smoke_build : vert.

## Livrables
`RAPPORT.md` · `PARCOURS.csv` (40) · `PARCOURS.html` + `PARCOURS.pdf` (planche) · `captures/desktop/`
(37) · `captures/mobile/` (3) · `mails/eml/` (preuve dry-run) · `scripts/` (harnais rejouable).
**Purge `[CT-PARCOURS]` vérifiée 0 ligne** (`purge_verify.py`). Branche poussée, **pas de merge**.
