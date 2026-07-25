# M21 — LOT C : finitions (délivrabilité · quota · suggestions)

**Branche** `fix/m21-c-finitions` (basée sur A — transport). Non poussée pour merge.

## C1 — Délivrabilité

**Ce que CC peut prouver ici** (sans le mot de passe Gmail, que seul Vic détient) :
- **Expéditeur affiché = `contact@labuse.immo`** dans TOUS les envois (reset, avis Chatel, digest, mail-test)
  — vérifié sur chaque capture SMTP (`qa/m21/a/`, `qa/m21/b/`), jamais l'adresse Gmail brute.
- Le **SPF** est déjà posé par Vic sur `labuse.immo` :
  `v=spf1 include:_spf.mx.cloudflare.net include:_spf.google.com ~all` — l'envoi via Gmail est donc autorisé
  côté DNS.

**Ce qui reste à faire par Vic** (nécessite le `.env` rempli — un secret que CC ne détient pas) :
1. `labuse mail-test votre-adresse@gmail.com` **et** `…@outlook.com` → vérifier l'arrivée **en boîte de
   réception, pas en spam**.
2. Si arrivée en indésirable, diagnostiquer dans cet ordre (ne PAS bricoler d'en-têtes au hasard) :
   - **SPF** : `dig TXT labuse.immo` doit renvoyer l'enregistrement ci-dessus (propagé).
   - **DKIM** : Gmail signe automatiquement pour l'alias vérifié `contact@labuse.immo` — vérifier la présence de
     `DKIM-Signature` dans l'en-tête reçu (Gmail : « Afficher l'original »).
   - **DMARC** : un enregistrement `_dmarc.labuse.immo` (`v=DMARC1; p=none; rua=…`) améliore la réputation.
   - **Contenu** : les mails sont en **texte brut**, sobres, sans image ni lien raccourci — profil peu spammy.
     L'`Message-ID` est en `@labuse.immo` (cohérent avec le From).

**Verdict C1** : le From est bon et le SPF est posé ; le test « inbox vs spam » est **le geste de Vic** après
avoir rempli le `.env` (il est impossible sans le secret). Checklist ci-dessus fournie.

## C2 — Limite de volume (Gmail gratuit ≈ 500 envois/jour)

- **Documenté** dans le README (section « E-mail (SMTP) »).
- **Refus EXPLICITE, jamais silencieux** : quand le serveur répond une erreur de plafond
  (`550 5.4.5 Daily user sending limit exceeded`, `rate limit`, `too many`…), `mail.send_email` **logue**
  `MAIL REFUSÉ — plafond d'envoi atteint (Gmail gratuit ≈ 500/jour) : passer à un relais SMTP transactionnel`
  et retourne `SendResult(sent=False, 'error: quota')`. **Prouvé** (serveur SMTP rejetant) :
  `qa/m21/c/C2_quota_refus.txt`. Aucun mot de passe dans le log.
- **À quel volume ça devient contraignant** : le digest est le poste dominant. À `N` abonnés en digest
  **quotidien**, on émet ~`N` mails/jour (reset/avis sont marginaux). La limite de 500/jour est atteinte vers
  **~500 abonnés** en digest quotidien (ou bien plus en digest **hebdomadaire**, le défaut : ~500×7). Au-delà :
  relais SMTP transactionnel (Brevo/Postmark/SES) — même module, on change les variables `LABUSE_SMTP_*`.

## C3 — Suggestions par e-mail — NON CODÉ (décision Vic)

Conformément à la décision de Vic, l'envoi des suggestions clients (M16-C2, stockées en base, lues via
`labuse suggestions`) **n'est PAS branché** dans ce mandat.

**Pour information** : le branchement serait trivial une fois le LOT A en place — une commande qui lit les
suggestions non traitées et appelle `mail.send_email(get_settings().admin_email, sujet, corps)` (quelques
lignes, même transport). À activer si Vic change d'avis.

## Non-régression
`golden 116/116` (`LABUSE_DEV_MODE=1`) · import-smoke `labuse.mail` OK · modèle P gelé · aucun secret.
