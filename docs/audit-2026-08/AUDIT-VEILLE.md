# AUDIT — VEILLE & NOTIFICATIONS

**Branche** : `audit/veille` · **Date** : 2026-08-24 · **Type** : audit seul (aucun code modifié, un seul rapport)
**Méthode** : 2 inventaires parallèles (déclencheurs/matcher · chaîne d'événements/mail) + vérifications personnelles (honnêteté « envoyé vs journalisé », câblage Courrier→admin, cloisonnement de la cloche, phantom des types de veille). Postgres en lecture stricte, **aucun email réel envoyé**, serveur intact.

**Verdict global** : la **plomberie est saine et honnête** — `mail.py` ne prétend jamais « envoyé » quand il journalise, le digest n'avance `last_digest_at` que sur un envoi réussi, la déduplication est robuste, le cloisonnement par compte est correct partout (cloche comprise). **MAIS** un déclencheur fantôme majeur : **3 des 4 types de veille du Copilote sont promis à l'écran (« Veille posée … notification in-app ») mais ne sont JAMAIS évalués** (seul `permis` a un évaluateur). C'est exactement le piège scoreMin, en pire (un type entier). Le mandat Courrier→Brevo est **sain** (la notif admin arrive).

---

## 1. Types de veille — promesse vs évaluation (périmètre 1 & 5)

Deux systèmes de veille INDÉPENDANTS coexistent :
- **Veilles Copilote** (`copilote_v2/veilles.py`) — par **commune**, posées via le chat.
- **Alertes de secteur** (`alertes.py`) — par **zone dessinée**, géométriques.

### 1a. Veilles Copilote (`veilles.py`)

| Type (router.py:155) | Libellé promis (TYPES) | Évaluateur réel | Verdict |
|----------------------|------------------------|-----------------|---------|
| `permis` | « permis de construire (Sitadel) » | `_nouveaux_permis()` (commune + date_dépôt) | ✓ ACTIF |
| `ventes` | « ventes (DVF) » | **aucun** | ✗ **FANTÔME (V1)** |
| `procedure_plu` | « procédures PLU (Sudocuh/annuaire) » | **aucun** | ✗ **FANTÔME (V1)** |
| `bodacc` | « BODACC sur un propriétaire suivi » | **aucun** | ✗ **FANTÔME (V1)** |

`EVALUABLES = {"permis"}` (veilles.py) ; `_EVALUATEURS = {"permis": _nouveaux_permis}`. Pour les 3 autres, `evaluer()` fait `ev = _EVALUATEURS.get(type)` → `None` → `hits = []` → **jamais de notification**, à vie.

### V1 — 3 veilles fantômes promises « notification in-app » · gravité : HAUTE
- **Le router propose les 4 types** (`router.py:155` : `veille_type ∈ permis|ventes|procedure_plu|bodacc`).
- **`_executer_veille` (copilote_v2.py:66) crée n'importe lequel** et répond : *« Veille posée : {label} · {commune} — vérification à chaque mise à jour des données, notification in-app. »* — **quel que soit le type**.
- **`veilles.creer` renvoie pourtant un flag `evaluable`** (`type_ in EVALUABLES`) — mais `_executer_veille` **l'ignore** : il confirme « posée » même pour un type qui ne s'évalue pas.
- **Conséquence** : un utilisateur qui demande « surveille les **ventes** à Saint-Paul » (ou les procédures PLU, ou le BODACC de son prospect) reçoit « Veille posée … notification in-app » et **ne sera JAMAIS notifié**. Promesse non tenue sur une fonction cœur.
- **Correctif candidat (sans le faire)** : soit **restreindre honnêtement** — `_executer_veille` refuse (ou dégrade) un type dont `evaluable` est faux (« la veille sur les ventes n'est pas encore disponible ») ; soit **implémenter les 3 évaluateurs** (les données existent : les alertes de secteur savent déjà croiser DVF/BODACC/zonage — cf. §1b).

### V3 — `criteres` stocké, jamais évalué · gravité : faible (latent)
La colonne `veilles.criteres` (jsonb) existe, mais (a) `_executer_veille` ne la remplit jamais (toujours `{}`), (b) `_nouveaux_permis` ne filtre que sur **commune** et **date**. Aucune sur-promesse ACTIVE aujourd'hui (la veille ne promet que « permis à {commune} »), mais c'est une **armature morte** : le jour où l'UI collecterait surface/tier/zonage, ils seraient silencieusement ignorés (rejouerait le piège scoreMin).

### V4 — `frequence` ignorée · gravité : faible (latent)
`veilles.frequence` (défaut `'ingestion'`) n'est **jamais lue** ; `evaluer_toutes()` évalue TOUTES les veilles à chaque passage. Sans valeur non-`ingestion` posée aujourd'hui, sans effet — mais une veille « hebdo » serait sur-déclenchée.

### 1b. Alertes de secteur (`alertes.py`) — SAINES

4 déclencheurs géométriques, tous **réellement évalués** et **cloisonnés** (`z.compte_id IS NOT DISTINCT FROM :cid`) :

| kind | détection | géométrie |
|------|-----------|-----------|
| `dvf_in_zone` | ventes DVF dans la zone | `ST_Contains` ✓ |
| `permis_in_zone` | permis Sitadel dans la zone | `ST_Contains` ✓ |
| `bodacc_in_zone` | BODACC sur PM propriétaire dans la zone | `ST_Intersects` + SIREN ✓ |
| `zonage_in_zone` | changement d'empreinte de zonage | diff snapshot ✓ |

Ironie utile pour V1 : **les alertes de secteur savent déjà évaluer DVF, BODACC et zonage** — la capacité existe, elle n'est simplement pas branchée aux veilles Copilote par commune.

### 1c. Veille PLU (`veille_plu.py`) — registre manuel, pas un déclencheur
Registre YAML curé (trimestriel, `a_reverifier()`), servi à la demande (fiche commune). Pas d'évaluation automatique — hors périmètre « déclencheur ». Sain (vigilances servies seulement si `confiance=SOURCE`).

---

## 2. Chaîne d'événements & mail — honnêteté « envoyé vs journalisé » (périmètre 2)

| Canal | Honnêteté | Vérif |
|-------|-----------|-------|
| `mail.py send_email` | ✓ retourne `SendResult(False,"no-config")` en journal, `(True,"ok")` seulement sur envoi réel, `(False,"error:…")` sur échec ; **jamais « envoyé » à tort** | mail.py:73-103 |
| **Digest** (`envoyer_digests`) | ✓ **exemplaire** : compte « envoyé » seulement si `res.ok` ; `last_digest_at` n'avance **que** sur succès (un échec Brevo ne se déguise pas en « déjà envoyé » → réessai) ; digest vide non envoyé ; adresse placeholder bloquée ; préférences par type respectées ; échec loggé+compté | events.py:1203-1217 |
| `send_email` (comptes avis-échéance, cli mail-test, annonces) | ✓ tous respectent `SendResult` (log/UI du `detail` : ok / no-config / error) | comptes.py:303, cli.py:130, events.py |
| `send_email_async` (reset mot de passe, **notif Courrier admin**) | ⚠ **N1** : jette le `SendResult` (fire-and-forget) → un envoi journalisé/échoué est **silencieux** | mail.py:106, courrier.py:119, onboarding.py:220 |

### N1 — `send_email_async` avale le résultat · gravité : faible
Deux usages : reset mot de passe et la **notif Courrier à l'admin**. Un échec (SMTP absent → journalisé, ou Brevo down) n'est pas remonté. **Atténué** : le reset affiche un message honnête via `mail_configured()` (« journalisé, zéro e-mail » en dev) ; le Courrier a un **backup fiable** (cloche + demande persistée, cf. §5). Correctif candidat : pour la notif admin, utiliser `send_email` (synchrone, résultat loggé) ou tracer `envoi_statut`.

**Brevo** : pas d'API dédiée — c'est le **relais SMTP transactionnel** (`LABUSE_SMTP_HOST` pointant sur Brevo en prod) ; tout passe par `send_email`. Le plafond Gmail (~500/j) est **détecté explicitement** (`SendResult(False,"error: quota")` + `log.error`, jamais silencieux).

---

## 3. Cloisonnement (périmètre 3) — SAIN

- **Veilles / alertes** : lecture ET notification cloisonnées. `evaluer_toutes` lit toutes les veilles mais passe **le `compte_id` de chaque veille** à `creer_notification` → jamais le mauvais compte. `evaluer_tous_secteurs` idem (`compte_id=r["compte_id"]`).
- **event_log / cloche** : `_visible` = `compte_id IS NOT DISTINCT FROM :cid OR (compte_id IS NULL AND kind = ANY(:market))`. Un event NULL n'est visible aux clients **que** si `kind` est un kind de marché. **Vérifié** : `systeme` n'est pas un kind de marché → la notif Courrier (`systeme`, `compte_id=None`, avec le nom du client dans le titre) est **invisible aux clients**, admin-only. Pas de fuite inter-clients.
- **event_seen** (vus de marché par compte) : PK `(compte_id, event_id)`, FK cascade. Mark-read SEC-IDOR (`WHERE … compte_id IS NOT DISTINCT FROM :cid`).

---

## 4. Fréquence, volumétrie, tempête, doublons (périmètre 4)

| Garde | État | Réf |
|-------|------|-----|
| **Déduplication** | ✓ robuste : `WHERE dedup=:d AND compte_id IS NOT DISTINCT FROM :c` + fenêtre (jour par défaut, ou `permanent` à vie). Rejeu du même lot = 0 doublon (veille : `dedup` = hash des réfs) | events.py:178-194, veilles.py |
| **Plafond notif** | ⚠ **V2** : `NOTIF_CAP_JOUR=50` par (kind, compte, jour). Le **51ᵉ+ est jeté SILENCIEUSEMENT** (`return 0`, WARNING log) | events.py:154,186 |
| Plafond parcelles suivies | ✓ 50/compte (409 si dépassé) | events.py:303 |
| Plafond courrier | ✓ 100/jour/sujet (refus explicite) | courrier.py |
| Rétention event_log | ✓ purge 90 j (cron) | events.py |
| Gmail 500/j | ✓ détecté explicitement (refus, log.error) | mail.py:98 |
| Digest anti-double-envoi | ✓ `last_digest_at` + intervalle ; réessai borné sur panne | events.py:1165 |

### V2 — plafond 50 notifs/jour, débordement silencieux · gravité : moyenne
Un run qui bascule 1000 parcelles pour un compte en une journée → **50 events créés, 950 jetés** (loggés WARNING, aucun event, aucune trace côté client). Le client voit 50 à la cloche/au digest et **croit tout avoir**. C'est un backstop anti-inondation légitime, mais le silence est trompeur. Correctif candidat : agréger le débordement en **un** event « + N autres aujourd'hui » (jamais 0 silencieux), ou relever le plafond pour les kinds agrégeables.

---

## 5. Câblage Courrier → admin (note du mandat) — SAIN

Sur une demande d'envoi de courrier (`POST /courrier/demande`, api/courrier.py) :
1. **Demande persistée** (`courrier_demandes`, statut `demande`) — visible dans la **vue admin** `/courrier/admin` quoi qu'il arrive.
2. **① Cloche** : `creer_notification(kind="systeme", compte_id=None, dedup="courrier:demande:{id}", permanent=True)` → feed admin (invisible aux clients, cf. §3), dédupliqué, best-effort (rollback si échoue, la demande reste).
3. **② E-mail Brevo** : `send_email_async(admin_email or mail_from, "[LABUSE] …")` — best-effort async (N1).

**Verdict** : la notification **arrive bien à l'admin** — la cloche (fiable, en base) + la demande persistée (vue admin) sont les canaux garantis ; l'e-mail Brevo est un push en plus. Aucune demande ne peut être perdue. Le seul angle à durcir : rendre l'e-mail admin non-silencieux (N1).

---

## 6. Gravités & correctifs candidats

| Réf | Constat | Gravité | Correctif candidat |
|-----|---------|---------|--------------------|
| **V1** | 3 veilles Copilote fantômes (`ventes`/`procedure_plu`/`bodacc`) : « Veille posée … notification in-app » mais jamais évaluées | **HAUTE** | gater `_executer_veille` sur le flag `evaluable` (refus honnête) OU implémenter les 3 évaluateurs (données déjà là, cf. alertes secteur) |
| **V2** | plafond 50 notifs/jour : débordement jeté en silence | moyenne | agréger en 1 event « +N autres », jamais 0 muet |
| **N1** | notif admin Courrier (et reset) par `send_email_async` : échec silencieux | faible | `send_email` synchrone + trace pour la notif admin (la cloche reste le backup) |
| **V3** | `veilles.criteres` stocké jamais évalué | faible (latent) | brancher au matcher le jour où l'UI collecte des critères, sinon retirer la colonne |
| **V4** | `veilles.frequence` jamais lue | faible (latent) | lire la fréquence dans `evaluer_toutes`, ou retirer la colonne |

**Points sains à conserver** : `mail.py`/digest **jamais « envoyé » à tort** (l'exigence du mandat) ; `last_digest_at` n'avance que sur succès ; dédup robuste (clé+compte+fenêtre) ; cloche cloisonnée (marché partagé, `systeme`/NULL admin-only, zéro fuite inter-clients) ; ciblage compte des notifs correct ; alertes de secteur réellement évaluées et géométriques ; Courrier→admin fiable (cloche + demande persistée). 

**Conclusion** : la chaîne d'envoi et la comptabilité des statuts sont **rigoureusement honnêtes** ; le vrai défaut est en amont, au **déclencheur** — trois types de veille promis mais vides (**V1, haute**). Fermer V1 (honnêteté ou implémentation) et adoucir V2 (débordement silencieux) suffit à aligner ce que la veille promet sur ce qu'elle fait.
