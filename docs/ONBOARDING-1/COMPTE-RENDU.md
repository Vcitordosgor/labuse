# ONBOARDING-1 — compte-rendu

Branche `feat/secteur-1` (le correctif part dans le même déploiement que le reste — mes 4 commits
précédents sont déjà mergés dans `origin/main` via `1c8b4bf1`, ma branche est 1 commit derrière ce
merge, aucun code nouveau à reprendre). Arbre propre à l'ouverture. **Un commit de plus. Ne pas merger.**
Golden non touché · API + front redémarrés avant recette (preuves : `docs/ONBOARDING-1/captures/`).

---

## O1 — Reproduire, pas deviner (diagnostic)

J'ai déroulé le tunnel COMPLET en local, comme un vrai client, **derrière le rideau** (`LABUSE_ENV=pilot`,
auth comptes active) — en curl ET en navigateur (Playwright) :

- Admin crée la licence + invitation (`/admin/licences/creer` → `creer_invitation`) → **le lien s'affiche
  dans l'admin** (décision Vic historique : `config.py:217` « AUCUN email automatique, liens à la main » ;
  il n'y a donc pas de mail dry-run — le lien se copie depuis l'écran admin).
- Ouverture du lien `GET /invitation?token=` → formulaire « Créer votre accès ».
- `POST /invitation` (mot de passe + CGV) → activation → bascule (paiement pour l'Intégral, ou « accès
  ouvert » pour l'essai/interne).
- Premier login → session → **arrivée dans l'app** (`/socle/`).
- **Essai 48 h** : MÊME tunnel (`creer_invitation` + compte `actif` + échéance) → « accès d'essai ouvert »
  → login → app, sans paiement. Vérifié.

**Résultat : le tunnel fonctionne pour un lien PROPRE de première main.** Le happy-path n'est pas cassé.

### L'ÉTAPE QUI CASSE (nommée précisément)

**`GET /invitation` — la validation du token échoue dès qu'un caractère invisible est collé en queue de
l'URL.** Un lien envoyé par e-mail arrive très souvent avec un **espace ou un retour-ligne** collé en fin
(le client mail coupe/enveloppe la ligne). Le serveur reçoit alors `?token=<jeton>%20` (ou `%0A`) →
`valider_invitation` hachait le token **brut** (`_sha(token)`) → hash différent → **« Invitation
introuvable » AU PREMIER CLIC**. Erreur exacte :

- **Back** : `SELECT … WHERE invite_token_hash = :h AND statut='invite' AND invite_expire_at > now()`
  ne matche rien (le hash inclut l'espace) → `valider_invitation` renvoie `None`.
- **Front** : la page renvoyée était `HTTP 404` « **Invitation introuvable — lien expiré ou déjà
  utilisé** » AVEC **AUCUNE issue** (pas de `/login`, pas de récupération) = **cul-de-sac**.

C'est très exactement le « tunnel bugué » du lien envoyé à `victorlaganepro@gmail.com`.

## O2 — Cause profonde (pas le symptôme)

**Pourquoi ça n'a jamais marché** : `valider_invitation` hachait le token **sans le nettoyer**. En test
local on colle un token propre (pas de round-trip e-mail) → ça passait toujours ; en vrai, tout client
mail qui ajoute un espace/retour-ligne en fin d'URL cassait le lien **au premier clic**. Le token
lui-même est bien signé (`secrets.token_urlsafe`, hash SHA-256 en base) — ce n'est **ni** une expiration
(7 j), **ni** un token mal signé, **ni** une route front absente derrière le rideau (`/invitation` est
public, `is_public`, et Caddy la proxifie au backend). C'est le **trim manquant**.

Deux correctifs de cause :

1. **`comptes.valider_invitation` TRIMME le token** (`token.strip()`) — un lien collé avec un espace ou
   un retour-ligne ouvre désormais le formulaire, jamais « Invitation introuvable ». (Point de validation
   UNIQUE : couvre GET, POST et l'admin.)
2. **La page d'erreur n'est plus un cul-de-sac** : « Ce lien n'est plus valide » offre un **bouton
   « Se connecter »** (l'utilisateur a le plus souvent déjà créé son accès en recliquant son lien) + la
   consigne « sinon, demandez un nouveau lien ». Refus PROPRE (O4).
3. **Bonus (finding ON-002)** : la page `/login` portait un `<script>` **INLINE** bloqué par la CSP
   `script-src 'self'` (erreur console à chaque connexion). Rapatrié dans `/parcours.js` (externe,
   CSP-safe, déjà public) — la porte garde son état de chargement + l'effacement d'erreur, **zéro erreur
   console**.

## O3 — Test de bout en bout

`tests/test_onboarding_tunnel.py` (6 tests, HTTP via TestClient) déroule le tunnel entier et **échoue si
une étape recasse** :
- `test_tunnel_http_de_bout_en_bout` — GET form → POST activation → login réel possible ;
- **`test_lien_mail_avec_espace_en_queue_fonctionne`** — GARDE DE RÉGRESSION du bug : un token avec espace
  / retour-ligne / espaces autour valide quand même (échoue si le trim régresse) ;
- `test_lien_invalide_offre_login_jamais_un_cul_de_sac` — lien inconnu → 404 AVEC `/login` ;
- `test_lien_reutilise_apres_activation_refus_propre` — re-clic après activation → refus + `/login` ;
- `test_essai_48h_meme_tunnel_puis_login` — l'essai emprunte le même tunnel, accès immédiat sans paiement ;
- `test_mot_de_passe_trop_court_refuse_proprement` — mdp < 10 → 400 explicite, jamais un 500.
(`tests/test_e2e_parcours.py` existant — invitation → webhook Stripe → actif → login — reste vert.)

## O4 — Recette réelle + expiration

Compte de test créé **de bout en bout via le lien**, derrière le rideau (pilot), 6 captures
`docs/ONBOARDING-1/captures/` : `1` formulaire, `2` mot de passe + CGV (bouton allumé), `3` « accès
d'essai ouvert », `4` page de login, `5` **arrivée dans l'app** (`/socle/`), `6` **lien réutilisé →
« Ce lien n'est plus valide » + bouton « Se connecter »** (refus propre, message clair). **0 erreur JS/
console** (la CSP ne crie plus).

---

## Vérifications

- **tsc** 0 · **vitest** 108/108 · **vite build** OK.
- **pytest** : **2039 passed, 0 failed** (+6 `test_onboarding_tunnel.py`), 45 skipped (tests « base
  applicative » qui exigent l'API up pendant la suite — inchangé).
- **Golden** : **119/119 PASS**, GARDE-RUN OK (`q_v11_m137`). **Intact** — 0 fichier de scoring touché
  (auth / comptes / onboarding uniquement).

## Fichiers

Nouveaux : `tests/test_onboarding_tunnel.py`, `frontend/qa/onboarding1_captures.mjs` (+ `onb_repro.mjs`
de diagnostic).
Modifiés : `src/labuse/comptes.py` (trim du token dans `valider_invitation`), `src/labuse/api/onboarding.py`
(page d'erreur avec `/login` + JS de la porte dans `/parcours.js`), `src/labuse/api/auth.py` (login :
`<script>` inline → `/parcours.js`).
