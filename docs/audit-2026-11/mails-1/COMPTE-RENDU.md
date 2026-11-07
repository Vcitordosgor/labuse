# MAILS-1 — un seul gabarit, 21 mails justes

- **Date** : 07/11/2026 · **Branche / worktree** : `feat/mails-1` · `~/Desktop/labuse-mails2`
- **Modèle** : Opus · **Ports** : 9800 / 7000 (non requis — travail hors-ligne + envoi Brevo)
- **Prod** : jamais touchée · **Merge** : non · **Envois de test** : uniquement `victorlaganepro+mails@gmail.com`
- **Maquette suivie** : `~/Downloads/Maquette — gabarit des mails LABUSE.html` (validée Vic)

## Ce qui a été fait

Un **gabarit unique**, rendu par l'app, décline les mails du catalogue NU5-C. **Brevo
n'est plus qu'un transport** : le HTML (e-mail compatible Gmail / Apple Mail / Outlook — tableaux,
styles en ligne, 600 px, lisible sur téléphone) + la version texte **partent du code**, plus aucun
`templateId`. Les modèles Brevo ne sont plus utilisés.

> **V3 (corrections Vic du 07/11)** : signature « gestionnaire relation entreprise » (sans « je lis
> chaque réponse »), numéro conservé ; **bouton = jeton exact de la charte** (`#4ade80` / `#06301a`,
> AA) ; **majuscule en tête de chaque titre et de chaque phrase** (test dédié) ; **un seul mail de
> réinitialisation** → le doublon `smtp_reset_password` (ancien #17) supprimé, **20 mails distincts** ;
> mail 04 : deux-points après chaque intitulé d'étape + « qui ont le plus de chances de se vendre » ;
> mail 14 : validité réelle du lien (`flash_token_days` = « 30 jours ») ; mail 16 : première personne
> (« Vous m'aviez signalé… », « Voici ma réponse ») ; mail 19 (annonce) : bouton « Voir les communes
> concernées » ; mail 20 (maintenance) : **pas de bouton**, phrase « Si l'app ne répond pas pendant ce
> créneau, réessayez après 23h00 » ; relecture ponctuation / espaces / accents sur majuscules.
>
> **V4 (corrections Vic)** : mail 10 — **gras sur le mot entier** avec pluriel juste (« 1 bien » /
> « 3 biens ») ; **`maj1` ne touche que le 1ᵉʳ caractère d'un titre/phrase**, jamais un texte inséré
> après « : » dans un objet → mail 19 objet « LABUSE — maintenance programmée : mise à jour serveur » ;
> les mails de **facturation / accès** (abonnement, paiement, suspension, rétablissement, fin
> d'abonnement, **rapport acheté**) deviennent **transactionnels** comme la sécurité : pas de
> List-Unsubscribe, pas de « Me désinscrire », pied « Ce message concerne votre abonnement ; il n'est
> pas désactivable. » ; mail 14 — **badge au vert de la charte**. Un test par point.

### 1. Le gabarit — `src/labuse/gabarit_mail.py`

Reproduit la maquette au pixel, mais en **HTML e-mail sûr** (tables + styles en ligne, pas de flex/grid) :

- **Bandeau sombre** `#0b0e0c` : logo `LA`**`BUSE`** (BUSE en `#7ee0a0`) + baseline
  « **Le trésor est sous vos pieds** » à droite.
- **Corps blanc**, 600 px, 15 px/1.6.
- **Bouton vert** = **le jeton de la charte de l'app** (`bg #4ade80` / texte `#06301a`, soit `bg-mint` /
  `mint-on`), contraste ≈ 8.9:1 (AA). Table + `bgcolor` → rendu fiable jusque dans Outlook ; jamais un lien brut.
- Blocs : paragraphe, note, **étapes numérotées** (pastilles rondes), **carte** (critères),
  **liste de biens** (Radar), **encadré** (maintenance), ligne de fait (digest), lien secondaire.
- **Deux registres** :
  - **personnel** — signature « **Victor Lagane**, gestionnaire relation entreprise ·
    **+262 693 51 71 53** » (avatar « VL ») ;
  - **automatique** — **étiquette de couleur selon la nature** (vert charte pour Radar / veille / vente /
    rapport, ambre maintenance, ardoise nouveauté), faits en clair, **pas de signature**.
- **Pied** (décision Vic) : `LABUSE · contact@labuse.immo` puis **Gérer mes notifications · Me désinscrire ·
  Confidentialité · Mentions légales**. **Pas d'adresse postale** (non fournie) → remplacée par le lien
  **Mentions légales** (`labuse.immo/mentions-legales/`, page existante) pour que l'éditeur reste
  identifiable. **Mails de sécurité** : même pied **sans** « Me désinscrire ».
- Version **texte** (repli multipart) pour chaque mail.

### 2. Le contenu des 21 mails — `src/labuse/mails_contenu.py`

Un seul endroit de texte, relu d'un coup. `rendre(key, params) -> (sujet, html, texte, headers)`.

**Corrections de fond (mandat), toutes appliquées :**

- **Plus de numéro factice** : le vrai numéro (`+262 693 51 71 53`) dans la signature ; le `06 92 00 00 00`
  de la maquette a disparu (vérifié par test).
- **Un seul mail de réinitialisation** : `mdp_oublie` est l'unique chemin ; le doublon
  `smtp_reset_password` (ancien #17) est **supprimé** (→ **20 mails distincts**, pas 21).
- **Prénom partout** où on le connaît (repli « Bonjour, » sinon).
- **Aucune promesse dépassée** : le Copilote est présenté comme une **page du menu de gauche** ; **aucune
  mention de « créole »** (vérifié par test).
- **Maintenance** : dit **quoi** (l'opération), **quand** (fenêtre de coupure, heure Réunion), **quoi faire**
  (rien, tout reprend seul).
- **Alerte Radar** : **liste chaque bien** — commune, surface, zone, prix, portail, date du relevé.
- **Une seule phrase d'appel à l'action** par mail (un bouton principal).
- **Zéro faute** (relecture).

Le **mail de fin d'essai proche** (`essai_fin_proche`) est **rendu par le code**, sans modèle Brevo.

### 3. Brevo = simple transport

- `brevo.envoyer_html(to, sujet, html, texte, headers)` — pousse `htmlContent` + `textContent` à
  `/v3/smtp/email`, expéditeur forcé sur `contact@labuse.immo`, suivi de clic désactivé. Mêmes gardes
  que l'existant (étanchéité dry-run `.eml` hors prod, clé absente = raison explicite).
- `mail.envoyer_template(to, key, params)` est **la façade** : si la clé est gérée par le gabarit
  (les 21), elle **rend le HTML et le pousse via `brevo.envoyer_html`** ; sinon (legacy) via le template.
  → La file `mail_queue` et sa machine à états sont **inchangées** (aucun risque de régression).
- `mail.send_email` : au repli Brevo (VPS sans SMTP), transporte désormais le **HTML** quand il est fourni
  (avant, le HTML était perdu).
- `emails.py` (reset, digest, annonce, maintenance, mise en vente) **délègue au gabarit** : les mails
  techniques passent par le même modèle, sans changer leurs appelants.
- `pige/digests.py` : l'alerte Radar passe les **biens structurés** (le gabarit les met en liste).
- Pied de page jetonisé (notifications / désinscription) complété depuis le compte si l'appelant ne l'a
  pas fourni (`mailfile._completer_liens`, best-effort, jamais bloquant).

### 4. Modèles Brevo désormais inutilisés (Vic peut les supprimer)

Tous les modèles du cycle de vie et Radar ne servent plus (contenu rendu par l'app) :

| id | nom Brevo | remplacé par (code) |
|---:|---|---|
| 4 | LABUSE-E-ESSAI-48H | `essai` |
| 5 | LABUSE-0-SOUSCRIPTION | `souscription` |
| 6 | LABUSE-1-BIENVENUE | `onboarding1` |
| 7 | LABUSE-2-METHODE | `onboarding2` |
| 8 | LABUSE-3-POINT-ETAPE | `onboarding3` |
| 9 | LABUSE-A-CARTE-REFUSEE | `relance_carte` |
| 10 | LABUSE-B-SUSPENSION | `suspension` |
| 11 | LABUSE-C-RETABLI | `retablissement` |
| 12 | LABUSE-12-RADAR-DIGEST | `radar_digest` (déjà retiré du flux) |
| 13 | LABUSE-13-RADAR-ALERTE | `radar_alerte` |
| 14 | LABUSE-D-MDP-OUBLIE | `mdp_oublie` |
| 15 | LABUSE-D-MDP-MODIFIE | `mdp_modifie` |
| 16 | LABUSE-F-RESILIATION | `resiliation` |
| 17 | LABUSE-G-FLASH-PRET | `flash_pret` |
| 18 | LABUSE-H-EMAIL-CHANGE | `email_change` |
| 19 | LABUSE-I-RETOUR-TRAITE | `retour_traite` |
| 20 | LABUSE-J-ESSAI-FIN-PROCHE | `essai_fin_proche` (jamais créé côté Brevo — plus besoin) |

> La **clé API Brevo** reste nécessaire (c'est le transport) ; seuls les **modèles** sont à supprimer.

## Recette

### Test automatique — `tests/test_mails_1_gabarit.py`

Sur **chaque** mail (20 + `essai_fin_proche`), vérifie : **bouton** = jeton charte cliquable (ou
**absence** de bouton pour la maintenance) · **signature** (personnel) / **étiquette** (auto) ·
**pied** (contact, Confidentialité, Mentions légales, et désinscription sauf sécurité) · **aucun lien
mort** ni variable `{{ … }}` · **majuscule en tête de chaque titre et paragraphe** · corrections de
fond. Plus : reset unique (un seul chemin), Radar liste chaque bien, maintenance quoi/quand/quoi-faire
+ phrase de reprise, annonce « Voir les communes concernées », flash « 30 jours », retour 1re personne.

→ **186 cas, tous verts** (dont : facturation/accès transactionnels, gras du mot entier + pluriel,
objets sans majuscule après « : », badge rapport vert).

### Suite unitaire (famille du hook)

`pytest -m "not db and not local and not reel and not network"` → **3174 passés, 0 échec**
(50 ignorés = environnement : base live / front non bâti). Tests de contenu mis à jour pour le nouveau
gabarit (annonce/maintenance/digest/mise-en-vente), tests de la file `mail_queue` mis à jour vers le
transport `brevo.envoyer_html` (machine à états inchangée).

**Front : non concerné** — **0 fichier `frontend/` modifié** (le changement est 100 % back-end + mails).
Le `node_modules` du front n'est pas installé dans ce worktree ; rien à rejouer côté front.

### Envoi `[V4 nn/20]`

Script `envoyer_mails_v4.py` : rend les 20 mails par le gabarit (après corrections V4) et les pousse
à Brevo, sujet préfixé `[V4 nn/20]`, **un toutes les 10 s**, destinataire **verrouillé** sur l'adresse
de test (vérifié avant chaque appel réseau). Résultats bruts : `envois_v4.json`.

> **20 et non 21** : la suppression du **doublon de réinitialisation** (11 et 17) laisse **20 mails
> distincts** — on n'envoie plus deux fois le même reset.

**Résultat : 20 / 20 partis** ✅ (07/11/2026, Brevo `/smtp/email`, expéditeur `contact@labuse.immo`)

| n | clé | sujet | messageId Brevo |
|---:|---|---|---|
| 01 | `essai` | [V4 01/20] Vos accès d'essai LABUSE — 48 h pour juger sur pièces | `<202611072002.39853176079@smtp-relay.mailin.fr>` |
| 02 | `souscription` | [V4 02/20] LABUSE — votre lien d'abonnement | `<202611072002.47538226818@smtp-relay.mailin.fr>` |
| 03 | `onboarding1` | [V4 03/20] Bienvenue sur LABUSE | `<202611072002.60687558640@smtp-relay.mailin.fr>` |
| 04 | `onboarding2` | [V4 04/20] La méthode pour trouver ce que les autres ne voient pas | `<202611072003.35826426613@smtp-relay.mailin.fr>` |
| 05 | `onboarding3` | [V4 05/20] 10 jours de LABUSE — on fait le point ? | `<202611072003.53447745597@smtp-relay.mailin.fr>` |
| 06 | `relance_carte` | [V4 06/20] LABUSE — un souci avec votre moyen de paiement | `<202611072003.68454471662@smtp-relay.mailin.fr>` |
| 07 | `suspension` | [V4 07/20] LABUSE — votre accès est suspendu | `<202611072003.79515719862@smtp-relay.mailin.fr>` |
| 08 | `retablissement` | [V4 08/20] LABUSE — votre accès est rétabli | `<202611072003.38037987744@smtp-relay.mailin.fr>` |
| 09 | `radar_digest` | [V4 09/20] Radar — 3 nouveautés le 07/11/2026 | `<202611072003.72996582352@smtp-relay.mailin.fr>` |
| 10 | `radar_alerte` | [V4 10/20] Veille « Saint-Denis — terrains de plus de 400 m² » — 3 correspondances | `<202611072004.66681579108@smtp-relay.mailin.fr>` |
| 11 | `mdp_oublie` | [V4 11/20] Réinitialisation de votre mot de passe LABUSE | `<202611072004.45244070773@smtp-relay.mailin.fr>` |
| 12 | `mdp_modifie` | [V4 12/20] Votre mot de passe LABUSE a été modifié | `<202611072004.83389205753@smtp-relay.mailin.fr>` |
| 13 | `resiliation` | [V4 13/20] Votre abonnement LABUSE prend fin le 30/11/2026 | `<202611072004.37825337275@smtp-relay.mailin.fr>` |
| 14 | `flash_pret` | [V4 14/20] Votre rapport LABUSE — 97411000BZ1065 | `<202611072004.78589423340@smtp-relay.mailin.fr>` |
| 15 | `email_change` | [V4 15/20] Votre adresse de connexion LABUSE a changé | `<202611072004.15756803335@smtp-relay.mailin.fr>` |
| 16 | `retour_traite` | [V4 16/20] Votre retour a été traité | `<202611072005.24474128211@smtp-relay.mailin.fr>` |
| 17 | `smtp_digest_notifications` | [V4 17/20] LABUSE — 2 changements sur vos suivis | `<202611072005.88252230425@smtp-relay.mailin.fr>` |
| 18 | `smtp_annonce` | [V4 18/20] LABUSE — Nouvelle source : RNU (règlement national d'urbanisme) | `<202611072005.81807641647@smtp-relay.mailin.fr>` |
| 19 | `smtp_maintenance` | [V4 19/20] LABUSE — maintenance programmée : mise à jour serveur | `<202611072005.83500335217@smtp-relay.mailin.fr>` |
| 20 | `smtp_mise_en_vente` | [V4 20/20] LABUSE — votre parcelle 97411000BZ1065 est mise en vente | `<202611072005.16687160981@smtp-relay.mailin.fr>` |


Passes précédentes : `[V2 nn/21]` (avant corrections, 21/21, `envois_v2.json`) et `[V3 nn/20]`
(20/20, `envois_v3.json`).

### Captures

- `rendus/montage-desktop.png` — les 20 mails rendus en **600 px (ordinateur)**.
- `rendus/montage-mobile.png` — les 20 mails rendus en **390 px (téléphone)** : **aucun débordement
  horizontal**, bandeau/corps/bouton/signature/pied s'adaptent.

> Les rendus ci-dessus sont produits à partir du **HTML exact** envoyé par Brevo. La vérification dans
> **Gmail ordinateur et téléphone** se fait sur la boîte de test (`victorlaganepro+mails@gmail.com`) où
> les mails `[V4 nn/20]` ont été livrés.

## Fichiers

- `src/labuse/gabarit_mail.py` — le gabarit unique (NOUVEAU).
- `src/labuse/mails_contenu.py` — le contenu des mails + specimens (NOUVEAU).
- `src/labuse/emails.py` — façade technique → délègue au gabarit (RÉÉCRIT).
- `src/labuse/brevo.py` — `envoyer_html` (transport HTML, NOUVEAU).
- `src/labuse/mail.py`, `src/labuse/mailfile.py`, `src/labuse/pige/digests.py` — transport branché.
- `tests/test_mails_1_gabarit.py` — test automatique (NOUVEAU).
- `docs/audit-2026-11/mails-1/` — ce rapport, `envoyer_mails_v4.py` (+ v2/v3), `envois_v4.json`, `rendus/`.
