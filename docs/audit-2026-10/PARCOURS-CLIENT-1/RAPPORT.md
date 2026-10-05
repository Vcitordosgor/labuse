# PARCOURS-CLIENT-1 — le parcours d'un client, joué et photographié

**Branche** `audit/parcours-client-1` · base = origin/main `56cc27ea` · worktree `~/Desktop/labuse-parcours`
· Opus · AUDIT JOUÉ (lecture seule du code, aucun correctif).

## Verdict en une ligne
**Oui — un promoteur peut aller de l'invitation à l'usage sans aide _sur le build de développement_** (CTA
clairs « Par où commencer », refus propres, erreurs honnêtes, dates au fuseau Réunion) — **MAIS une
question BLOQUANTE plane sur le build de PRODUCTION**, qui rend une **page blanche** dans le navigateur
disponible et doit être re-vérifié sur la vraie chaîne de déploiement ; s'ajoutent plusieurs frictions
GÊNANTES (pas de confirmation de mot de passe, CTA « paiement » sur un essai, pas de « se souvenir »,
lien d'invitation non copiable en local, dry-run non étanche côté Brevo).

## Environnement (choix assumés)
- **Single-origin** : le front est servi par FastAPI (`/socle`) + pages serveur (`/login`, `/invitation`,
  `/reset`, `/moi`, `/cgv`…) + API, **sur une seule origine** — comme la prod (Caddy). Évite de prendre
  un trou de proxy dev pour un bug produit.
- **Dry-run mail** : `LABUSE_SMTP_*` **et** `BREVO_API_KEY`/`LABUSE_BREVO_API_KEY` **et** les clés Stripe
  vidés (voir *finding BREVO* ci-dessous — c'est nécessaire). → `mail_configured()=False`, `brevo` non
  configuré → tout mail entre en file `a_rejouer`, **rien ne part**.
- **Auth active** : `LABUSE_AUTH_PASSWORD` posé (pilote = admin de fait, sans TOTP ; client = email+argon2id),
  `env=local`, **pas** de `LABUSE_SECRET_KEY`.
- **Navigateur** : Playwright Node, `chromium-1217`, 1440×900 (desktop) + 390×844 (mobile). Scripts
  rejouables sous `scripts/` (`run-api.sh`, `vite.parcours.config.mjs`, `run.sh`, `*.mjs`, `*.py`).
- Comptes de test `[CT-PARCOURS]` à domaine **visible** (`@cabinet-parcours.re`) — le préfixe `[CT-PARCOURS]`
  ne déclenche PAS le masquage (seuls `[CT-TEST]`/`@labuse.test` le font), or il fallait les voir dans la
  liste admin pour jouer le cycle de vie. **Tous purgés** en fin de session (preuve §13).

## Déjà prouvé (COMPTE-2/AUDIT-2/3 + CLOISONNEMENT-1) — cité, non refait
Cycle de vie (`creer-essai`/`creer`/`activer_par_invitation`/prolonger/suspendre/rétablir/`effacer_compte_rgpd`),
16 templates Brevo (IDs 4→19, registre `brevo.py`), dry-run RV-013, cloisonnement projets/CRM/veilles/zones,
cascade RGPD. Ce parcours les **rejoue dans un vrai navigateur** et ajoute les findings ci-dessous.

---

## 🔴 BLOQUANT

### BLOQUANT-1 — le build de PRODUCTION rend une PAGE BLANCHE (à vérifier sur la chaîne de prod)
Le build `npm run build` (vite 8 / Rolldown, **chunk `vendor`**) rendu sous `chromium-1217` lève
`TypeError: t is not a function` dans `assets/vendor-*.js` → **écran noir, 0 nœud rendu** (vérifié dans le
navigateur MCP connu-bon ET dans mon chromium). C'est exactement la classe « page noire = chunk vendor »
notée dans MAPLIBRE-1 (non mergé). Conséquence : **si la prod sert ce build sous un navigateur équivalent,
toute l'app est blanche** — le client ne voit rien.
*Réserve honnête* : build fait avec le `node_modules` (symlink) du dépôt principal, pas le lockfile figé ;
la version de Rolldown peut différer de la prod. **À re-vérifier sur la vraie chaîne de déploiement + un
Chrome récent** avant go-live. J'ai contourné en jouant sur le **dev server** (même source, non-minifié,
rend correctement) pour auditer l'UX réelle. Capture : `captures/desktop/01-B-comptes-liste.png` est le dev
qui marche ; la page blanche prod est décrite ici (console `vendor-DA4-6ZFC.js:1 TypeError: t is not a function`).

---

## 🟠 GÊNANT

### G1 — « dry-run » local NON étanche côté Brevo (incident corrigé en cours d'audit)
`config.py:34 load_dotenv(.env, override=False)` **injecte dans le process** toute variable du `.env` non
déjà posée. Vider `LABUSE_SMTP_*` coupe le SMTP, **mais PAS Brevo** : `BREVO_API_KEY` (non préfixé) du
`.env` est injecté → `brevo` configuré → **les mails du cycle de vie (templatisés) PARTENT POUR DE VRAI**.
Constaté : la 1ʳᵉ invitation `essai` de la session est passée en `etat='recu'` (envoi Brevo réel, vers un
domaine inexistant → bounce). **Corrigé** en vidant explicitement `BREVO_API_KEY`. *Risque produit* : un
opérateur qui « teste en local » avec une vraie clé Brevo dans `.env` enverra de vrais e-mails sans le
vouloir — le mode « dry-run » n'est garanti que pour le SMTP, pas pour Brevo.

### G2 — page « choix du mot de passe » (invitation)
- **Aucun champ de confirmation** du mot de passe (un seul champ) → la « confirmation différente refusée »
  du mandat est sans objet.
- **La règle « 10 caractères minimum » n'est pas imposée sur le bouton** : avec un mot de passe de 3
  caractères (CGV cochée) le bouton devient **actif** (`aria-disabled` retombe à false). L'`minlength=10`
  de l'input peut bloquer le POST HTML5, mais le bouton ne reflète pas la règle affichée.
- **Le bouton est libellé « Continuer vers le paiement » pour un ESSAI** (qui n'a aucun paiement à faire) —
  CTA trompeur, confirme le doute de COMPTE-AUDIT-2.
*OK par ailleurs* : CGV requise (bouton gris sans CGV), succès → compte actif, **2e clic / lien invalide →
« expiré » propre**, login ensuite OK.

### G3 — connexion : « se souvenir de moi » ABSENT
Pas de case sur `/login`. Session fixe (12 h). Mandat : fonctionnalité demandée, inexistante.

### G4 — lien d'invitation non copiable en local
Après création, la fiche affiche « Invitation envoyée ✓ » mais **n'expose pas le lien brut** ; en local les
liens pointent sur `127.0.0.1:8000` (bandeau rouge « aucun client ne pourra cliquer », bien présent). Vic
n'a donc aucun moyen de donner un lien fonctionnel au client depuis l'écran.

### G5 — mails : trois réserves (détail dans MAILS.csv)
- **Aucun lien de désabonnement** dans AUCUN des 16 templates — acceptable pour le transactionnel, **GÊNANT
  pour `radar_digest` (12) et `radar_alerte` (13)** qui sont des e-mails récurrents.
- **`suspension` (10) et `retablissement` (11) ne sont déclenchés par AUCUN geste admin automatique** : les
  boutons « Suspendre »/« Rétablir » changent le statut mais n'envoient pas le mail correspondant.
- **`resiliation` (16)** : l'objet préfixe « le » (`…prend fin le {{DATE_FIN_ACCES}}`) → **« le le 12 octobre »**
  si le caller passe une date déjà préfixée. À vérifier côté caller (facturation).

### G6 — refus admin : deux cas non « 403 propre »
Sur 5 URL admin testées en session client : `/admin/licences`, `/admin/mails`, `/admin/pilotage` → **403
propre** (pas de page blanche, bien). Mais `/usage/admin` → 404 et `/retours` (GET) → **405** (au lieu d'un
403/redirection). Mineur, pas une fuite.

---

## ✅ Ce qui est prouvé JUSTE
- **Bandeau « liens non cliquables »** bien affiché sur la page Comptes (local).
- **Validations de création** : boutons désactivés si champ vide / CGV absente ; **e-mail invalide → bouton
  reste désactivé** ; **accents (« Rémi Téoulé ») acceptés**.
- **Cycle de vie (API)** : prolonger 168 h → « jusqu'au 12/10/2026 à 23h22 (heure Réunion) » ; suspendre →
  `suspendu` ; rétablir → `actif` ; déconnecter → 0 session ; reset mdp → `mdp_oublie` en file (dry-run).
- **Connexion** : mauvais mot de passe → « incorrect » (neutre) ; **compte expiré/suspendu → écran
  « Abonnement à régulariser » + « Vos données sont intactes »** (desktop+mobile) ; déconnexion révoque la
  session serveur.
- **Aucune fuite admin côté client** : bouton « Admin » absent du rail client ; routes `/admin/*` → 403.
- **16 templates Brevo** : tous actifs, **expéditeur + reply-to `victor@labuse.immo`**, **0 variable `{{}}`
  non remplie**, **0 lien `127.0.0.1`/localhost** (les liens viennent des params), **dates au fuseau Réunion**,
  **vouvoiement cohérent**, signature « Victor Lagane · LABUSE ». Rendus desktop+mobile dans `mails/`.
- **Dashboard à jour** : la fiche du client montre « Dernière connexion 05/10 23:29 » (= le login joué) et
  « Usage 20 min sur 7 jours », statut « Essai expiré » — **juste et à jour**.
- **Cloisonnement tient post-merge** : `test_cloisonnement_1.py` **15/16 PASS** (le seul échec appelle Stripe
  `invoices.list` → échoue car clé Stripe vidée dans mon env dry-run — **artefact d'env, pas une régression**).
- **RGPD** : `effacer_compte_rgpd` → **0 ligne orpheline** sur les **34 tables à `compte_id`** + `mail_queue`
  (par destinataire) + `utilisateurs` + `comptes` (preuve `scripts/purge_verify.py`).

## Fluidité
Dev server : chargements **< 1 s à ~2 s**. Parcours lisible : l'écran d'accueil propose 4 gestes explicites
(« Explorer la carte — couches, filtres, parcelles », « Suivre le marché — Radar », « Demander au Copilote »,
« Ouvrir un outil — 16 outils fonciers »). Le refus (compte expiré) est rassurant (« données intactes »).

## Couverture — ce qui N'A PAS été joué cette session (honnêteté)
- **Step 11 (Safari)** : `webkit` non installable (Playwright 1.62 — « does not support … on mac13-arm64 » ;
  seul `chromium-1217` présent). Tout a tourné sous chromium. **À rejouer sur un poste avec webkit.**
- **Step 7** : ~15 des 20 gestes (ouvrir une fiche en détail, Gabarit 2D/3D, Taxe d'aménagement, Assemblage,
  Dossier PDF, Pré-dossier, Veille, alerte, **plafond IA**, Comparer communes, Remonter le temps, Mes vues,
  partage) **non joués individuellement** (budget) — seuls recherche/Outils/Copilote/Radar/Documents capturés.
- **Step 8** : changement de mot de passe in-app + « mot de passe oublié » client (round-trip reset) non
  rejoués en entier (reset admin vérifié).
- **Step 2** : l'état `echec` dur (Brevo en panne) montré via `a_rejouer` dry-run, pas via un échec forcé.
- **Mobile** : app connectée seulement en D9 (compte purgé avant une passe mobile plus large) ; pages
  publiques mobiles capturées (login, légales, invitation expirée).

## Livrables
`RAPPORT.md` · `PARCOURS.csv` (14 lignes) · `MAILS.csv` (16 templates) · `STEPS.md` · `captures/desktop/`
(41) · `captures/mobile/` (7) · `mails/` (32 PNG + HTML + `MAILS_render.json`) · `scripts/` (harnais
rejouable). Purge `[CT-PARCOURS]` vérifiée **0 ligne**.
