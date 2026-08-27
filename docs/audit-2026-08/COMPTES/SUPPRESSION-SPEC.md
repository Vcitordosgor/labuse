# SUPPRESSION & RÉTENTION DES COMPTES — CONSTAT + SPÉCIFICATION (V2, non implémenté)

> Mandat AUDIT COMPTES · A6. **Ce document ne modifie rien** : constat de l'état réel + spec
> conforme RGPD, à trancher par Vic. Aucune implémentation dans ce mandat.

## 1. État réel aujourd'hui

### Deux mécanismes distincts

| Mécanisme | Code | Effet |
|-----------|------|-------|
| **Suppression d'un utilisateur** | `comptes.py:420` `supprimer_utilisateur(email)` · CLI implicite | Anonymise l'audit de l'utilisateur (`evenements_compte.utilisateur_id = NULL`, detail `[efface RGPD]`), `DELETE FROM utilisateurs` (sessions en cascade). Si le compte n'a plus d'utilisateur → `statut='resilie'` (le compte-coquille RESTE en base). |
| **Effacement du compte entier** | `comptes.py:443` `effacer_compte_rgpd(email)` · CLI `labuse effacement-rgpd --oui` | Anonymise tout l'audit du compte, `DELETE FROM comptes` → cascade FK. |

### Suspension ≠ suppression (déjà distinctes, mais implicites)

- **Suspension réversible** : `statut ∈ {suspendu, paiement_requis}` — la session est refusée
  (`session_utilisateur`), **les données restent intactes**, réversible (`reactiver_compte`).
  C'est le mécanisme de D4 (dashboard) et de l'essai expiré (D9).
- **Résiliation logique** : `statut='resilie'` — posé quand le dernier utilisateur est supprimé.
  Le compte-coquille survit (aucune purge de données).
- **Effacement physique** : `effacer_compte_rgpd` — le seul qui supprime réellement des lignes.

### Défauts constatés (→ findings AC-003, AC-005)

1. **AC-003 🟠 — Effacement INCOMPLET.** `effacer_compte_rgpd` compte sur la cascade FK, mais
   **12 tables à `compte_id` n'ont pas de FK cascade** vers `comptes` (cf. A3) :
   `copilote_conversations` (+`copilote_messages`), `veilles`, `veille_reprise`, `ia_log`,
   `usage_events`, `retours`, `licence_mails`, `notif_prefs`, `notif_canaux`, `share_links`,
   `lettre_zonage_refs` (`evenements_compte` est anonymisé exprès). Ces lignes **survivent** comme
   orphelins. Le **contenu personnel** (texte des conversations Copilote) et les **liens de
   partage** `/p/{token}` encore résolvables ne sont **pas** effacés → droit à l'effacement RGPD
   non honoré.
2. **AC-005 🟡 — Pas de délai de grâce, pas d'auto-service, pas de confirmation 2 temps.**
   L'effacement est immédiat et définitif (CLI admin `--oui`). Aucune fenêtre d'annulation, aucun
   parcours client de demande d'effacement, aucune double confirmation.
3. **AC-006 🟡 — Pas de politique de rétention documentée.** Rien ne dit ce qui doit survivre pour
   raisons comptables (factures) ni combien de temps. `ia_log` (ledger de facturation IA) serait
   purgé par une purge naïve, alors qu'il peut devoir être conservé (agrégé/anonymisé).

## 2. Spécification proposée (RGPD-conforme)

### 2.1 Trois états explicites (nommer ce qui existe déjà + le manquant)

```
actif ──suspend──► suspendu ──réactive──► actif           (réversible, données intactes)
  │                    │
  │                    └──demande d'effacement──► en_effacement (délai de grâce 30 j)
  │                                                    │
  └──────────────────────────────────────────────────►│──30 j──► EFFACÉ (purge physique)
                                                        └──annule──► actif/suspendu
```

- **`suspendu`** (existe) : réversible, données intactes. Suspension manuelle (D4) ou essai
  expiré (D9). *Aucune purge.*
- **`en_effacement`** (NOUVEAU) : le client (ou Vic) a demandé l'effacement ; horodaté
  `efface_demande_at`. Accès coupé, données encore là. **Délai de grâce 30 jours** (config) pendant
  lequel l'effacement est **annulable** (retour à `suspendu`). Un e-mail de confirmation part à la
  demande ET à l'échéance.
- **`EFFACÉ`** : à l'échéance du délai, un job (cron quotidien) purge physiquement. Le compte
  disparaît, un enregistrement d'audit **anonyme** subsiste (`compte_efface_rgpd`, sans identité).

### 2.2 Purge COMPLÈTE (corrige AC-003)

Deux options, la première recommandée :

- **Option A (recommandée) — poser les FK cascade manquantes.** Ajouter
  `FOREIGN KEY (compte_id) REFERENCES comptes(id) ON DELETE CASCADE` sur les 11 tables listées
  (toutes sauf `evenements_compte`, anonymisé). Alors `DELETE FROM comptes` emporte tout,
  atomiquement. Symétrise l'incohérence `agent_runs` (a la FK) vs `copilote_conversations` (ne
  l'a pas). Migration idempotente dans `ensure_scoping` (le patron existe déjà pour 14 tables).
- **Option B — purge explicite table par table** dans `effacer_compte_rgpd` avant le `DELETE
  comptes`. Plus verbeux, plus fragile (une table oubliée = orphelin), mais ne touche pas au schéma.

### 2.3 Ce qui doit SURVIVRE (rétention légale/comptable)

| Donnée | Rétention | Traitement à l'effacement |
|--------|-----------|---------------------------|
| Factures / paiements | Chez **Stripe** (obligation comptable 10 ans) | Rien à faire côté LABUSE — nous ne stockons pas les données de carte ; `stripe_customer_id` part avec le compte. |
| `ia_log` (ledger conso IA) | Utile à la facturation / au pilotage | **Anonymiser** (`compte_id → NULL`) plutôt que supprimer : garde les montants agrégés sans rattacher à une personne. |
| `evenements_compte` (audit légal) | Trace des actions sensibles | **Déjà anonymisé** (`utilisateur_id`/`compte_id → NULL`, `detail='[efface RGPD]'`). Conserver. |
| Courriers **postés** (`courrier_demandes` statut `poste`) | Preuve d'un envoi effectué (adressage générique, jamais d'identité de particulier) | À trancher : anonymiser `compte_id → NULL` en gardant la trace de l'envoi, OU purger. Recommandation : anonymiser (léger, utile au litige). |
| Contenu personnel (conversations Copilote, veilles, filtres, projets, CRM, notifs, share_links) | Aucune | **Purger** intégralement (Option A). |

### 2.4 Parcours (proposition)

1. **Demande** : bouton « Supprimer mon compte » côté client (auto-service) → `en_effacement`,
   e-mail de confirmation avec lien d'annulation valable 30 j. OU demande à Vic (dashboard).
2. **Grâce** : 30 j, réversible en un clic (retour `suspendu`).
3. **Effacement** : cron quotidien purge les comptes `en_effacement` dont `efface_demande_at + 30 j
   < now()`. Anonymise `ia_log`/`evenements_compte`/courriers postés, `DELETE FROM comptes`
   (cascade complète, Option A). Log `compte_efface_rgpd` anonyme.
4. **Confirmation** : e-mail « votre compte et vos données ont été supprimés ».

### 2.5 Config proposée

```
efface_delai_grace_jours: int = 30     # fenêtre d'annulation
efface_auto_service: bool = False      # bouton client (défaut off : Vic pilote en V2)
```

## 3. Priorité

- **AC-003 (purge incomplète)** est la seule à toucher un enjeu de **conformité réel** (contenu
  personnel non effacé) — à corriger en priorité si une demande d'effacement arrive avant le VPS.
  L'Option A (FK cascade) est ~1 h de travail + test, à faire dans un mandat dédié.
- Le délai de grâce, l'auto-service et le cron d'effacement sont du confort produit (V2).
- **Décision de Vic** sur : auto-service oui/non, durée de grâce, sort des courriers postés.
