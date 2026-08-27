# AUDIT COMPTES & CLOISONNEMENT — RAPPORT

> Mandat AUDIT COMPTES & CLOISONNEMENT (27/08/2026). Branche `audit/comptes-cloisonnement`
> (depuis `e0732190`, qui inclut le merge du dashboard admin). LABUSE n'avait jamais eu qu'un
> seul compte réel : ce mandat est le **premier test à deux comptes clients coexistants** —
> le dernier angle mort avant la vente.
>
> **Méthode.** L'audit empirique (A2, A5, A7) est mené sur la base de test `labuse_test` via
> un `TestClient` FastAPI in-process, **auth active** (env pilot + secret), **comptes et
> sessions réels** (mêmes tables, même code, même cloison que la prod). Arbitrage : NE PAS
> opérer sur la base servie par l'uvicorn `:8000` en route — pour ne rien polluer ni risquer
> sur le serveur vivant (règle « ne tue rien »). La purge finale est vérifiée en SQL sur
> `labuse_test`. Les objets créés sont de vraies lignes SQL, l'attaque de cloison est réelle.

## Gravités
🔴 fuite / faille exploitable (corrigée dans ce mandat) · 🟠 durcissement recommandé (risque
réel non exploité) · 🟡 constat / dette / amélioration UX-sécurité (documenté, décision Vic).

---

## A1 — INVENTAIRE DU CYCLE DE VIE (constat)

Tableau de l'état RÉEL aujourd'hui, mécanisme par mécanisme. Verdicts : ✅ existe et sain ·
⚠️ existe mais bancal · ❌ absent.

| # | Mécanisme | État | Chemin de code | Comment ça marche / défaut |
|---|-----------|------|----------------|----------------------------|
| 1 | **Création de compte** | ✅ (invitation only) | `comptes.py:118` `creer_invitation` · endpoint `dashboard.py` `admin_licence_creer` · UI `onboarding.py:41` | Par INVITATION admin uniquement (pas de self-service). Crée `comptes` (statut `invite`) + `utilisateurs` (rôle `titulaire`, statut `invite`). Token SHA-256 en base, **7 jours**, usage unique. Lien envoyé à la main. |
| 2 | **Première connexion** | ✅ | `onboarding.py:79` `invitation_submit` · `comptes.py:163` `activer_par_invitation` | L'invité pose SON mot de passe (min 10 c.) + accepte CGV horodatées. Token consommé, utilisateur → `actif`. Le compte reste `invite` jusqu'au paiement Stripe. Pas de mot de passe provisoire (l'invité le choisit d'emblée). |
| 3 | **Changer son mot de passe (connecté)** | ❌ **ABSENT** | — (aucun endpoint) | Un utilisateur connecté **ne peut pas** changer son mot de passe : il doit passer par le flux « oublié » (reset), qui tue toutes ses sessions. Lacune UX-sécurité. → **AC-010 🟡** |
| 4 | **Mot de passe oublié (reset)** | ✅ (anti-énumération) | `comptes.py:282` `demander_reset` / `299` `appliquer_reset` · `onboarding.py:237/274` | POST `/reset-demande` (email). Token SHA-256, **60 min**, usage unique. Réponse identique que l'email existe ou non (anti-énumération). Application : nouveau mdp (min 10 c.), **toutes** les sessions du compte révoquées, compteur d'échecs remis à 0. Pas d'e-mail de confirmation post-reset. |
| 5 | **Durée / expiration de session** | ⚠️ | `comptes.py:230` `creer_session` · `config.py:51` `session_hours=12.0` | Token SHA-256 en base, `expire_at = now()+12 h` (config `LABUSE_SESSION_HOURS`). Cookie httpOnly/SameSite=Lax/Secure. Vérifié à CHAQUE requête (`expire_at > now()`). **Pas de renouvellement glissant** ; **pas de purge des sessions expirées** (lignes mortes en base). → **AC-011 🟡** |
| 6 | **Déconnexion** | ✅ | `app.py` `logout` · `comptes.py:275` `detruire_session` | `/logout` fait `DELETE FROM sessions_auth WHERE token_hash` — **révocation serveur immédiate**, pas seulement le cookie (un cookie rejoué ne rouvre pas l'accès). |
| 7 | **Verrouillage après échecs** | ✅ | `comptes.py:186` `verifier_login` · `config.py:188` `login_echecs_max=5`, `login_verrou_minutes=15` | 5 échecs → verrou 15 min (`verrouille_jusqu_a`). Message JAMAIS différencié (« e-mail ou mot de passe incorrect »). Pas de déverrouillage admin manuel (attendre 15 min ou SQL). → **AC-012 🟡** |
| 8 | **Suppression de compte** | ✅ (RGPD réel) | `comptes.py:422` `supprimer_utilisateur` / `443` `effacer_compte_rgpd` · CLI `effacement-rgpd` | Deux niveaux : suppression d'un utilisateur (anonymise l'audit, DELETE utilisateur, compte → `resilie` s'il devient vide) ; effacement compte entier (`DELETE FROM comptes` → CASCADE sur les 10 tables scopées). Pas d'auto-suppression client, pas de délai de grâce, pas de confirmation 2 temps. → détaillé en **A6**. |
| 9 | **Hachage du mot de passe** | ✅ | `comptes.py:20` `PasswordHasher()` (argon2-cffi) | **argon2id** (OWASP), paramètres lib par défaut (time_cost=3, 64 MiB, parallelism=4). Rehash automatique au login si les paramètres changent (`check_needs_rehash`). |
| 10 | **Robustesse du mot de passe** | ⚠️ | `comptes.py:174` / `305` (`len < 10`) | Contrainte serveur = **longueur ≥ 10 uniquement**. Aucune complexité exigée (`aaaaaaaaaa` passe). Le front conseille « mélangez lettres, chiffres, symboles » mais ce n'est pas validé serveur. Acceptable (verrou anti-brute-force) mais non optimal. → **AC-013 🟡** |
| 11 | **Mot de passe admin** | ⚠️ (double nature) | `config.py:45` `auth_password` · `auth.py:196` `password_ok` · `auth.py:168` `exiger_admin` | Deux mondes : (a) PILOTE — mot de passe partagé `LABUSE_AUTH_PASSWORD` (clair ou `sha256:…`), session **signée HMAC sans état en base**, admin de fait ; (b) MULTI-COMPTE — utilisateur `role='admin'`. Le pilote n'a **ni verrou d'échecs ni traçabilité d'identité**. → détaillé en **A4** (**AC-020/021/022**). |

**Synthèse config** (défauts) : session 12 h · verrou 5 échecs / 15 min · token reset 60 min ·
token invitation 7 j · essai 48 h. `reset` et `invitation` sont **codés en dur** (non config).

**Verdict A1.** Authentification de fond solide (argon2id, tokens hachés en base, anti-énumération,
révocation immédiate, RGPD réel). Angles morts, tous **non bloquants** et documentés :
changer-son-mdp absent (AC-010), sessions non purgées (AC-011), pas de déverrouillage admin
(AC-012), complexité mdp non exigée (AC-013), double-nature du mdp pilote (A4). Aucune de ces
lignes n'est une fuite de cloisonnement — le cœur du mandat (A2) est traité séparément.
