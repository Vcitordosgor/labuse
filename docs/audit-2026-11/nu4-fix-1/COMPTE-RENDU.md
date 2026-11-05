# NU4-FIX-1 — Corriger NU-4, par cause

**Registre.** Branche `fix/nu4-1`, worktree `~/Desktop/labuse-nu4fix`, ports 9720/6920, modèle Opus.
**Aucun merge, aucun accès prod, Stripe en mode TEST.** Chaque correction est faite **à la source** ;
chaque trouvaille est **rejouée par une reproduction** (rouge avant, verte après) dans un test dédié
`tests/test_nu4fix_1_*.py`. OPS-URGENCE-2 (disque, calcul-nuit, sauvegardes, Radar) **non touché**.

Rapports corrigés : `docs/audit-2026-11/nu-4/{A,B,E,F}/RAPPORT.md`.

| Lot | Trouvailles traitées | Repro |
|---|---|---|
| **A — sécurité** | M1 (2FA) · M2 · M3 · Y1 · Y2 · Y3 · m1 · m3 · m4 + garde structurelle | `test_nu4fix_1_securite.py` (9) |
| **B — paiement** | T1 · T2 · T3 · T4 · T5 · T6 · T7 | `test_nu4fix_1_paiement.py` (9) |
| **E — charge** | R1 · R2 · R3 · R6 | `test_nu4fix_1_charge.py` (8) |
| **F — John** | prompt confidentiel · plafond par appel | `test_nu4fix_1_john.py` (4) |

---

## A — Sécurité (vue attaquant)

**Classe systémique fermée : les écritures d'état partagé hors `/admin` sans garde.**

- **M2 — `/audit/{reference,adresse,polygone}`** (`app.py`) : écrivent la table globale `parcels`
  (`origine='audit'`) + cascade de scoring, comme la sœur `/parcels/{idu}/evaluate`. Ajout de
  `request: Request` + `auth.exiger_admin(request)` sur les trois routes.
- **M3 — `/modules/prospection-piscines/pas-une-piscine`** (`modules.py`) : exclusion GLOBALE
  cross-tenant (`ON CONFLICT (idu)`). Ajout de `exiger_admin` (décision opérateur).
- **Y1 — `/api/copilote-v2/veilles/evaluer`** (`copilote_v2.py`) : évalue les veilles de **tous** les
  comptes, avance leurs filigranes. Ajout de `exiger_admin`.
- **Y2 — `/sources/{source_id}/test`** (`app.py`) : énumère le catalogue de sources + déclenche un
  appel sortant. Ajout de `exiger_admin`.
- **Garde STRUCTURELLE** (`test_nu4fix_1_securite.py`) : un test énumère **toutes** les routes mutantes
  hors `/admin` et refuse toute route **non classée** (publique-par-conception / tenant-scopée /
  mutation-globale→`exiger_admin`). Une nouvelle route qui écrirait « pour tous » sans garde fait
  désormais **échouer le test** — le trou de classe ne peut plus se rouvrir en silence.
- **M1 — limite d'essais 2FA tenue EN BASE.** Le compteur vivait dans le cookie `labuse_2fa` que
  l'attaquant rejouait à `n=0` (1000/1000 essais à l'audit). Ajout de `echecs_2fa` + `verrouille_jusqu_a`
  sur `totp_2fa`, avec `enregistrer_echec_2fa` / `verrou_2fa_restant` / `reinit_echec_2fa` (mêmes seuils
  que le mot de passe : `login_echecs_max` / `login_verrou_minutes`). `/login/2fa` : au-delà du seuil,
  **429** quel que soit le cookie, et un bon code reste refusé tant que le verrou tient. `/login/2fa`
  rejoint aussi `PREFIXES_PROTEGES` (rate-limit per-IP, défense en profondeur).
- **Y3 — jeton de désinscription** (`events.py`) : `==` → `hmac.compare_digest` (temps constant).
- **Mineurs** : m1 attribution `/feedback` prise de la **session** (plus du corps, forgeable) ; m3
  `slow_failure` passé en `run_in_threadpool` (plus de `time.sleep` bloquant sur l'event-loop des
  handlers `async`) ; m4 en-têtes `Permissions-Policy` + `Cross-Origin-Opener-Policy`.
- **Résiduels NON traités (documentés)** : m2 (DDL `/partners/share` sur chemin chaud), m5 (SSRF TOCTOU
  `depot-agence`, atténué par allowlist), m6 (cap de corps dépôt Radar) — hardening admin-only, faible
  exploitabilité ; à reprendre hors fenêtre.

---

## B — Paiement (toute la vie d'un compte)

- **T1 (CRITIQUE) — « Régulariser » ne crée plus de 2ᵉ abonnement.** `facturation.lien_regularisation`
  renvoie l'`hosted_invoice_url` de la facture **ouverte** de l'abonnement existant (comme le lien du
  mail `relance_carte`) ; `onboarding.paiement_lancer` l'ouvre quand le compte **a déjà** un abonnement
  (`a_abonnement`), et ne crée un Checkout que pour une **première** souscription. Plus de 349 € pris
  sans service.
- **T2 — essai expiré qui paie débloque.** L'activation webhook efface `essai_expire_at` → plus de
  re-suspension au 1ᵉʳ accès.
- **T3 — mention 293 B dès la 1ʳᵉ facture.** `creer_checkout` **pré-crée** le client Stripe avec
  `invoice_settings.footer` et le passe en `customer=` → la 1ʳᵉ facture hérite du pied (avant : posé
  après coup, la 1ʳᵉ sortait `footer:null`).
- **T4 — ré-abonnement propre.** L'activation distingue le **vrai doublon** (double-clic d'un compte
  actif → annulation ROB-C préservée) de la **ré-souscription** (ancien abo résilié/suspendu, ou
  `acces_fin_at` posé) → on **adopte la nouvelle** souscription et on efface `acces_fin_at`.
  `reactiver_compte` efface aussi `acces_fin_at` / `lecture_seule_avertie_at`.
- **T5 — admin lit Stripe dans le même mode que l'app.** `stripe_lecture.cle_restreinte` n'emploie la
  clé restreinte que si son **mode** (test/live) == celui de la clé d'écriture de l'app ; sinon elle lit
  avec la clé de l'app (lecture seule). Fin du « admin voit le LIVE, l'app facture en TEST ».
- **T6 — bascule lecture seule annoncée.** Colonne `lecture_seule_avertie_at` (une fois) ;
  `session_utilisateur` enfile à J+7 un rappel de paiement (`relance_carte`, dédup distinct
  `lecture_seule:{compte}`) via la file mail. *(Choix : réutiliser le template de rappel existant plutôt
  que créer un template Brevo id 20 non provisionné, pour ne pas casser la recette `local` de Vic.)*
- **T7 — accès lecture borné.** Au-delà de `PAIEMENT_GRACE_JOURS + PAIEMENT_LECTURE_SEULE_JOURS`
  (7 + 30 j), `session_utilisateur` **suspend** même sans `subscription.deleted` de Stripe.

Toute la vie d'un compte du lot B est rejouée par webhooks SIGNÉS + Stripe stubé (mode test).

---

## E — Charge (50 clients + 7 nuits)

- **R1 (GRAVE) — le rendu PDF ne peut plus tuer un worker.** `exports/rendu.render_pdf` tourne
  **hors-process** (pool de processus `spawn`, `max_tasks_per_child` → mémoire bornée, `RLIMIT_AS`
  dans l'enfant, timeout dur). Un crash natif (Cairo/Pango) ou un OOM tue l'**enfant** et remonte en
  `RenderError` ; le worker survit et le pool se rétablit. `pdf_slot` (concurrence bornée) conservé.
  *(En service par défaut ; in-process sous pytest pour la vitesse — le mécanisme d'isolation est prouvé
  directement.)*
- **R3 (MAJEUR) — plus de transaction DB tenue pendant l'appel modèle.** `ai.core.complete` libère la
  connexion (`_liberer_connexion` → `commit`) **avant** l'appel réseau. Couvre d'un coup `/ask`,
  `/explain`, `/ia/*`, Copilote (tous passent par `core.complete`). Fin des 43 « idle in transaction »
  et du risque `idle_in_transaction_session_timeout`.
- **R2 — hygiène du pool.** `pool_use_lifo=True` + `pool_timeout` réglable (`db_pool_timeout_s`). La
  cause d'épuisement (connexions tenues pendant l'I/O modèle) est traitée par R3. *(On n'augmente pas
  le pool : 5 workers × 15 = 75 laisse de la marge sous `max_connections=100` pour les batchs
  calcul-nuit — l'augmenter l'épuiserait.)*
- **R6 — le DDL du heal ne bloque plus les lectures en local.** `models.ensure_schema` passe désormais
  par le moteur de heal dédié à `lock_timeout = 5s` (comme les autres étapes) : un `ALTER … ADD COLUMN`
  qui percute un lecteur échoue vite au lieu de convoyer. R1 supprime par ailleurs son **déclencheur**
  local (plus de relance de worker sous trafic après un crash PDF).

**Limite assumée (comme l'audit).** Le banc **50 clients / 30 min iso-prod** est une activité de banc
hors unitaire ; ici les mécanismes corrigés sont prouvés par repros ciblées (isolation du rendu,
libération de connexion, config du pool). À rejouer sur banc iso-prod pour la mesure « 0 serveur mort,
0 500 » en charge réelle.

---

## F — John Taylor

- **Prompt confidentiel.** Clause de confidentialité ajoutée au system prompt (refus de recopier /
  réciter / traduire les consignes, y compris « débogage / mode développeur / sudo / backticks »), **et**
  filtre de sortie `fuite_prompt` (dernier rempart, indépendant du phrasé du modèle) : bloque toute
  réponse qui reproduit une ligne du prompt, un marqueur distinctif (RÈGLE D'OR / GOLDEN RULE / CARNET /
  « Hors de cette liste »…) ou ≥3 clés d'action `snake_case` (invariantes par traduction). Zéro faux
  positif sur l'auto-référence légitime (« je reste John Taylor… ») et le refus de changement de rôle.
  Les 11 cessions de l'audit (dont la traduction anglaise intégrale et la liste des 7 actions) sont
  toutes capturées ; le message servi devient un refus honnête.
- **Plafond vérifié avant chaque appel modèle.** `chat.repondre` re-teste `budget.etat` **à chaque
  itération** de la boucle d'outils (pas seulement à l'entrée du tour) : le dépassement n'est plus
  « borné à 6 appels » mais nul (le coût de l'appel précédent est au ledger avant le re-test).

---

## Recette

- **Reproductions NU4-FIX-1** : `test_nu4fix_1_securite.py` 9/9 · `_paiement.py` 9/9 · `_charge.py` 8/8 ·
  `_john.py` 4/4 — **30/30 verts** (chacune rejoue la trouvaille : rouge décrit, verte prouvée).
- **Banc complet** `pytest -m "not local and not reel and not network"` (unitaires + base de test) :
  **4339 passed, 90 skipped**, et **2 rouges PRÉ-EXISTANTS, prouvés indépendants de ce mandat** :
  - `test_api.py::test_m137_tuiles_ne_crashent_pas` — `relation "score_labuse" does not exist` dans
    `labuse_test` ; **vérifié : échoue à l'identique sur la base (mes changements remisés)** — c'est le
    red labuse_test connu (cf. mémoire INJECTION-SOLIDE-2 « base-test rouges pré-existants »).
  - `test_copilote3_verdicts.py::test_answer_copro…` — témoin `97404000AV0167` absent de `labuse_test` :
    le résolveur rend « reformuler », que le garde `skip` du test (qui ne teste que « introuvable ») ne
    couvre pas → faux rouge dépendant des données/ordre. Chemin copro déterministe (RNIC) et résolveur
    **non touchés** par ce mandat. En isolement le test **skip** (données absentes), avec ou sans mes
    changements.
  - *(La 3ᵉ rouge du 1ᵉʳ run — `test_dashboard.py::test_stripe_lecture_non_configure` — était bien la
    mienne : T5 tombait en repli sur la clé app même clé restreinte ABSENTE. Corrigé : repli UNIQUEMENT
    sur mode divergent ; clé absente → « non configuré » préservé. Re-testé vert.)*
- **Suite de cohérence** (`-m coherence`, 12 témoins) : **23 passed**.
- **Hook** (`scripts/git-hooks/pre-push`) : scan de secrets **rien trouvé** ; unitaires verts (hors 2
  pré-existants ci-dessus) ; cohérence verte. Front **non touché** (zéro changement frontend → tsc/vitest
  inchangés). Ruff n'est pas dans le hook ; style conforme au voisinage.
- Suites existantes touchées re-jouées sans régression : auth/2FA, facturation, onboarding, stripe,
  ai/core, copilote, brevo, PDF/annonce.

**Dette / hors-scope assumé** : mineurs A m2 (DDL `/partners/share` sur chemin chaud), m5 (SSRF TOCTOU
`depot-agence`), m6 (cap corps dépôt Radar) — hardening admin-only, faible exploitabilité. Banc 50 clients
iso-prod (mesure « 0 mort / 0 500 » en charge réelle) à rejouer sur banc, hors unitaire. Commit NON mergé,
NON poussé (mandat). Les 2 rouges labuse_test pré-existants (score_labuse, témoins absents) relèvent de la
base de test, pas du code.
