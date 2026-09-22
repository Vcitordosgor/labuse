# VEILLE-FIX-1 — Les veilles tournent, et ne préviennent que qui est concerné

**Branche** `feat/veille-audit-1` · **hash de départ** `32db3b1e` (après [[VEILLE-AUDIT-1]]) ·
**worktree** `~/Desktop/labuse-veille` · **un commit par lot** · **date** 22/09/2026 · **modèle** Opus ·
transport neutralisé (dry-run, `BREVO_API_KEY`/SMTP absents) · objets `[AUDIT-TEST]` purgés.

Correctifs des cinq trous nommés par l'audit. Commits :
`c20c49f0` (Lot 1) · `f1182c7d` (Lot 2) · `9642346d` (Lot 3) · `f08a5607` (Lot 4) · `1df0b12d` (Lot 5).

---

## Lot 1 — Le registre (bloquant) : les 4 veilles du matin ont un job, et ça FONCTIONNE

Retirer les crons legacy éteignait quatre fonctions que le registre CRON-1 ne portait pas. Ajoutées à
`jobs.py` (raison FR, `touche=exploitation`, `test=`, créneau matinal 07:00 Réunion — évaluateurs d'abord,
digest après) + implémentations `jobs_impl.py` :

| Job (crontab) | cron_utc | impl → fonction | envoie mail |
|---|---|---|---|
| `evaluer-suivis` | `2 3 * * *` (07:02) | `evaluer_suivis` (parcelles suivies) | non |
| `evaluer-secteurs` | `3 3 * * *` (07:03) | `evaluer_tous_secteurs` (zones dessinées) | non |
| `detect-events` | `4 3 * * *` (07:04) | `detect_events` (recherches sauvegardées + bascules) | non |
| `digest` | `15 3 * * *` (07:15) | `envoyer_digests` (digest du matin, chaînes 1+2) | oui |

**`detect-events` — correctif du prédécesseur.** Le prédécesseur du run servi est le run calculé JUSTE
AVANT lui (`computed_at <`), jamais « le dernier autre run » (un candidat non promu calculé *après* le
servi → un diff à l'envers qui fabrique des bascules fantômes). Mesuré : le mauvais couple
`q_v14→q_v11_m137` produisait 2000 bascules ; le bon `q_v10_m129→q_v11_m137`, 169 (le vrai passage servi).
Idempotent par `(kind, idu, run_from, run_to)`.

**Verrou V8a** — « toute veille et tout envoi a un job du registre ». Casse si une fonction d'évaluation
(suivis/secteurs/recherches/veilles/sentinelle) ou d'envoi (digest/Radar) n'a pas de job au registre, ou
si l'impl du job ne l'appelle pas (suit un niveau de délégation, ex. `sonde_sources → sentinelle_sources
→ sentinelle.passer`). Prouvé cassé (retrait du job `digest`) puis vert. Note dans
`retirer_crons_legacy.sh` : deploy.sh joue les verrous avant de poser — ne retirer le legacy qu'après un
V8a vert.

### La sortie des quatre exécutions (base réelle, commande EXACTE du crontab, transport neutralisé)

```
>>> labuse jobs run evaluer-suivis
    RUN 1 exit=0 statut=ok  compteurs={"total":3,"mutation":2,"permis":1,"bodacc":0,"zonage":0}
    RUN 2 exit=0 statut=ok  compteurs={"total":0,"mutation":0,...}          ← idempotent
>>> labuse jobs run evaluer-secteurs
    RUN 1 exit=0 statut=ok  compteurs={"scopes":3,"alertes":491,"notifications":4}
    RUN 2 exit=0 statut=ok  compteurs={"scopes":3,"alertes":0,"notifications":0}   ← idempotent
>>> labuse jobs run detect-events
    RUN 1 exit=0 statut=ok  compteurs={"run_from":"q_v10_m129","run_to":"q_v11_m137","bascule":169,...}
    RUN 2 exit=0 statut=ok  compteurs={...,"bascule":0,...}                 ← idempotent
>>> labuse jobs run digest
    RUN 1 exit=0 statut=dry-run  compteurs={"envoyes":0,"ignores":13,"echecs":0,"simules":3}
    RUN 2 exit=0 statut=dry-run  compteurs={"simules":3}                    ← mail_queue dédup, 0 nouvelle ligne
```

**Effet sur le cas `[AUDIT-TEST]`** (comptes 72/73) : événement en base + cloche (event_log
`parcelle_suivie` « Vente : votre parcelle CY0018 a changé de mains » + `veille_zone`) + **ligne
`mail_queue`** (digest_quotidien, `en_attente`, dry-run = rien envoyé). Détail :
`captures/veille-fix1/lot1-quatre-jobs.txt`.

> ⚠️ **Note shared-base.** `detect-events` sur la base partagée crée les bascules réelles du run servi
> (169) — dans une prod saine elles existent déjà (créées à la promotion → 0 nouvelle, idempotent). Sur la
> base de dev (run servi dont les bascules n'avaient jamais été générées) elles sont créées à la première
> exécution ; les lignes de test ont été purgées après mesure.

---

## Lot 2 — Radar selon les critères

Le digest Radar (template 12 `radar_digest`) partait à **tous** les comptes actifs. **Retiré.** Ne reste
que l'alerte de veille (template 13 `radar_alerte`) : un client ne reçoit un mail QUE si une de ses veilles
Radar matche ≥1 annonce du jour, avec seulement ces annonces-là ; aucune veille qui matche → aucun mail
(`pige/digests.py`).

Preuve `test_pige_digests::test_radar_trois_comptes_deux_veilles_un_sans` : 3 comptes, 2 veilles (communes
distinctes), 1 sans veille → 2 alertes au bon contenu (1 annonce chacune), 0 au troisième. Live
(`captures/veille-fix1/lot2-radar-cible.txt`) : 1 annonce → 1 alerte au compte à veille, **0 broadcast**,
0 au compte sans veille (contre 6 mails broadcast avant le correctif).

---

## Lot 3 — Essai expiré

Un compte resté `actif` mais dont `essai_expire_at` est passé recevait encore les mails. Garde ajoutée aux
**deux** points d'envoi (`_clients_actifs` pour Radar, recipients de `envoyer_digests` pour le digest) :
`essai_expire_at IS NULL OR essai_expire_at > now()`. Test `test_essai_expire_exclu_de_tout_envoi` : deux
comptes actifs à veille, l'un essai expiré (hier), l'autre valide (dans 30 j) → seul le valide reçoit.

---

## Lot 4 — La cloche d'un compte neuf ouvre à 0

Les événements de marché (broadcast `bascule`/`bodacc`/`match`, `compte_id NULL`) étaient comptés non-lus
pour **tous** les comptes : un compte neuf ouvrait la cloche à ~1250 non-lues (mesuré 1254 à l'audit). Le
fragment `_seen` (`api/events.py`) compte désormais LU d'office un événement de marché ANTÉRIEUR à
`compte.created_at` — count, liste et tri corrigés d'un seul geste ; le bucket pilote (NULL) n'est pas
concerné. Test `test_cloche_compte_neuf_a_zero` : compte neuf + 3 bascules marché antérieures → **0** ;
une bascule marché postérieure → **1**. Live : un compte créé à l'instant ouvre à **0**.

---

## Lot 5 — La trace : les mails de veille passent par mail_queue

L'alerte Radar partait par `mail.envoyer_template` en direct, hors `mail_queue` (aucune trace ; le mandat
« mail_log » de l'audit ne les voyait pas). Les deux mails de veille passent désormais par
`mailfile.envoyer_mail` **comme les autres** : une ligne `mail_queue` par envoi, dédup par jour, échec
bruyant conservé. Deux ajouts à `mailfile.py` : le **mail brut** (`params['__raw']`, `template_id` NULL)
pour le digest du matin (HTML construit côté code, départ SMTP par la file) ; la garde **`dry_run`**
(la ligne est écrite `en_attente`, sans `prevu_at` → le worker des programmés ne la fera jamais partir).
« Dry-run = une ligne écrite, rien envoyé. » Test `test_lot5_dry_run_ecrit_une_ligne_mail_queue_rien_envoye`
+ live (`captures/veille-fix1/lot5-trace-mailqueue.txt` : ligne `radar_alerte` template 13, `en_attente`).

---

## Portes

- **tsc -b** : vert (aucune modification frontend).
- **pytest tests/** (base `labuse_test` propre) : **3006 passés, 66 skipped, 0 échec** hors `tests/verrous/`
  (exécuté séparément). ⚠️ Les échecs vus au premier passage venaient d'un `labuse_test` **encrassé** par
  des résidus de runs antérieurs (biens saisis « aujourd'hui » non purgés) — nettoyés ; les tests neufs
  ont été rendus robustes au résidu (communes de test uniques, plus d'assertion sur un compteur global).
  Aucun échec nouveau imputable au code.
- **labuse circuit verrous -w G8** : **V8a vert** (« 7 fonctions de veille/envoi, chacune portée par un
  job »), tous les verrous et garanties verts SAUF **V1c** et **G8** — tous deux **pré-existants, hors
  périmètre** :
  - **V1c cassé** = 3 tables orphelines `ingestion_delta`, `score_labuse`, `score_labuse_runs` de
    **SCORING-6** (non mergé), présentes dans la base partagée mais absentes de la carte de cette branche.
    Aucun rapport avec VEILLE-FIX-1 (qui ne crée aucune table).
  - **G8 avertissement** (non bloquant, `-w G8`) = sources sans contrôle récent, agent plafonné à 0 € —
    état d'exploitation pré-existant.

Aucun envoi réel. Objets `[AUDIT-TEST]` et lignes `mail_queue` de test purgés ; base rendue à l'identique.
