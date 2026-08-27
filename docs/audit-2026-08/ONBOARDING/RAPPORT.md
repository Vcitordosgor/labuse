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

---

## E5 — COHÉRENCE STRIPE ⇄ APP

Pas de clés Stripe en local, et interdiction de toucher au LIVE → E5 = durcir le CODE pour que
l'app ne puisse jamais afficher un prix différent de celui facturé, + outiller Vic pour vérifier.

**Risque identifié** : l'app AFFICHE le prix d'`offres.py` (349/79) mais FACTURE le **Prix Stripe**
pointé par `.env` (`STRIPE_PRICE_INTEGRAL`/`_FLASH`). Rien ne garantissait qu'ils coïncident — un
price_id périmé (ancien 499, ancien montant) ferait afficher 349 et facturer autre chose.

**Corrections** :
- `provisionner()` (création des produits) lit désormais les montants d'`offres.py` (349/79) — E1.
- **Garde-fou** `_garde_coherence_prix` dans `creer_checkout` ET `creer_checkout_flash` : avant de
  créer la session Checkout, lit le Prix Stripe et, s'il diffère du prix affiché, **REFUSE** avec un
  message clair (« l'app affiche 349 € mais Stripe facturerait X € »). Tolérant à une lecture
  réseau qui échoue (ne bloque pas un paiement sur un incident transitoire ; seule une divergence
  confirmée lève). → l'app ne facture jamais un montant différent de l'affiché.
- **Commande `labuse stripe-verifie`** (lecture seule) : compare les Prix Stripe configurés aux
  offres et sort non-zéro en cas d'écart. **Vic doit la lancer contre le mode TEST puis le mode
  LIVE** (une clé à la fois) avant l'ouverture des paiements.
- Docstring de `stripe-provisionne` corrigée (mentionnait encore « Indé 290 €/Pro 490 € + founding »,
  offres mortes).

Tests : `tests/test_stripe_coherence.py` (Stripe mocké : divergence → refus ; concordance → OK).

**À VÉRIFIER PAR VIC dans le dashboard Stripe** (LIVE et TEST) :
1. `labuse stripe-verifie` → tout vert (les price_id de `.env` = 349 €/mois + 79 € unique).
2. **Aucun produit/prix fantôme** actif (anciens 499/290/490, offres Indé/Pro/Illimité/founding) —
   les archiver côté Stripe s'ils traînent.
3. Le produit Intégral est bien **récurrent mensuel**, le Flash bien **paiement unique**.

### Finding E5/E6
- **PE-005** (à arbitrer par Vic) — **l'engagement 12 mois est CONTRACTUEL (CGV) mais PAS enforced
  techniquement** : `creer_checkout` crée un abonnement Stripe mensuel simple, sans
  `subscription_schedule` de 12 mois ni verrou d'annulation. Si le portail client Stripe est activé,
  un client pourrait résilier avant 12 mois. Enforcement technique = changement côté Stripe LIVE →
  laissé à Vic (option : phase d'engagement via subscription_schedule, ou gestion à la résiliation).

---

## E6 — L'ENGAGEMENT 12 MOIS EST-IL TENU PARTOUT ?

| Surface | État |
|---|---|
| Écran d'invitation client | « engagement {12} mois » — interpolé depuis `offres.py` ✓ |
| Écran de souscription (`/onboarding/paiement`) | « Engagement 12 mois », « 349 €/mois pendant 12 mois, puis reconduction… » — interpolés ✓ |
| CGV (§5 Durée/reconduction) | durée ferme 12 mois + reconduction tacite 12 mois + clause Chatel — interpolé ✓ |
| Mail d'avis d'échéance (`emails.avis_echeance`) | texte à valeur légale L.215-1 (loi Chatel), dénonciation 1 mois avant ✓ |
| Facture/reçu | émis par Stripe (identité EI + mention fiscale via `facture_mention`) — engagement non requis sur la facture |
| Menu « Mon compte » (front) | montre le plan (libellé depuis `offres.py`, plus de fantôme) — **mais pas la date d'échéance** (PE-006) |

**Correction** : toutes les mentions « 12 mois » des écrans de souscription, jusque-là **en dur**,
sont désormais interpolées depuis `offres.py` (`engagement_mois`) — une seule source. Le libellé de
plan du menu « Mon compte » lit aussi `offres.py` (fin du « Essentiel » vestigial ; `interne`→« Interne »).

**Mécanique avis d'échéance (Chatel)** : `avis_echeance_dus` s'ancre sur la **date d'activation**
de l'abonnement (pas la création), calcule les **anniversaires annuels** (activation + k×12 mois),
déclenche dans la fenêtre Chatel [≈1 mois, ≈3 mois] avant l'échéance, avec **dédup par terme** —
cohérent avec un engagement annuel. La commande `labuse avis-echeance` est **cronée** (VPS,
`labuse-avis-echeance`, quotidien 08:30 heure Réunion). Gelé par `tests/test_engagement.py`.

### Finding E6
- **PE-006** (mineur, ouvert) — le menu « Mon compte » du front ne montre pas la **date d'échéance /
  de reconduction** au client. À surfacer (le mécanisme d'échéance annuelle existe déjà côté serveur) ;
  dépend du branchement du palier par compte (`plan_par_compte`, aujourd'hui stubbé) → mandat « Auth
  & Plans ». Noté pour Vic.

---

## E7 — MOBILE

Recette réelle des pages du parcours à **390 px** (Playwright, chromium headless, deviceScaleFactor 2).
Captures dans `docs/audit-2026-08/ONBOARDING/captures/*-390.png` (invitation client, activation admin,
flash, reset ×2, retour paiement, CGV).

**Résultat visuel** : layout responsive impeccable — **aucun débordement horizontal** (scrollWidth
= 390 sur toutes les pages), conteneur `.bloc` en 100 %/max-width, boutons pleine largeur, cibles
tactiles ~39 px, CGV lisible. L'écran d'invitation client affiche bien « Intégral · 349 €/mois ·
engagement 12 mois » ; l'écran admin « Activer votre accès administrateur · aucun paiement ».

**DEUX bugs mobiles/DA trouvés et corrigés** (des raccourcis CSS `font` invalides, silencieusement
ignorés depuis toujours) :
- **PE-007** — `input{font:15px inherit}` : raccourci **invalide** (`inherit` n'est pas une
  font-family de raccourci) → **règle ignorée**, les champs tombaient au défaut navigateur **~13 px**
  (< 16 px) → **zoom au focus sur iOS Safari** (le formulaire « saute »). Corrigé en **longhand**
  `font-size:16px;font-family:inherit` (vérifié : computed 16 px sur tous les champs texte).
- **PE-008** — titres/prix `font:… 'Space Grotesk',inherit` : le `,inherit` **invalidait** la règle
  → la **police d'identité LABUSE (Space Grotesk) ne s'appliquait pas** (repli Inter). Corrigé avec
  un repli générique valide (vérifié : computed `Space Grotesk` sur les `h1`).

Gelé par `tests/test_parcours_css.py` (aucun raccourci `font:…inherit`, champs 16 px, titres avec
famille valide). Le Checkout Stripe et le téléchargement PDF iOS sont hébergés/gérés par Stripe et
le navigateur ; le retour de paiement (`/onboarding/retour`, `/flash/retour`) est recetté ci-dessus
et son JS de polling est CSP-safe depuis E3.
