# Radar & Veille — ce qui se passe vraiment (28 octobre 2026)

**Audit lecture seule.** Base de prod lue en direct (`ssh labuse-vps`), base locale du Mac
(`postgresql:///labuse`), code de la branche `audit/radar-etat-1`. Rien n'a été modifié, rien déployé,
aucun mail envoyé.

## La photo en une phrase

Le Radar **collecte** encore des annonces quand on le lance à la main, mais il **ne prévient plus
personne** : la dernière capture arrivée en prod date du **6 octobre**, les cinq tâches de nuit qui
transforment une annonce en alerte sont **gelées** depuis « Phase 8 Stéphanie », et **aucun client n'a
de veille Radar**. La chaîne est débranchée à trois endroits en même temps.

---

## 1. La capture (l'extension Chrome)

- **L'extension ne tourne pas toute seule le soir.** Elle sait le faire (une alarme à 21 h + un délai
  au hasard de 0 à 3 h est codée), mais aucune des captures réelles ne porte cette signature : **toutes**
  les captures depuis le 26/09 sont tombées **après minuit** (entre 00 h 12 et 02 h 40), par petits
  paquets, sur quelques jours isolés. C'est la trace d'un lancement **à la main** (bouton « Capturer
  maintenant » ou rejeu du fichier Saint-Denis de recette), pas d'une capture automatique du soir.
- **Sur quelle API elle pointe.** Par défaut, l'extension envoie tout sur **`http://localhost:8205`**
  (le LABUSE du Mac, pas la prod), et elle n'a le droit de parler qu'à Leboncoin et à `localhost`
  (son `manifest.json`). Pour qu'elle nourrisse la prod, il faut **changer l'URL** dans ses options
  **et** élargir ses permissions. Tel qu'il est réglé, l'outil remplit la base **du Mac**, pas la prod.
- **Dernière capture réelle.**
  - **Prod : 6 octobre 2026, 01 h 34** (puis plus rien — 22 jours de silence).
  - **Mac (local) : 27 octobre 2026, 00 h 34.** Le Mac a continué à capturer les 10, 23 et 27 octobre,
    mais **rien de tout cela n'est arrivé en prod** : les deux bases divergent après le 6 octobre.
- **Jeton.** Le jeton de prod (`LABUSE_RADAR_TOKEN`) **est bien posé** côté serveur. Côté extension, le
  jeton vit dans le stockage du navigateur (illisible d'ici) ; comme les captures partent vers
  `localhost`, l'extension du Mac est configurée pour le **dev**, pas pour la prod.
- **Manuel vs automatique depuis le 26/09.** **Zéro dépôt « à la main » façon Cmd+S** (le dernier
  remonte au 29-30 août). Depuis le 26/09, **100 % des dépôts** passent par le tuyau « automatique » de
  l'extension — mais, comme dit plus haut, **déclenchés à la main**, pas par l'horloge du soir.
- **« Pause », c'est quoi.** Il n'existe **aucun interrupteur global** « Radar en pause ». Le seul
  « pause » du code est **par alerte** : chaque veille a une case `en_pause` (colonne `veilles.en_pause`,
  bouton `POST /radar/veille/{id}/pause`), posée par **RADAR-2 Lot 4 le 27 septembre 2026**. Une veille
  en pause reste affichée (« En pause ») mais ne notifie plus et ne compte plus de nouveautés. En prod,
  **aucune veille n'est en pause** (et de toute façon aucune veille Radar n'existe, cf. §3).

## 2. Les tâches de nuit (crons du VPS)

Le vrai crontab du serveur (`/etc/cron.d/labuse`) dit ceci :

| Tâche | État réel | Cadence | Dernier passage | Ce qu'elle a produit |
|---|---|---|---|---|
| **radar-cloche** | **GELÉE** (commentée « Phase 8 Stéphanie ») | — | **jamais** | rien |
| **radar-cycle** | **GELÉE** | — | **jamais** | rien |
| **radar-dvf** (radar-cycle-dvf) | **GELÉE** | — | **jamais** | rien |
| **radar-mensuel** (radar-cycle-mensuel) | **GELÉE** | — | **jamais** | rien |
| **digest** (le mail du matin) | **GELÉE** | — | **jamais** | rien |
| evaluer-suivis | **active** | 07 h 02 | 28/10 07 h 02, OK | 0 événement (aucun fait sur une parcelle suivie) |
| detect-events | **active** | 07 h 04 | 28/10 07 h 04, OK | 8 bascules de marché le 28/10 (cloche collective, pas un mail) |
| mail-queue (mail-queue-consommer) | **active** | toutes les 5 min | 28/10 17 h 00, OK | **0 mail parti** (la file est toujours vide) |

Le journal `job_runs` ne remonte qu'au **13 octobre** (la table est récente). Sur toute cette fenêtre :
les trois tâches actives tournent proprement tous les jours, mais **les cinq tâches Radar/digest n'ont
jamais tourné** parce qu'elles sont commentées dans le crontab. Le gel est **volontaire** (motif
« Phase 8 Stéphanie » inscrit dans le code lui-même, `jobs.py`), pas une panne.

Bonne nouvelle au passage : le **consommateur de la file mail** (absent en septembre) **existe
maintenant** et tourne toutes les 5 minutes — mais il n'a jamais rien à envoyer côté Radar.

## 3. Les données

**En prod :** 271 biens — **168 en vente** (`active`), **103 retirés**. Dernière annonce : **5 octobre**
(rien de plus récent). Répartition des biens en vente :

- Par commune : Saint-Denis 34, Saint-Pierre 25, Saint-Paul 22, Le Tampon 17, Saint-Louis 8,
  La Possession 7, Saint-Joseph 7, Saint-André 6, La Plaine-des-Palmistes 6, Sainte-Marie 5…
- Par type : **maison 98, appartement 43, terrain 23** (4 sans type).

**En local (Mac) :** 416 biens (117 en vente, 299 retirés), dernière annonce du **26 octobre** — le Mac
est plus à jour que la prod, preuve que les captures récentes sont restées sur le Mac.

**Prix demandés vs DVF : oui, c'est calculé et affiché.** Le code sert, par commune, la **médiane du prix
demandé (Radar)** à côté de la **médiane du prix acté (DVF)**, avec un « écart demandé/acté », sur la
fiche (§Marché) et dans l'outil Communes. La fiabilité est graduée selon le nombre d'annonces
(« normal » ≥ 30, « indicatif » 5-29, « insuffisant » < 5).

**Qui a une veille, qui a reçu quelque chose :**
- **Veilles Radar de clients : 0.** Il y a 8 veilles en base, mais toutes de type foncier
  (`permis`/`bodacc`), **sans compte** — ce sont des veilles système, pas des alertes d'annonce de
  client. **Aucun des 27 comptes n'a de veille Radar.**
- Parcelles suivies : un seul vrai client (compte 18) suit **1 parcelle** ; l'admin en suit 4.
- **Reçu depuis le 1er octobre :** **cloche Radar = 0, digest = 0, mail Radar = 0.** Les seuls mails
  partis (11 en tout, tous « reçus ») sont des mails de cycle de vie (essai, souscription, mot de passe)
  à **4 comptes**. Les seuls événements posés depuis le 1er octobre sont 62 « bascules » de marché et
  123 « système » — **tous collectifs, aucun adressé à un client**.

## 4. Une annonce réelle, suivie bout en bout

La dernière annonce entrée en prod : **bien 284 — un terrain à La Plaine-des-Palmistes, 88 000 €,
420 m², annonce Leboncoin `3230785453`**, saisi le **6 octobre à 01 h 34**.

1. **Capture** — arrivée par le tuyau automatique (dépôt « nouvelles · page … »), lors de la session du
   6 octobre après minuit. ✅ *C'est la dernière chose qui a marché.*
2. **Parseur** — prix, surface, type, commune, identifiant extraits correctement. ✅
3. **Dédup** — rangé sous son identifiant d'annonce `3230785453`, pas de doublon. ✅
4. **Cycle de vie** — toujours marqué **« active »** 22 jours plus tard, jamais revérifié (`last_seen`
   figé au 6/10). Il devrait être passé « en vente longue », mais **radar-cycle est gelé** → le statut
   ne bouge plus. ⛔
5. **Critères de veille** — comparé à… **rien** : aucun client n'a de veille Radar. ⛔
6. **Cloche** — **radar-cloche est gelé** et il n'y a aucune veille → **aucun événement**. En prod,
   aucun événement Radar n'a **jamais** été créé. ⛔
7. **Digest** — **gelé** → aucun mail du matin. ⛔
8. **Mail** — rien ne part (la file reste vide). ⛔

**Où ça s'arrête :** l'annonce **entre** dans la base et serait **visible** dans l'écran Radar et sur la
carte, mais **elle ne déclenche plus aucune alerte** — ni cloche, ni mail. Et comme la prod n'a plus reçu
de capture depuis le 6 octobre, même cette collecte s'est arrêtée.

---

## Une soirée type (aujourd'hui)

Le soir, **il ne se passe rien tout seul.** L'extension est réglée pour le Mac en dev et n'est pas
lancée par son horloge ; aucune capture ne part vers la prod. Pour qu'une annonce entre, il faut que
quelqu'un ouvre Chrome et clique « Capturer maintenant » (ce qui remplit la base du Mac, pas la prod).

## Une semaine type (aujourd'hui)

Chaque matin en prod, trois tâches tournent proprement : `evaluer-suivis` (07 h 02), `detect-events`
(07 h 04) et le consommateur de mail (toutes les 5 min). Elles produisent quelques « bascules » de
marché dans la cloche collective, et c'est tout. **Aucun mail du matin ne part, aucune alerte Radar
n'arrive à un client**, parce que les cinq tâches qui font ce travail sont gelées et qu'aucun client
n'a de veille Radar. La prod n'a reçu **aucune nouvelle annonce de toute la semaine** (dernière : 6/10).
