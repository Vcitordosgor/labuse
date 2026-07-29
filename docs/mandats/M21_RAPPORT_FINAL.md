# M21 — RAPPORT DE VAGUE : branchement du service e-mail

Autonome, filet `avant-m21` (main `a677ef0`). **CC ne merge pas** — 3 branches poussées, non mergées.
Golden 116/116 par lot (`LABUSE_DEV_MODE=1`). Modèle P gelé. **Aucun secret dans le code, les logs ou un
commit** (`.env` gitignored vérifié ; le mot de passe d'application reste chez Vic).

## Note sur la preuve d'envoi réel
Le mot de passe d'application Gmail vit dans le `.env` que **Vic** remplit — il n'est pas sur la machine de dev.
CC ne peut donc pas joindre Gmail. Chaque mécanique est prouvée par un **envoi SMTP réel vers un serveur de
capture local** (`qa/m21/smtp_catcher.py`) : transaction SMTP complète (MAIL FROM / RCPT / DATA), message reçu et
lu — un envoi réel, pas un mock. Le test **inbox-vs-spam via Gmail** est le seul geste qui exige le secret : il
revient à Vic (`labuse mail-test`), cf. LOT C.

## 1. Preuves d'envoi réel (par mécanique)

| Mécanique | Preuve (envoi réel capturé) | From |
|---|---|---|
| **Transport / mail-test** (A) | `qa/m21/a/mail_test_capture.txt` — `labuse mail-test` → message reçu | `contact@labuse.immo` |
| **Reset mot de passe** (B1) | `qa/m21/b/B1_reset_B2_avis_capture.txt` — lien token + validité 1 h | `contact@labuse.immo` |
| **Avis Chatel** (B2) | `qa/m21/b/B1…` + `B2_avis_cli_capture.txt` — CLI `labuse avis-echeance` bout-en-bout, **dédup 1→0** | `contact@labuse.immo` |
| **Digest notifications** (B3) | `qa/m21/b/B3_digest_capture.txt` — 2 événements + liens parcelle + **List-Unsubscribe** ; désinscription → 2ᵉ passage = 0 | `contact@labuse.immo` |
| **Refus quota** (C2) | `qa/m21/c/C2_quota_refus.txt` — refus loggé explicite, non silencieux | — |

Comportement **A2** vérifié : sans `LABUSE_SMTP_HOST`, le mail est **journalisé et non envoyé** (jamais « envoyé »
à tort). UI reset **honnête** selon l'état réel du transport.

## 2. Textes des e-mails (la voix de LABUSE — Vic peut tout réécrire dans `src/labuse/emails.py`)

### Reset mot de passe
> **Objet** : LABUSE — réinitialisation de votre mot de passe
>
> Bonjour,
>
> Une réinitialisation du mot de passe de votre compte LABUSE a été demandée. Pour choisir un nouveau mot de
> passe, ouvrez le lien ci-dessous :
>
> {lien}
>
> Ce lien est valable 1 heure. Passé ce délai, il faudra en redemander un.
>
> Si vous n'êtes pas à l'origine de cette demande, ignorez simplement cet e-mail : votre mot de passe reste
> inchangé et votre compte n'est pas modifié.
>
> — LABUSE / contact@labuse.immo

### Avis d'échéance — loi Chatel (VALEUR LÉGALE — à relire avec attention)
> **Objet** : LABUSE — votre abonnement se reconduit le {date d'échéance}
>
> Bonjour,
>
> Conformément à l'article L. 215-1 du code de la consommation (loi Chatel), nous vous informons que votre
> abonnement LABUSE arrive à échéance le {date d'échéance}.
>
> Sauf dénonciation de votre part, il sera reconduit tacitement pour une nouvelle période de douze (12) mois, aux
> conditions en vigueur.
>
> Vous pouvez choisir de NE PAS reconduire cet abonnement. Pour cela, informez-nous de votre décision au plus tard
> UN (1) MOIS avant l'échéance, soit avant le {échéance − 1 mois}, par e-mail à contact@labuse.immo ou depuis votre
> espace :
>
> {lien espace}
>
> Si vous ne nous avez pas informés de votre faculté de non-reconduction dans ce délai, vous pourrez mettre
> gratuitement un terme à la reconduction et, le cas échéant, être remboursé des sommes versées d'avance après la
> date de reconduction (art. L. 215-1, al. 3).
>
> — LABUSE / contact@labuse.immo

### Digest de notifications
> **Objet** : LABUSE — {N} nouveauté(s) sur vos parcelles ({cette semaine / aujourd'hui})
>
> Bonjour,
>
> Voici le point sur vos parcelles suivies et vos veilles pour {période} ({N} événement(s)) :
>
> • {titre de l'événement}
>   {détail}
>   {lien vers la parcelle}
>   …
>
> — — —
> Vous recevez cet e-mail parce que vous suivez des parcelles ou avez enregistré des veilles sur LABUSE. Pour ne
> plus recevoir ce résumé : {lien de désinscription}
>
> — LABUSE / contact@labuse.immo

## 3. Variables d'environnement + report VPS
```
LABUSE_SMTP_HOST=smtp.gmail.com
LABUSE_SMTP_PORT=587
LABUSE_SMTP_USER=contactlabuse@gmail.com
LABUSE_SMTP_PASSWORD=<mot de passe d'application, 16 c. — Vic le colle dans le .env>
LABUSE_SMTP_STARTTLS=1
LABUSE_MAIL_FROM=LABUSE <contact@labuse.immo>
```
Documentées dans `.env.example` (sans valeur) et le README. **À reporter au déploiement VPS** :
1. Remplir ces variables dans le `.env` du VPS (le mot de passe = secret Vic).
2. `labuse mail-test vic@…` pour valider (inbox-vs-spam).
3. **Cron QUOTIDIEN** `labuse avis-echeance` (obligation Chatel — chaque jour, la fenêtre 3→1 mois est balayée ;
   dédup par terme garantit un seul envoi).
4. **Cron** `labuse digest` — **hebdomadaire** conseillé (défaut), ou quotidien si Vic préfère.

## 4. Délivrabilité (LOT C1)
From = `contact@labuse.immo` prouvé partout ; SPF déjà posé par Vic (`include:_spf.google.com`). Le test
**inbox vs spam** exige le `.env` rempli → **geste de Vic** (`labuse mail-test`). Checklist SPF/DKIM/DMARC/contenu
dans `docs/mandats/M21_C_FINITIONS.md`. Quota Gmail ~500/j documenté + refus explicite loggé (C2).

## 5. Non fait / bloqué
- **Test inbox-vs-spam réel** : impossible sans le secret Gmail → à faire par Vic (checklist fournie).
- **Suggestions par e-mail (C3)** : NON codé (décision Vic) ; branchement trivial documenté.
- Rien d'autre bloqué.

## 6. Branches & ordre de merge (Vic, `--no-ff`)
```
feat/m21-a-smtp        (transport unique + mail-test)           ← base
feat/m21-b-mecaniques  (reset, avis Chatel, digest+unsub)       ← basée sur A
fix/m21-c-finitions    (refus quota + délivrabilité + rapport)  ← basée sur A
```
Ordre : **A → B → C**. B et C sont basées sur A (dépendance transport) → merges propres. Puis **LOT D**
(vérification sur main mergée) après le merge.
