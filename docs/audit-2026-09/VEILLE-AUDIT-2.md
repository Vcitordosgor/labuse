# VEILLE-AUDIT-2 — La chaîne complète : événement → cloche → page Veille → mail

**Branche** `audit/veille-audit-2` · **base main** `d6f17fb9` (arbre propre, branche neuve, 0 diff) ·
**worktree** `~/Desktop/labuse-veille` · **ports** 8545/5745 · **date** 27/09/2026 · **modèle** Opus ·
**lecture seule** — objets `[VEILLE-AUDIT-2]` créés puis **purgés** (vérifié 0), transport neutralisé
(`dry_run`), **aucun mail réel**, jamais un client (compte de test dédié, adresse de Vic).

> **La photo en une ligne.** Depuis que **VEILLE-FIX-1** et **VEILLE-2** ont été **mergés dans main**, la
> chaîne est **entièrement câblée dans le code** : les jobs `evaluer-suivis`, `detect-events`,
> `radar-cloche` et `digest` sont **au registre** (`jobs.py`). Le circuit tourne de bout en bout — je l'ai
> joué en réel (dry-run) sur les 4 témoins. **Deux fils restent cassés** : (1) le digest du matin (07:15)
> **rate le dépôt Radar de la veille au soir** — sa fenêtre « annonces du jour » = *aujourd'hui*, or la
> capture se fait le soir → au matin les annonces sont datées d'hier et sortent de la fenêtre ; (2) le
> **réglage de fréquence** (`digest_freq`) est **stocké mais jamais lu**. Et une nuance de prod : le
> **registre n'était toujours pas posé au VPS** au dernier relevé connu (VEILLE-AUDIT-1, 18/09) — non
> ré-observable ici (pas d'accès SSH).

> **Méthode & limites.** Inventaire par lecture du code (file:line). Circuit **joué en local sur la base
> réelle `labuse`** (comptes/veilles/biens réels), transport neutralisé, via appels directs aux fonctions
> de service (mêmes fonctions que les jobs du crontab). Harness + preuves :
> `docs/audit-2026-09/captures/veille-audit2/` (`harness.py`, `temoins.json`, `digest-compte-test.html/.txt`).
> **L'état prod du VPS n'a pas été observé** (hors périmètre) : le §2 « posé/a tourné » s'appuie sur
> `CRON-1-LOT0`/VEILLE-AUDIT-1 (18/09). App web non démarrée (base partagée, famine de verrou connue) —
> les preuves sont des payloads/HTML rendus, pas des captures d'écran.

---

## 1 · La carte de la chaîne

Légende du statut de chaque flèche : **✓ existe & câblée au registre** · **⚠ existe mais cassée/incomplète**
· **✗ n'existe pas / n'atteint pas le client** · **(prod?)** posée au VPS non ré-observée ici.

```
ÉVÉNEMENT (déclencheur)                     MOTEUR (job registre)              TABLE ÉCRITE          CE QUE LE CLIENT VOIT
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
① Vente DVF / permis / BODACC / chgmt PM   evaluer-suivis  07:02              event_log             cloche : « Vente : votre
   SUR une parcelle suivie                  (events.py:39 evaluer_suivis) ✓   kind=parcelle_suivie  parcelle CY0018… » → fiche
                                                                                                     ✓ (T1 prouvé)
② Bascule de classement du run             detect-events   07:04              event_log             cloche : « ▲ … Neutre→À suivre »
   (diff run servi ↔ précédent)             (events.detect_events) ✓          kind=bascule (NULL)   broadcast marché → fiche ✓
                                                                                                     (mais SORT du mail, §4)
   └ recherches sauvegardées / secteurs     — ARCHIVÉS (VEILLE-2 Lot 4)        —                     ✗ plus de veille secteur
③ Nouvelle annonce Radar (dépôt HTML)      radar-cloche    07:05              event_log             cloche : « Nouvelle annonce
   qui matche les critères d'une veille     (digests.evaluer_radar_cloche)    kind=radar (compte)   pour votre veille — Maison à
                                            ⚠ fenêtre « du jour » = today                            Saint-Pierre » → l'annonce
                                                                                                     ✓ matching, ✗ dépôt de la veille
④ Retrait / baisse de prix (RADAR-AUTO-1)  radar-cycle 04:00 / -dvf 04:30 /   pige_biens.statut     ✗ AUCUN événement client :
                                            -mensuel (jobs au registre) ✓     pige.baisse_prix      pige.* = journal interne
                                            MAIS n'émet aucun event client    (compte_id NULL)      (compte NULL), invisible (T3)
⑤ Nouvelle source amont injectée           sonde-sources 07:00               event_log             ✗ client NON prévenu :
                                            (sentinelle.passer) ✓             kind=systeme (NULL)   cloche PILOTE seulement (T4)
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
event_log ──► CLOCHE DE LA FICHE  +  CLOCHE EN HAUT À DROITE      list_events (events.py:701) — client-scopé
                                                                  + broadcast marché ; compte neuf à 0 (VEILLE-2/FIX-1) ✓
          ──► PAGE VEILLE : 2 chemins  PARCELLE (watched_parcels) · RADAR (veilles)     (secteurs/recherches retirés) ✓
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
DIGEST DU MATIN  07:15   digest → envoyer_digests(freq="quotidien")   UN mail/compte : suivis + Radar + nouveautés
   (events.py:1243) ✓    ⚠ ne lit PAS digest_freq (toujours quotidien)   dédup mail_queue par (compte, jour), jamais vide
          │
          ▼
mail_queue (raw, template_id NULL)   ──►  départ SYNCHRONE dans le job (prevu_at=NULL → _tenter_depart)
   (mailfile.py:206) ✓                     ⇒ PAS de worker séparé pour le digest.  SMTP send_email (mail.py) → mail reçu
          │                                ⚠ depart_des_programmes (worker des mails PROGRAMMÉS J+3/J+10) : AUCUN job/CLI ✗
          ▼
Brevo ?  Le digest = HTML BRUT en SMTP (pas un template Brevo).   radar_alerte = template Brevo n°13 mais CLI-seulement.
          ▼
Lien désinscription / réglages : /events/desabonner + /events/preferences (token) → routes réelles ✓  (fréquence non réglable ✗)
```

---

## 2 · Le registre CRON

Le crontab est **dérivé du registre `labuse.jobs.JOBS`** (`cli.py:_crontab_du_registre` → `/etc/cron.d/labuse`
via `deploy.sh`, wrapper `scripts/jobs/run-job.sh` + flock). **Le passage d'un job n'est persisté en base que
pour les jobs « eau »** (`circuit_journal`, `jobs.py:175`) ; les jobs « exploitation » (digest, evaluer-suivis,
radar-cloche…) n'écrivent qu'un **fichier d'état JSON** (`LABUSE_JOBS_STATE_DIR/<nom>.json`, absent de ce
worktree). **Conséquence : « dernier passage réel » des jobs de veille est inobservable depuis ici.** Le seul
témoin en base (shared) :

```
circuit_journal — job passages réels : coherence-robinets (cron, ok, 2026-09-22 21:25) · sonde-sources (cron, ok, 2026-09-22 20:55)
```

### 2.1 — Les jobs que la chaîne de veille suppose · présents / planifiés (registre) / a tourné

| Job supposé | Au registre ? | cron | Impl appelée | Envoie mail | A tourné (observable ici) |
|---|---|---|---|---|---|
| `evaluer-suivis` (parcelles suivies) | ✅ `jobs.py:413` | `2 3 * * *` (07:02) | `evaluer_suivis` | non | inobservable (JSON state) |
| `detect-events` (bascules marché) | ✅ `jobs.py:422` | `4 3 * * *` (07:04) | `detect_events` | non | inobservable |
| `radar-cloche` (Radar → cloche) | ✅ `jobs.py:379` | `5 3 * * *` (07:05) | `evaluer_radar_cloche` | non | inobservable |
| `digest` (UN mail/compte) | ✅ `jobs.py:428` | `15 3 * * *` (07:15) | `envoyer_digests` | **oui** | inobservable |
| `radar-cycle` (expirées/longue) | ✅ `jobs.py:389` | `0 0 * * *` (04:00) | `radar_cycle` | non | inobservable |
| `radar-cycle-dvf` (vendue) | ✅ `jobs.py:396` | `30 0 * * *` (04:30) | `radar_cycle_dvf` | non | inobservable |
| `radar-cycle-mensuel` (Courrier) | ✅ `jobs.py:402` | `30 1 1 * *` | `radar_cycle_mensuel` | non | inobservable |
| `sonde-sources` (sentinelle amont) | ✅ `jobs.py:295` | `0 3 * * *` (07:00) | `sonde_sources` | non | **oui — 2026-09-22 (circuit_journal)** |
| **consommateur `mail_queue`** (programmés) | ❌ **absent** | — | `depart_des_programmes` jamais appelé | — | — |
| `evaluer-secteurs` | ❌ **retiré** (VEILLE-2 Lot 4) | — | — | — | secteurs archivés |

**Tout ce que la chaîne suppose est au registre**, sauf un consommateur de la file pour les mails
**programmés** (voir ci-dessous). Le radar-cycle (RADAR-AUTO-1) est bien planifié — contredisant l'ancien
commentaire « radar-cycle : retirés » resté juste au-dessus (`jobs.py:452`, mort, à nettoyer).

### 2.2 — Le consommateur de `mail_queue`

- **Le digest ne dépend d'aucun worker.** `envoyer_mail(prevu_at=None)` déclenche le départ **synchrone**
  dans le job lui-même (`mailfile.py:223` → `_tenter_depart`). En dry-run, la ligne est écrite `en_attente`
  **sans `prevu_at`** et **rien ne part** (prouvé T1/T2 : `mail_queue` #15, `en_attente`).
- **Les mails PROGRAMMÉS (onboarding J+3, relance J+10)** attendent le worker `depart_des_programmes`
  (`mailfile.py:262`, ne prend que `prevu_at IS NOT NULL`). **Ce worker n'est branché à AUCUN job du registre
  ni à AUCUNE commande CLI** (grep vide). → **les mails programmés ne partent jamais tout seuls.** Hors
  chaîne de veille stricte, mais c'est le seul vrai « consommateur de file » et il est mort.
- **En local** : SMTP non configuré (`mail_configured()=False`) ⇒ **dry-run automatique** pour tout job
  `envoie_mail=True` (`jobs.py:134`). **En prod** : si `LABUSE_SMTP_HOST` est posé, le digest part en direct.
- **Si Brevo/SMTP refuse** : `_tenter_depart` incrémente `tentatives`, garde `en_attente` jusqu'à
  `TENTATIVES_MAX=3` (`mailfile.py:35`), puis passe **`echec`** — **rejeu MANUEL seulement** (`rejouer`,
  `mailfile.py:229`). **Aucun job de re-tentative automatique.** Un échec Brevo n'est donc jamais repris
  sans geste humain (mais il est bruyant : `erreur` colonne + `echec`, jamais silencieux).

---

## 3 · Quatre témoins suivis de bout en bout

Compte de test **actif** `[VEILLE-AUDIT-2]` (id 78, titulaire `kampusreunion+va2@gmail.com`, `digest_freq=hebdo`),
purgé en fin. Preuves : `captures/veille-audit2/temoins.json`.

### T1 — Parcelle suivie ✅ jusqu'au mail (dry-run)
Suivi de **CY0018** (Saint-Paul) et **BZ1065** (mandat). `evaluer-suivis` → `{mutation:1}` :
- **event_log** `parcelle_suivie` « **Vente : votre parcelle CY0018 a changé de mains** — Mutation du
  2025-12-31 — 2 300 000 € (Vente terrain à bâtir) », lien `/socle/#parcelle=97415000CY0018`, `lu=false`.
- **cloche** (payload) : l'événement apparaît non-lu pour le compte 78.
- **digest dry-run** : sujet « **LABUSE — 2 changements sur vos suivis** », corps contenant la vente ;
  **ligne `mail_queue` #15** (`digest_quotidien`, `en_attente`, dédup `digest:78:2026-09-27`) — **rien envoyé**.
- **Où ça s'arrête** : nulle part pour CY0018. **BZ1065 reste MUETTE** — elle n'a **aucune mutation DVF** en
  base (`T1_BZ1065_a_un_evenement=false`) : la fiche peut la suivre (cloche allumée), mais tant qu'aucun
  fait ne tombe SUR elle, rien ne se produit — comportement correct, pas un bug.

### T2 — Radar par critères ⚠ s'arrête à la fenêtre « du jour »
Bien de test (Saint-Pierre, maison, 350 k€, 90 m² hab, particulier) **daté aujourd'hui** + veille qui
matche (`communes:[Saint-Pierre], type:maison, prix_max:400000`) + veille qui ne matche pas (`type:terrain`) :
- **matching** : `matche()` = **true** pour la veille maison, **false** pour terrain (`T2_matche_*`).
- `radar-cloche` → `{radar:1}` : **event_log** `radar` « **Nouvelle annonce pour votre veille — Maison à
  Saint-Pierre** · 350 000 € · … », lien = l'annonce ; le digest le reprend (2ᵉ événement du mail T1).
  **Une seule veille (la matchante) déclenche ; la non-matchante n'écrit rien.** ✅
- **🔴 Où ça s'arrête pour une VRAIE annonce d'hier soir** : `_biens_du_jour` filtre
  `date_premiere_saisie ≥ (now Réunion)::date` (`digests.py:82`). J'ai mesuré en direct : **biens « du jour »
  = 1** (mon bien de test daté aujourd'hui) **vs 98 annonces réelles du dépôt du 26/09** (
  `T2_biens_reels_hier_26=98`) **qui n'entrent PAS**. La capture se fait **le soir** (extension RADAR-AUTO-1,
  « plafond 40/soir ») ; le job tourne à **07:05 le lendemain** → au matin, les annonces sont **datées de la
  veille** et **sortent de la fenêtre**. **Le dépôt du soir n'atteint donc jamais ni la cloche ni le digest**
  (sauf si Vic dépose après minuit). C'est le fil cassé le plus lourd de la chaîne Radar.

### T3 — Retrait / baisse de prix ✗ n'atteint jamais la veille
Baisse insérée sur le bien de test :
- **Aucun événement client** : tous les `pige.*` (`pige.baisse_prix`, `pige.statut_change`, `pige.nouvelle`…)
  ont **`compte_id NULL`** — `T3_pige_baisse_events_compte_null = 0` événement avec un compte. Ce sont des
  traces du **journal interne Radar** (`tables.py::journaliser`, hors `creer_notification`/registre),
  **invisibles à tout client**.
- Une annonce **retirée** sort de `_biens_du_jour` (`statut IN active/en_vente_longue`, `digests.py:75`).
- **Où ça s'arrête** : à l'écriture. Les cycles `radar-cycle*` **mettent bien à jour le statut** (expirée /
  vendue / retiree_sans_vente) et alimentent l'écran d'instruction + le Courrier, mais **aucune baisse ni
  aucun retrait ne devient une notification de veille pour le client**. (La baisse s'affiche en revanche sur
  la *carte* d'un bien encore « du jour » dans le mail — jamais un événement dédié.)

### T4 — Événement de marché ✗ pour le client (par conception)
- **Bascule de scoring** : `event_log kind=bascule`, **`compte_id NULL`** (broadcast marché) — visible à la
  **cloche** de tous, mais **exclue du mail** (`envoyer_digests` : « le marché SORT du digest », events.py:1307).
- **Nouvelle source injectée** : `event_log kind=systeme`, **`compte_id NULL` ou admin (31)** — **cloche
  PILOTE seulement**, **jamais un client** (`T4_systeme_compte_id=[31, null]`). Aucun canal, aucun texte
  côté client.
- **Où ça s'arrête** : le client n'est **jamais** prévenu d'une bascule par mail, ni d'une nouvelle source
  par quelque canal que ce soit. C'est le modèle voulu (VEILLE-2 : la cloche du haut porte le marché en
  lecture, le mail non) — à confirmer que c'est bien l'intention de Vic pour « bascule de scoring ».

---

## 4 · Les mails

**Registre unique des templates Brevo** = `brevo.py` (`REGISTRE`, ids 4→19, source de vérité, verrou de
params `verifier_templates` + garde fail-closed `mailfile.py:172`). Templates de la veille :

| Template | Brevo id | Objet | Usage | Dans la chaîne servie ? |
|---|---|---|---|---|
| `radar_digest` | 12 | LABUSE-12-RADAR-DIGEST | ancien digest « à tous » | **RETIRÉ** (VEILLE-FIX-1 Lot 2) |
| `radar_alerte` | 13 | LABUSE-13-RADAR-ALERTE | alerte par veille matchée | **CLI seulement** (`radar-digests`) — hors chaîne servie |
| `digest_quotidien` | — (raw) | « LABUSE — N changements sur vos suivis » | **le mail servi** | **oui** — HTML **brut** en SMTP, pas un template Brevo |

- **Le digest du matin n'est PAS un template Brevo** : HTML construit côté code (`emails.py`), envoyé par
  **SMTP** via `mail_queue` (`template_id NULL`), avec en-têtes **RFC 8058 List-Unsubscribe** (1-clic).
  Sujet factuel dynamique (`emails.py:54`). Doctrine « jamais un digest Radar à tous » **appliquée et
  prouvée** (T2 : la veille non-matchante n'écrit rien ; global 1 mail au seul compte à événement, 8 ignorés).
- **base_url** = `https://app.labuse.immo` (prod) / `127.0.0.1:8000` (local), liens `/socle/#parcelle=` et
  `/socle/#m=radar` (`config.py:315`).
- **Désinscription / réglages** = liens **réels et token-gardés** dans chaque mail
  (`/events/desabonner?c=..&t=..` et `/events/preferences?c=..&t=..`, `events.py:1447/1512`) —
  **présents et fonctionnels** dans le HTML rendu (`digest-compte-test.html`). Le désabonnement coupe l'e-mail
  de tous les types désactivables ; la page préférences règle **cloche / e-mail / brief par type**.
- **Digest rendu en dry-run (T1 + T2)** joint : `captures/veille-audit2/digest-compte-test.html` et `.txt`
  (vente CY0018 + annonce Radar Saint-Pierre, liens de désinscription/réglages inclus).
- ⚠ **Copie à corriger** : le corps dit encore « vos parcelles suivies, **vos secteurs** et vos critères »
  alors que les secteurs sont archivés (VEILLE-2) — reliquat de texte.

---

## 5 · Ce que le client règle

| Réglage | Stocké (table.colonne) | Écrit par | Lu / appliqué ? | Contrôle UI |
|---|---|---|---|---|
| Canaux **cloche / e-mail / brief** par type | `notif_canaux` | `set_pref` (events.py:337) ; PATCH `/events/prefs` ; POST `/events/preferences` | ✅ **oui** — cloche (`_cloche_filter`), e-mail (`envoyer_digests:1305`), brief (`brief_matin`) | page `/events/preferences` + panneau réglages |
| **Désinscription** e-mail (1-clic) | via `set_pref` (coupe e-mail) | `desabonner_email` (GET/POST `/events/desabonner`) | ✅ oui | lien de chaque mail (RFC 8058) |
| **Critères Radar** (communes, type, prix, surface, particulier) | `veilles.criteria` (jsonb) | POST `/radar/veille` (veille.creer) | ✅ **oui** — `veille.matche` lit chaque critère (prouvé T2) | `SurveillancePanel`/`VeilleExterne` |
| Parcelles suivies | `watched_parcels` | `watch_toggle` (cloche fiche / barre IDU) | ✅ oui | `WatchButton` + page Veille |
| **Fréquence** (immédiat / quotidien / hebdo) | `notif_prefs.digest_freq` (défaut `hebdo`) | **jamais écrit** | **❌ NON** — `envoyer_digests` reçoit `freq` en **paramètre** (le job passe toujours `"quotidien"`) et ne lit **jamais** la colonne ; le SELECT des destinataires (events.py:1263) ignore `digest_freq` | **❌ aucun contrôle UI** |

**Preuve empirique du trou fréquence** : mon compte de test avait `digest_freq='hebdo'` et a **quand même**
reçu le **digest quotidien** (T1/T2). Un client ne peut donc **ni choisir « immédiat », ni « hebdo »** : la
cadence est fixée par les jobs (07:15 quotidien), point. La `frequence` des veilles Radar
(`veilles.frequence`, défaut `ingestion`) est un autre champ, sans effet sur le rythme du mail.

---

## 6 · Verdict

**Ce qui marche** : la chaîne est **entièrement câblée dans le code de main** (VEILLE-FIX-1 + VEILLE-2
mergés). ① parcelle suivie → cloche → digest : **prouvé de bout en bout** (T1). ③ Radar → cloche → digest :
**prouvé** pour une annonce **du jour** matchante, avec ciblage strict par critères (T2). Cloche isolée par
compte, compte neuf à 0, digest un/jour/compte non vide, désinscription/réglages **réels et token-gardés**,
doctrine « jamais un digest Radar à tous » **appliquée**. Le digest part **synchrone** (pas besoin de worker).

**Flèches cassées / absentes, par gravité** :
1. **🔴 Radar rate le dépôt du soir** — `radar-cloche`/`digest` (07:05/07:15) ne voient que les biens
   `date_premiere_saisie ≥ aujourd'hui` ; la capture étant le **soir**, les annonces sont datées d'**hier**
   au matin → **jamais notifiées** (mesuré : 98 réelles d'hier exclues). *La veille Radar est de facto muette.*
2. **🟠 Fréquence non réglable** — `digest_freq` stocké, **jamais lu** ; aucun UI. Le client ne peut pas
   choisir immédiat/quotidien/hebdo (mesuré : `hebdo` → reçoit quand même le quotidien).
3. **🟠 Aucun consommateur des mails PROGRAMMÉS** — `depart_des_programmes` n'a **ni job ni CLI** → les mails
   J+3/J+10 ne partent jamais seuls ; et **aucun rejeu auto** d'un mail en `echec` (Brevo refuse → geste manuel).
4. **🟡 (prod)** — registre non ré-observé au VPS ; dernier relevé connu (18/09) = **non posé** ⇒ si rien n'a
   changé, digest/suivis/radar-cloche **n'ont jamais tourné en prod** malgré le code prêt.
5. **🟡 Reliquats** — corps du digest cite « secteurs » (archivés) ; commentaire `jobs.py:452` « radar-cycle
   retirés » faux (ils sont au registre).

**3 recommandations pour VEILLE-FIX-2** :
- **(A)** Élargir la fenêtre Radar de « du jour » à **« depuis le dernier passage »** (ou J-1) dans
  `_biens_du_jour`, pour que le dépôt du soir soit notifié le lendemain matin. *(ferme le 🔴.)*
- **(B)** **Brancher `digest_freq`** : le SELECT des destinataires lit la colonne, un job `digest-hebdo`
  (ou un filtre de cadence) l'honore, et exposer le réglage sur la page préférences. *(ferme le 🟠 fréquence.)*
- **(C)** **Poser le registre au VPS** et **planifier/relancer un consommateur de `mail_queue`** (worker des
  programmés + rejeu des `echec`), avec un verrou de vérification. *(ferme prod + file.)*

---

## 7 · Hors mandat (non fait)

Corrigé : rien. Planifié : rien. Aucun mail réel. Pas de merge. La capture Radar elle-même (RADAR-AUTO-1
mergé) et l'état prod du VPS ne sont pas traités. Objets `[VEILLE-AUDIT-2]` **purgés** (vérifié : comptes 0,
events 0, mail_queue 0, pige_biens 0). Base rendue à l'identique.

---

### Annexe — Preuves (`captures/veille-audit2/`)
`harness.py` (rejouable, self-purge) · `temoins.json` (résultats bruts des 4 témoins) ·
`digest-compte-test.html` + `.txt` (digest T1+T2 rendu en dry-run, liens désinscription/réglages).
