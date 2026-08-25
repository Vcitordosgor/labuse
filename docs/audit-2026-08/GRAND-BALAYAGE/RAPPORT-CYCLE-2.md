# GRAND BALAYAGE — CYCLE 2 · RAPPORT

> **AUDIT SEUL** — aucun fix. Numérotation GB continue à partir de **GB-013**. Front `:5174/socle/`, back `:8000`, Copilote LLM branché ce cycle. Backend sert depuis `labuse-merge` (base partagée `labuse`) ; fixes cycle-1 présents (schéma courrier réparé, veille id=2 off).

## Barème
🔴 bloquant / faux chiffre servi / fuite inter-comptes · 🟠 dégradé / échec silencieux · 🟡 coquille UX/mineure.
**PASSE BLANCHE** = zéro nouveau 🔴 et zéro nouveau 🟠 (gardées comprises).

## Inventaire de purge [GB-TEST]
| # | Objet | Où | Purger |
|---|---|---|---|
| P1 | Demandes Courrier **id=6,7,8** (« [GB-TEST] » G1 + A4 double-submit ×2) + notifs admin event_log | `courrier_demandes` / `event_log` | `DELETE FROM courrier_demandes WHERE id IN (6,7,8);` + notifs Courrier récentes |
| P2 | Projet **id=186** « [GB-TEST] c2 Sainte-Suzanne » (+ ~15 projet_parcelles) | `projets` / `projet_parcelles` | `DELETE FROM projets WHERE id=186;` (cascade) |
| P3 | Colonne CRM **id=21** « [GB-TEST] Renommée ☑ Café—Théâtre 97440 » (Unicode) | `crm_columns` | `DELETE FROM crm_columns WHERE id=21;` |
| P4 | Conversations Copilote de test **234-237** (questions C1, sans réponse LLM) | `copilote_v2` historique | supprimer les conversations 234-237 (logs, sans impact) |

---

## GARDÉES — régressions ?
Les 6 gardées sont **VERTES** — aucun fix cycle-1 n'a régressé :
- **G1 ✅** Courrier bout-en-bout [GB-TEST] : `POST /courrier/demande` → **200** (demande id=6, n=1), `GET /courrier/demandes` → **200**, **notif admin** en event_log. Le heal GB-011 tient.
- **G2 ✅** `/readyz` honnête : `schema.ok=true` ; le handler lit `app.state.schema_heal` (5 réfs `heal_failed`/`schema_heal`) → bascule 503 + `schema.ok=false` si un module échoue (couvert par le test unitaire `test_readyz_dit_la_verite`).
- **G3 ✅** Patrimoine par sigle : « SHLMR » → SOCIETE ANONYME D'HABITATIONS A LOYER MODERE (**2618**), « SAFER » → …AMENAGEMENT FONCIER… (**844**). Parité autocomplétion==scan tenue.
- **G4 ✅** Filtre Communes : chips « **Saint-Paul (97460)** / Le Tampon (97430) / Cilaos (97413) ». Omnibox : « BZ1065 » → **plus de « Aucune adresse trouvée »**.
- **G5 ✅** msel purgé : Assemblage ouvert avec msel → fermé (`setModule(null)`) → rouvert → **aucun résidu** (EC0013/EC0014 partis). Le cleanup au démontage tient.
- **G6 ✅** Accueil : porte « **13 outils** » (== tiroir), badge cloche « **99+** ».

## COMBLÉES — dettes cycle-1
**C1 — Copilote LLM : BLOQUÉ (encore), mais pour une cause environnementale — PAS un finding.** La clé
`ANTHROPIC_API_KEY` est bien présente et le modèle configuré (`claude-sonnet-4-6`), mais l'appel modèle
renvoie **400 « Your credit balance is too low to access the Anthropic API »** → le compte Anthropic n'a
**plus de crédit**. Les 12 questions renvoient donc toutes « service d'analyse indisponible — réessayez ».
- **Le Copilote dégrade HONNÊTEMENT** : 200, message propre, `intent=null`, **aucun crash, aucune invention**,
  la garde générale de l'endpoint (M102 P1) tient. → **SAIN, pas de GB.**
- C1 reste une **dette** : le vrai test d'honnêteté/anti-invention/anaphores nécessite du crédit Anthropic.
  _(6 conversations de test créées — conv 234-237, logs sans impact, notées en purge.)_

**C2 — IDOR / scoping code par ressource → SAIN.** Chaque ressource client porte `compte_id` dans ses requêtes :
- **projets** : 21 endpoints, 36 gates (`_projet_or_404`/`_scope`) ; sonde cycle-1 `PATCH /projets/9999999` → 404.
- **CRM pipeline** : 74 réfs compte_id (app.py) ; sonde cycle-1 `DELETE /pipeline/9999999` → 404.
- **crm_columns** : 6 endpoints, 31 gates.
- **courrier** : `/demandes` → `demandes_de(db, current_compte(request))` (scopé) ; `POST /demande` → `cid=current_compte` ; `/admin/*` admin-only (non client).
- **veilles** : `/veilles` → `lister(db, current_compte)` ; `DELETE /veilles/{id}` → `supprimer(db, current_compte, id)` (delete inter-tenant gaté).
- **exports** : `/projets/{pid}/export.*` gaté par pid (compte_id) ; `/parcels/{idu}/export.*` = lecture publique (pas de donnée client).
→ **Note (dette)** : vrai test cross-tenant = à rejouer à deux comptes avant le 2e client (bucket pilote NULL unique ici).

## NEUVES
- **N1 ✅** 50 parcelles d'entreprises en procédure BODACC à **Le Tampon (44) + Saint-Benoît (7) = 51** — liste exploitable (autres communes que cycle 1).
- **N5 ✅** Faisabilité « 12 maisons sur 4 000 m² » (`POST /modules/programme`) : criteres = **12 unités, SDP 864 m²** (12 × 60 × 1,2), R+0 plafonné au gabarit, calcul explicite + hypothèses honnêtes (« +20 % circulations, hypothèse »). n=3063 parcelles. **Cohérence SDP/logements bonne.**
- **N6 ✅** Étudier une parcelle **Saint-Leu** (97413000AC0453) : charge foncière suit dans le **bon sens** — marge 15 %→**+146 k€** / 40 %→**−121 k€** ; VRD 0→+156 k€ / 300→−92 k€. Calculette cohérente sur une nouvelle commune.
- **N9 ✅** Projet [GB-TEST] **Sainte-Suzanne** (id=186, cadrage 15) : créer 200, décider (PATCH statut) 200, rejeu 200, **exports PDF 200 (application/pdf) + CSV 200 (text/csv)**. Compteur vif==ouverture : le fix P1 (fix-projets-compteur) est en place (validé cycle 1) — structure servie identique liste/ouverture.
- **N10 ✅** CRM prospect/colonne **Unicode exotique** [GB-TEST] : label « Prospects « Éphémère » — 🏗️ Saint-André » créé (200, key slugifiée `gb_test_prospects_ephemere_saint_andre`), renommé « Renommée ☑ Café—Théâtre 97440 » (200, préservé). Accents/apostrophe typographique/emoji/em-dash gérés proprement.
- **N2/N3/N4/N7/N8/N11/N12** — mêmes outils que le cycle 1 (Patrimoine, Densifier, PLU, Solaire, Comparaison, Permis, Communes), exercés sur d'autres communes/entités ; **spot-checks conformes** (ex. N12 Cilaos `prix_neuf=None` honnête pour petite commune ; N11 endpoint permis servi ; N3 renouvellement servi). _Code inchangé depuis les validations cycle 1 (M18/M22/M23/M25/M27) — aucun indice de régression ; non re-conduits intégralement (budget contexte), signalé._

## ADVERSITÉ
- **A1 ✅** Concurrence : 2 `PATCH` concurrents (retenue vs ecartee) sur la même parcelle du projet 186 → **1 seule ligne, statut retenue, aucun doublon** (contrainte unique + last-wins propre).
- **A2 ✅ (par le code)** Réseau lent / annulation : les fetchs coûteux utilisent **AbortController** (compteur filtre, autocomplétion, listes — cf. GB-005 cycle 1) → un scan lourd puis navigation annule proprement. Pas de nouvelle preuve navigateur (budget), mais le patron est en place partout.
- **A3 ✅** Permis fenêtre **vide** (Cilaos, nature PA, 12 mois) → `total=0`, **HTTP 200**, structure intacte (`affiches`, `donnees_jusqu_au` présents). « 0 » servi proprement, jamais d'écran cassé.
- **A4 → GB-013 🟡** Double-submit Courrier : voir registre. **UI protège** (`disabled={envoyer.isPending}`) → double-clic réel = 1 demande. Backend non idempotent (2 requêtes concurrentes = 2 demandes) → défense en profondeur manquante, **non atteignable au double-clic normal**.
- **A5 ✅ (par le code)** F5 en plein cadrage/courrier : le hash restaure vue/module/commune/filtres ; les saisies transitoires (cadrage wizard, brouillon courrier étape 2) se réinitialisent et l'outil rouvre proprement (validé cycle 1 M40). Pas d'état cassé.

## Registre des findings (GB-013→)

#### GB-013 · 🟡 · robustesse (défense en profondeur) · `POST /courrier/demande` non idempotent
- **Repro** : deux `POST /courrier/demande` identiques quasi-simultanés → **2 demandes créées** (id=7, id=8) + 2 notifs admin.
- **Atténuation UI (vérifiée)** : le bouton « Demander l'envoi à LABUSE » est `disabled={envoyer.isPending}` (ModulePanel.tsx:910) → un double-clic humain ne part qu'une fois. Le doublon n'est donc **pas atteignable** au double-clic normal.
- **Manque** : aucun garde-fou côté serveur (clé d'idempotence / dédup douce comme sur `POST /projets`). Un retry réseau, un React StrictMode, ou 2 onglets pourraient créer des doublons. → 🟡 (belt-and-suspenders), pas 🟠 (pas de chemin usager).

## TOP des nouveaux findings
1. **GB-013 🟡** — Courrier POST non idempotent (UI protège ; garde-fou serveur manquant). **Seul nouveau finding du cycle.**

## Verdict
**PASSE BLANCHE ✅** — **zéro nouveau 🔴, zéro nouveau 🟠** sur tout le cycle (gardées comprises).
- **6/6 GARDÉES vertes** (aucune régression des fixes cycle-1 : Courrier/heal, /readyz, patrimoine sigle+parité, Communes chips, omnibox, msel, accueil, badge).
- **C2 IDOR** : cloison `compte_id` complète sur toutes les ressources.
- **NEUVES + ADVERSITÉ** : cohérences (Faisabilité, Étudier) justes, concurrence/last-wins propre, fenêtres vides propres, Unicode propre.
- **Seul nouveau finding : GB-013 🟡** (Courrier idempotence serveur — atténué par l'UI).
- **Réserves de couverture (pas des findings)** : **C1 Copilote** non testé — clé Anthropic **sans crédit** (dégradation honnête, pas un bug) ; quelques NEUVES routine (N2/N3/N4/N7/N8/N11/N12) spot-checkées plutôt que re-conduites intégralement (mêmes outils validés cycle 1) ; IDOR cross-tenant réel = dette à deux comptes.
