# MAILS-1 — un seul gabarit, 21 mails justes

- **Date** : 07/11/2026 · **Branche / worktree** : `feat/mails-1` · `~/Desktop/labuse-mails2`
- **Modèle** : Opus · **Ports** : 9800 / 7000 (non requis — travail hors-ligne + envoi Brevo)
- **Prod** : jamais touchée · **Merge** : non · **Envois de test** : uniquement `victorlaganepro+mails@gmail.com`
- **Maquette suivie** : `~/Downloads/Maquette — gabarit des mails LABUSE.html` (validée Vic)

## Ce qui a été fait

Un **gabarit unique**, rendu par l'app, décline **les 21 mails** du catalogue NU5-C. **Brevo
n'est plus qu'un transport** : le HTML (e-mail compatible Gmail / Apple Mail / Outlook — tableaux,
styles en ligne, 600 px, lisible sur téléphone) + la version texte **partent du code**, plus aucun
`templateId`. Les modèles Brevo ne sont plus utilisés.

### 1. Le gabarit — `src/labuse/gabarit_mail.py`

Reproduit la maquette au pixel, mais en **HTML e-mail sûr** (tables + styles en ligne, pas de flex/grid) :

- **Bandeau sombre** `#0b0e0c` : logo `LA`**`BUSE`** (BUSE en `#7ee0a0`) + baseline
  « **Le trésor est sous vos pieds** » à droite.
- **Corps blanc**, 600 px, 15 px/1.6.
- **Bouton vert** `#1f7a46` (table + `bgcolor` → rendu fiable jusque dans Outlook), jamais un lien brut.
- Blocs : paragraphe, note, **étapes numérotées** (pastilles rondes), **carte** (critères),
  **liste de biens** (Radar), **encadré** (maintenance), ligne de fait (digest), lien secondaire.
- **Deux registres** :
  - **personnel** — signature « **Victor Lagane**, fondateur de LABUSE · je lis chaque réponse ·
    **+262 693 51 71 53** » (avatar « VL ») ;
  - **automatique** — **étiquette de couleur selon la nature** (vert Radar/veille/vente, bleu rapport,
    ambre maintenance, ardoise nouveauté), faits en clair, **pas de signature**.
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
- **Un seul mail de réinitialisation** : `mdp_oublie` et `smtp_reset_password` rendent le **même** corps.
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

Sur **chaque** mail (21 + `essai_fin_proche`), vérifie : **bouton** vert cliquable · **signature**
(personnel) / **étiquette** (auto) · **pied** (contact, Confidentialité, Mentions légales, et
désinscription sauf sécurité) · **aucun lien mort** ni variable `{{ … }}` · corrections de fond.
Plus : reset unique, Radar liste chaque bien, maintenance quoi/quand/quoi-faire.

→ **157 cas, tous verts.**

### Suite unitaire (famille du hook)

`pytest -m "not db and not local and not reel and not network"` → **2988 passés, 0 échec**
(50 ignorés = environnement : base live / front non bâti). Tests de contenu mis à jour pour le nouveau
gabarit (annonce/maintenance/digest/mise-en-vente), tests de la file `mail_queue` mis à jour vers le
transport `brevo.envoyer_html` (machine à états inchangée).

**Front : non concerné** — **0 fichier `frontend/` modifié** (le changement est 100 % back-end + mails).
Le `node_modules` du front n'est pas installé dans ce worktree ; rien à rejouer côté front.

### Envoi `[V2 nn/21]`

Script `envoyer_mails_v2.py` : rend les 21 mails par le gabarit et les pousse à Brevo, sujet préfixé
`[V2 nn/21]`, **un toutes les 10 s**, destinataire **verrouillé** sur l'adresse de test (vérifié avant
chaque appel réseau). Résultats bruts : `envois_v2.json`.

**Résultat : 21 / 21 partis** ✅ (07/11/2026, Brevo `/smtp/email`, expéditeur `contact@labuse.immo`)

| n | clé | sujet | messageId Brevo |
|---:|---|---|---|
| 01 | `essai` | [V2 01/21] Vos accès d'essai LABUSE — 48 h pour juger sur pièces | `<202611071854.87621556257@smtp-relay.mailin.fr>` |
| 02 | `souscription` | [V2 02/21] LABUSE — votre lien d'abonnement | `<202611071854.80329762239@smtp-relay.mailin.fr>` |
| 03 | `onboarding1` | [V2 03/21] Bienvenue sur LABUSE | `<202611071854.25058496524@smtp-relay.mailin.fr>` |
| 04 | `onboarding2` | [V2 04/21] La méthode pour trouver ce que les autres ne voient pas | `<202611071854.48041498957@smtp-relay.mailin.fr>` |
| 05 | `onboarding3` | [V2 05/21] 10 jours de LABUSE — on fait le point ? | `<202611071854.61878595403@smtp-relay.mailin.fr>` |
| 06 | `relance_carte` | [V2 06/21] LABUSE — un souci avec votre moyen de paiement | `<202611071854.52291673148@smtp-relay.mailin.fr>` |
| 07 | `suspension` | [V2 07/21] LABUSE — votre accès est suspendu | `<202611071855.36562734982@smtp-relay.mailin.fr>` |
| 08 | `retablissement` | [V2 08/21] LABUSE — votre accès est rétabli | `<202611071855.47022106469@smtp-relay.mailin.fr>` |
| 09 | `radar_digest` | [V2 09/21] Radar — 3 nouveautés le 07/11/2026 | `<202611071855.38464067212@smtp-relay.mailin.fr>` |
| 10 | `radar_alerte` | [V2 10/21] Veille « Saint-Denis — terrains de plus de 400 m² » — 3 correspondances | `<202611071855.77586992792@smtp-relay.mailin.fr>` |
| 11 | `mdp_oublie` | [V2 11/21] Réinitialisation de votre mot de passe LABUSE | `<202611071855.96854380854@smtp-relay.mailin.fr>` |
| 12 | `mdp_modifie` | [V2 12/21] Votre mot de passe LABUSE a été modifié | `<202611071855.72090101058@smtp-relay.mailin.fr>` |
| 13 | `resiliation` | [V2 13/21] Votre abonnement LABUSE prend fin le 30/11/2026 | `<202611071856.65697120399@smtp-relay.mailin.fr>` |
| 14 | `flash_pret` | [V2 14/21] Votre rapport LABUSE — 97411000BZ1065 | `<202611071856.15385592206@smtp-relay.mailin.fr>` |
| 15 | `email_change` | [V2 15/21] Votre adresse de connexion LABUSE a changé | `<202611071856.14444906294@smtp-relay.mailin.fr>` |
| 16 | `retour_traite` | [V2 16/21] Votre retour a été traité | `<202611071856.49321914555@smtp-relay.mailin.fr>` |
| 17 | `smtp_reset_password` | [V2 17/21] Réinitialisation de votre mot de passe LABUSE | `<202611071856.96664334633@smtp-relay.mailin.fr>` |
| 18 | `smtp_digest_notifications` | [V2 18/21] LABUSE — 2 changements sur vos suivis | `<202611071856.68703303659@smtp-relay.mailin.fr>` |
| 19 | `smtp_annonce` | [V2 19/21] LABUSE — nouvelle source : RNU (règlement national d'urbanisme) | `<202611071857.73156909612@smtp-relay.mailin.fr>` |
| 20 | `smtp_maintenance` | [V2 20/21] LABUSE — maintenance programmée : mise à jour serveur | `<202611071857.36478031508@smtp-relay.mailin.fr>` |
| 21 | `smtp_mise_en_vente` | [V2 21/21] LABUSE — votre parcelle 97411000BZ1065 est mise en vente | `<202611071857.59728926351@smtp-relay.mailin.fr>` |


### Captures

- `rendus/montage-desktop.png` — les 21 mails rendus en **600 px (ordinateur)**.
- `rendus/montage-mobile.png` — les 21 mails rendus en **390 px (téléphone)** : **aucun débordement
  horizontal**, bandeau/corps/bouton/signature/pied s'adaptent.

> Les rendus ci-dessus sont produits à partir du **HTML exact** envoyé par Brevo. La vérification dans
> **Gmail ordinateur et téléphone** se fait sur la boîte de test (`victorlaganepro+mails@gmail.com`) où
> les 21 mails `[V2 nn/21]` ont été livrés.

## Fichiers

- `src/labuse/gabarit_mail.py` — le gabarit unique (NOUVEAU).
- `src/labuse/mails_contenu.py` — le contenu des 21 mails + specimens (NOUVEAU).
- `src/labuse/emails.py` — façade technique → délègue au gabarit (RÉÉCRIT).
- `src/labuse/brevo.py` — `envoyer_html` (transport HTML, NOUVEAU).
- `src/labuse/mail.py`, `src/labuse/mailfile.py`, `src/labuse/pige/digests.py` — transport branché.
- `tests/test_mails_1_gabarit.py` — test automatique (NOUVEAU).
- `docs/audit-2026-11/mails-1/` — ce rapport, le script d'envoi, `envois_v2.json`, captures.
