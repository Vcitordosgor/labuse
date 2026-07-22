# AUDIT TOTAL PAIEMENT, AUTH & DESIGN D'ENTRÉE — rapport (avant bascule live)

**Branche `commerce/audit-paiement` · tout en MODE TEST · Vic merge.** Deux postures :
l'auditeur adversarial (A-D, faites) puis le designer senior (E, maquettes → verdict Vic).

## ⟪ CURSEUR ⟫ **STOP MI-PARCOURS — A-D livrées, maquettes d'auth à trancher par Vic**

Chaque faille : un test qui échouait → corrigé → le test RESTE (régression permanente).
Suite **1118/0**, golden **116/116 avec auth active**, headers de sécurité live.

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

## 4. Design d'entrée (partie E)
_Les maquettes sont dans `docs/mockups/auth/` (STOP mi-parcours). Après verdict Vic :
implémentation + atlas avant/après._

## 5. Écrans/parcours que VIC valide à l'œil
_(liens + commandes — complété au STOP final)._

## 6. Verdict go/no-go bascule
_(complété au STOP final ; à ce stade : A-D VERTES, aucune faille non corrigée ; réserves =
les 3 points Vic de la section 3, non bloquants pour le code)._
