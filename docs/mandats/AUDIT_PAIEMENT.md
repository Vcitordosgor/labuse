# AUDIT TOTAL PAIEMENT, AUTH & DESIGN D'ENTRÉE — rapport (avant bascule live)

**Branche `commerce/audit-paiement` · tout en MODE TEST · Vic merge.** Deux postures :
l'auditeur adversarial (A-D, faites) puis le designer senior (E, maquettes → verdict Vic).

## ⟪ CURSEUR ⟫ **STOP FINAL — A-D auditées + E (design d'entrée) implémentée et vérifiée**

Chaque faille : un test qui échouait → corrigé → le test RESTE (régression permanente).
Suite **1119/0** (18 skips environnementaux), golden **116/116 avec auth active**, headers
de sécurité live. Partie E livrée : design system `coffre_ui`, 9 surfaces refondues, écran de
bascule Checkout protégé par jeton HMAC signé (+ son test de régression). **Verdict : GO** (§6).

---

## 1. Tableau des attaques (A-D)

### A — Sécurité de l'accès
| Attaque | Résultat |
|---|---|
| **IDOR multi-tenant** : compte B lit/modifie/supprime/exporte projets, CRM, veilles de A via un id d'URL | **FAILLE CRITIQUE CORRIGÉE** (SEC-IDOR) — cloison `compte_id` sur 5 tables, tout scopé, 404 partout |
| **CRM globalement mono-tenant** : `UNIQUE(parcel_id)` empêchait deux comptes de suivre la même parcelle | **FAILLE CORRIGÉE** — clé rekeyée `(compte_id, parcel_id)` |
| Statuts × routes : invite/suspendu/résilié dehors, paiement_requis/actif dedans | Vérifié, tient (décidé à CHAQUE requête) |
| Session après révocation (résiliation → requête suivante tombe ; reset → sessions tombent) | Vérifié, tient (re-prouvé HTTP) |
| Tokens rejoués / consommés / expirés / forgés | Vérifié, tient (refusés sans fuite) |
| Brute-force : verrou 5 échecs, non contournable par casse d'email | Vérifié, tient |

### B — Cycle de vie Stripe
| Attaque | Résultat |
|---|---|
| Webhook non signé / mal signé | Vérifié, tient (rejet sec) |
| **Webhook rejoué** (Stripe réessaie en vrai) | **DURCI** (ROB-B) — dédup par event id (table `stripe_events`) : rejeu ignoré, pas de double activation/re-suspension |
| **Paiement réussi mais webhook JAMAIS reçu** (le pire cas commercial) | **FILET AJOUTÉ** — réconciliation au login (interroge Stripe : souscription active → activation, pas de relance Checkout ⇒ pas de double paiement) |
| Ordre inversé (invoice.paid avant liaison customer) | Vérifié, tient (no-op puis activation, état final correct) |
| FLASH : payer puis fermer avant génération | **DURCI** — généré par le webhook ; lien RÉCUPÉRABLE via session_id (DB-backed, plus de mémoire process — corrige le piège multi-worker du mi-course) |
| FLASH : lien rejoué après 30 j / télécharger un autre IDU / double paiement | Vérifié/durci — expiration appliquée, token = 1 commande = 1 pdf, double paiement = deux commandes distinctes |

### C — Robustesse & cas limites
| Attaque | Résultat |
|---|---|
| **Double-clic / deux onglets « Payer »** → deux souscriptions | **DURCI** (ROB-C) — une seule active (COALESCE garde la 1ʳᵉ ; le doublon entrant est annulé chez Stripe) |
| Multi-worker : le poll Flash change de worker | Durci (DB-backed) + testé |
| Entrées hostiles : email malformé/unicode/casse/injection SQL, IDU inexistant/malformé | Vérifié, tient (4xx propres, JAMAIS un 500 nu ; tables intactes) |
| Serveur redémarré en pleine génération Flash | Vérifié, tient (reprise idempotente au poll suivant) |

### D — Conformité & hygiène
| Point | État |
|---|---|
| **RGPD effacement TOTAL** | **CORRIGÉ** (LEX-D) — le compte + toutes ses données client partent par cascade (avant : le user partait, ses projets restaient) ; audit anonymisé conservé |
| Facture Stripe française | invoice_creation activée sur Flash + pied de facture (mention fiscale) ; **identité EI+SIREN à compléter dans les réglages Stripe — Vic** |
| Consentement CGV horodaté/versionné/retrouvable | Vérifié + CLI `cgv-preuve` (preuve exportable) |
| Aucune donnée de carte côté LABUSE | Vérifié (Checkout hébergé ; aucune colonne carte en base) |
| 500 sans fuite de stack, headers de sécurité, voie QA sans trou | Vérifié + middleware headers (défense en profondeur) |

## 2. Corrections & leurs tests de régression
- **SEC-IDOR** → `tests/test_audit_secu.py` (isolation projets/CRM/veilles, matrice statuts, tokens, brute-force, entrées hostiles).
- **ROB-B / ROB-C** → `tests/test_audit_stripe.py` (rejeu, ordre, réconciliation via concurrence, FLASH récupérable/cloisonné/expirable).
- **LEX-D** → `tests/test_audit_conformite.py` (RGPD cascade, CGV, no-card, no-stack-leak, headers, QA).

## 3. Conformité — ce que VIC doit trancher (hors code)
1. **TVA** (point dur) : le MRR visé dépasse la franchise en base (293 B) dans l'année. Défaut
   posé = « TVA non applicable, art. 293 B du CGI » (`config.facture_mention`) — **à trancher
   avec le comptable AVANT le premier encaissement** et basculer dès l'assujettissement.
2. **Identité EI + SIREN** : à poser dans `/mentions-legales` (placeholder explicite) ET dans
   les réglages de compte Stripe (pour la facture).
3. **Relecture CGV** : passage avocat recommandé avant les premières signatures.

## 4. Design d'entrée (partie E) — IMPLÉMENTÉ

Maquettes validées (`docs/mockups/auth/`) portées en production sur un **design system unique** :
`src/labuse/api/coffre_ui.py`. Principe : **design ≠ mécanique** — la nuit « Coffre » est refaite,
la mécanique de paiement auditée (A–D) n'est **jamais** touchée.

- **Source unique du dessin** : tokens en variables CSS (`coffre_ui.CSS`), **zéro hex épars** dans
  les pages ; `auth.login_page` et tout `onboarding.py` rendent à travers `coffre_ui.page(...)`.
  auth.py passe de ~130 lignes de CSS inline à un appel au module (diff : −165/+50 environ).
- **Accessibilité AA** : contraste, focus visibles, labels liés, erreurs annoncées (`role=alert`,
  `aria-live`), `prefers-reduced-motion`, jauge de robustesse mot de passe annoncée (`labStrength`).
- **Écran de bascule Checkout** (net-neuf) : entre l'acceptation CGV et Stripe, une page de confiance
  (récap 349 €/mois, 3 signaux : sécurisé Stripe / aucune donnée bancaire / facture auto + résiliation).
  Sécurité = **jeton HMAC signé** (`coffre_ui.pay_token`/`pay_cid`, TTL 30 min), pas la session : la
  page est publique par nature (atteinte juste après l'invitation, avant toute session). Route
  `/onboarding/paiement` ajoutée à `_PUBLIC`. Au POST, `creer_checkout` est appelé **inchangé**.
- **Atlas avant/après** : `docs/mockups/auth/ATLAS_PARTIE_E.md` (rendus PNG dans `rendus/`, gitignorés
  — convention atlas du dépôt : versionnés en local + `~/labuse-backups/audit-paiement-rendus/`).

## 5. Écrans/parcours que VIC valide à l'œil

Atlas complet : **`docs/mockups/auth/ATLAS_PARTIE_E.md`** (9 surfaces, avant/après, rendus réels
440×900 ×2). Les 3 écrans à fort enjeu d'abord :

| Écran | Rendu | Enjeu |
|---|---|---|
| **Bascule Checkout** (net-neuf) | `rendus/shot_bascule_checkout.png` | le point d'anxiété : rassurer avant Stripe |
| **Retour échec / succès** (net-neuf) | `rendus/shot_retour_echec.png` · `_succes.png` | « rien n'a été débité » vs « bienvenue » |
| **Flash** (confirm / génération / saisie) | `rendus/shot_flash_confirm.png` · `_gen.png` · `_APRES_flash_saisie.png` | one-shot 79 € : lisibilité + PDF |
| Porte (login) | `rendus/shot_login_defaut.png` · `_erreur.png` | la porte, erreur de couple sobre |
| Invitation | `rendus/shot_invitation.png` | jauge robustesse + consentement CGV encadré |
| Reset | `rendus/shot_APRES_reset.png` | « toutes les sessions seront fermées » |
| CGV / mentions | `rendus/shot_legal_cgv.png` | design system 760 px ; mentions corrigées (retrait « Resend ») |

Parcours à dérouler en local (mode test) : `labuse api` puis `/login`, `/invitation?token=…`,
et le tunnel invitation → CGV → **bascule** → Stripe test 4242 → `/onboarding/retour`.

## 6. Verdict go/no-go bascule — **GO (sous réserves non bloquantes de la §3)**

**GO pour la bascule live du point de vue CODE.** État à ce STOP final :

- **A–D vertes** : aucune faille d'accès/Stripe/robustesse/conformité non corrigée ; chaque
  correction gardée par un test de régression permanent.
- **E livrée et vérifiée** : suite **1119/0**, golden **116/116 avec auth active** (Partie E ne
  touche ni scoring ni données — confirmé), écran de bascule protégé par jeton signé + test
  `test_bascule_paiement_atteignable_sans_session_mais_jeton_signe` (durci contre la flakiness :
  jeton altéré déterministe, jamais 401/500, 400 gracieux sur absent/forgé/altéré).
- **Réserves = les 3 points §3, hors code, à la main de Vic** : (1) TVA — trancher art. 293 B avec
  le comptable avant le 1ᵉʳ encaissement ; (2) identité EI + SIREN dans Stripe et `/mentions-legales` ;
  (3) relecture CGV par un avocat. Aucun n'est un défaut de code ; ce sont des gestes juridico-fiscaux.

**La bascule effective (clés Stripe live, DNS, rideau) reste un mandat séparé** — ici tout est en
MODE TEST. Rien n'est mergé : Vic relit la branche, tranche les 3 réserves, puis bascule.
