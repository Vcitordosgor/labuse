# RAPPORT — PARCOURS D'ENTRÉE (onboarding, paiement, accès)

Branche `fix/parcours-entree` (depuis main `6cb7465a`). Régime autonome. Ce rapport suit E1→E9.
Source de vérité de l'offre (décision Vic 27/08) : **Intégral 349 €/mois, engagement 12 mois** ·
**Flash 79 €, paiement unique**. Aucune autre offre (ni « Illimité », ni 499 €, ni sièges/founding).

---

## E1 — CHASSE AUX CHIFFRES FAUX

### Racine du bug prod « licence Illimité · 499 €/mois »
Chaîne exacte :
1. `comptes.py` portait une **offre fantôme** `PLANS["illimite"] = {"label": "Illimité", "eur_mois": 499}`
   (jamais commercialisée, vestige M23-E).
2. `creer-admin` / `creer_admin_invitation` créaient le compte admin avec `plan='illimite'`
   (« plan valide le plus haut », hors facturation).
3. La page `/invitation` (tunnel CLIENT) affichait `PLANS[inv["plan"]]` → pour un admin :
   « licence **Illimité** · **499** €/mois · engagement 12 mois » + « Continuer vers le paiement ».

Les trois valeurs fausses venaient donc d'**un compte admin routé dans le tunnel client** lisant
une offre fantôme. Corrigé en E1 (offre fantôme retirée) et E2 (écran admin dédié).

### Tableau des occurrences (avant → après)
| Fichier:ligne | Valeur trouvée | Correct ? | Traitement |
|---|---|---|---|
| comptes.py:37 | `illimite` « Illimité » 499 | ✗ offre fantôme | **retirée** ; PLANS ne garde qu'Intégral (dérivé d'offres.py) |
| comptes.py:528,571 | admin `plan='illimite'` | ✗ | → `plan='interne'` (ni offre ni prix) |
| quota.py:29,52-58 | « Illimité 499 €/mois », plafond 200 | ✗ (message CLIENT) | message réécrit sans offre fantôme ; `interne` non borné |
| facturation.py:55,67 | `349*100`, `79*100` en dur | ✓ valeurs | lues depuis `offres.py` (une source) |
| onboarding.py invitation/paiement | `PLANS[...]` 349/499 | mixte | → `offre_integral()` (jamais 499) |
| onboarding.py CGV:370-398 | « 349 € », « 79 € », « 12 mois » en dur | ✓ valeurs | interpolées depuis `offres.py` |
| onboarding.py flash:562-576 | « 79 € » en dur | ✓ valeur | interpolé depuis `offres.py` |
| Licences.tsx:195 | « 349 €/mois » **en dur (front)** | ✓ valeur | lit `/api/offres` (getOffres) |
| config.py | `flash_price_eur=79` | ✓ | + `integral_prix_eur_mois=349` (source du prix Intégral) |

### Source de vérité unique
`src/labuse/offres.py` : `offre_integral()` (349 €/mois, engagement 12 mois) et `offre_flash()`
(79 €, unique), **prix lus en config** — un seul endroit à changer. Servie au front par
**`GET /api/offres`**. Test anti-régression `tests/test_offres.py` : échoue si un montant d'offre
est écrit en dur dans le front, ou si « Illimité »/499 réapparaît.

---

## E2 — ACTIVATION ADMIN (sans paiement)

`GET /invitation` détecte un compte `plan='interne'` (admin nominatif) et sert un **écran dédié** :
e-mail (non modifiable) → mot de passe → « Créer mon accès administrateur ». **Aucune** mention
d'offre, de prix, de CGV commerciales, de Stripe. Il annonce que la 2FA s'enrôle à la 1ʳᵉ connexion.
`POST /invitation` déroge à la CGV pour l'interne (jugé sur le **plan serveur**, pas sur un champ
falsifiable) ; le garde CGV du tunnel client reste intact. Le login admin déclenche déjà la 2FA
(V5, `role=='admin'` → `/login/2fa`). Cas « déjà promu, mot de passe posé » (Vic) : message CLI
enrichi (→ `/login`, la 2FA s'enrôle ; reset en filet). Tests : `tests/test_activation_admin.py`.

---

## E3 — LE BUG DE LA CASE CGV

**Racine** : la CSP de prod (`app.py` : `script-src 'self'`) bloque **tout script inline** ET
**tout gestionnaire `onchange=`/`oninput=`**. Le toggle CGV (`labCgv()`, inline) ne s'exécutait
jamais en production → la case cochée ne débloquait pas le bouton (message « Vous devez d'abord
accepter… » figé). Le commentaire du code prétendait « zéro script inline » — faux pour les pages
serveur onboarding.

**Correction** (systémique) : tout le JS du parcours est servi en **fichier same-origin**
(`/parcours.js`, `/flash-retour.js`) que `script-src 'self'` autorise ; handlers posés par
`addEventListener`, **zéro inline**. En défense : le bouton n'est plus jamais `disabled`
(plus de cul-de-sac si le JS échoue), la case reste `required` (validation native) et le
serveur garde l'exigence CGV.

**Même patron corrigé ailleurs** (autres victimes de la CSP, trouvées en balayant) :
- `/flash/retour` : le **polling du PDF** était inline → en prod, l'acheteur restait sur
  « votre rapport arrive… » sans jamais voir le bouton de téléchargement. Porté en `/flash-retour.js`.
- `/reset` : la barre de robustesse du mot de passe (STRENGTH_JS inline) → `/parcours.js`.

Tests : `tests/test_cgv_bouton.py` (aucun JS inline sur les 4 pages, bouton cliquable, JS servi).

---

## E4 — INVENTAIRE ET RECETTE DES ÉCRANS D'ENTRÉE

Routes réelles (depuis le code, pas inventées) et recette par état (TestClient, env pilote) :

| # | Écran | Route | États recettés | Verdict |
|---|---|---|---|---|
| 1 | Connexion | `GET/POST /login` | page OK ; mauvais mdp → 401 ; pilote → 303 ; rate-limit (log « connexion refusée ») | ✓ |
| 2 | Invitation client | `GET/POST /invitation` | valide (349·12 mois·CGV) ; sans token/token bidon → 404 « introuvable » ; **email déjà actif → refus** `ValueError « existe déjà (statut actif) »` | ✓ |
| 3 | Souscription Intégral | `POST /invitation` → `/onboarding/paiement` → `/onboarding/retour` | token frais + CGV → **303 `/onboarding/paiement`** ; retour ok=1 « bienvenue · Intégral actif » ; ok=0 « interrompu » | ✓ |
| 4 | Flash (public) | `GET/POST /flash`, `/flash/retour`, `/flash/statut`, `/flash/telecharger` | accueil (79 € · IDU) ; IDU < 14c → « introuvable · 14 » ; IDU 14c connu → recap+prix ; retour → JS externe | ✓ (voir PE-004) |
| 5 | Mot de passe oublié | `GET /reset`, `POST /reset-demande`, `POST /reset` | demande self-service ; token → écran mdp ; token invalide → 400 « lien expiré » | ✓ (voir PE-003) |
| 6 | Essai 48 h | `POST /admin/licences/creer-essai` → login | compte actif à échéance → « accès d'essai ouvert » ; à l'échéance, bascule suspension | ✓ |
| 7 | Régularisation | `POST /login` (compte suspendu) | → écran « Abonnement à régulariser » + lien de paiement | ✓ |
| 8 | Déconnexion / session | `GET /logout` | 302 → `/login`, session révoquée en base | ✓ |
| 9 | Activation admin | `GET/POST /invitation` (interne) | écran dédié sans paiement (E2) | ✓ |
| — | Légales | `GET /cgv`, `/mentions-legales`, `/confidentialite` | 200, offres à jour (349/79/12 mois) | ✓ |

**Écrans morts / doublons / inatteignables** : aucun. Le `POST /reset` apparu en double au grep
est en fait `/pipeline/columns/reset` (préfixe du routeur CRM) — pas de conflit avec `/reset`.

### Décision E4.5 — e-mail de réinitialisation
La page `/reset-demande` **envoie déjà un e-mail automatique** via le transport SMTP transactionnel
(`labuse.mail.send_email_async`), pas via Vic à la main. **Décision : on garde l'automatique** — un
reset de mot de passe est transactionnel (self-service, immédiat), l'attente d'un envoi manuel
serait un cul-de-sac. Les 8 templates **Brevo** restent réservés au cycle de vie commercial
(essai, souscription, onboarding, relance carte, suspension…), pas au reset. Sans SMTP configuré,
l'envoi est journalisé (file d'attente dev) sans jamais rien prétendre.

### Findings E4
- **PE-001** (RÉSOLU E1/E2) — admin voyait « Illimité · 499 € » + tunnel de paiement (racine ci-dessus).
- **PE-002** (RÉSOLU E3) — CSP bloquait le JS inline : case CGV figée, polling PDF Flash invisible,
  barre de robustesse morte.
- **PE-003** (TRANCHÉ E4.5) — reset : e-mail automatique conservé (SMTP transactionnel).
- **PE-004** (mineur, ouvert) — `/flash` ne distingue pas « IDU hors des 24 communes couvertes »
  d'« IDU introuvable » (même message). Amélioration UX possible ; faible priorité.
