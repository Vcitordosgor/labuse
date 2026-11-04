# DEPLOY-JOHN-COPILOTE4 — mise en prod de John Taylor + COPILOTE-4 (`fcd545595` → `59ce629db`)

Lancé le **2026-11-04** (matin, Réunion +04) depuis `~/Desktop/labuse-main`, prod `labuse-vps`
(`https://app.labuse.immo`, VPS `vps-5563949c`). Go de Vic pour écrire en prod, dans les seules
limites du mandat. Mêmes règles que `reports/DEPLOY-TABLEAU-1.md`. Périmètre : avancer la prod de
**`fcd545595`** (DEPLOY-TABLEAU-1) à **`59ce629db`** — c.-à-d. `main` (`4f7504e70`, qui contient
déjà les merges de `feat/john-taylor-1` et `feat/copilote-4`) **plus quatre correctifs de mise en
prod** décrits au §3. À lire d'abord : `docs/audit-2026-11/john-taylor-1/COMPTE-RENDU.md` et
`docs/audit-2026-11/copilote-4/COMPTE-RENDU.md`.

> **Bilan en une ligne.** John Taylor et COPILOTE-4 sont déployés et verts sur **`59ce629db`** ;
> **`/readyz` 200 stable, `NRestarts=0`**, gate `LABUSE_CALCUL_NUIT_PROMEUT=0` conservée, served run
> **q_v20** intact, **plafond John 50 €** posé explicitement, clé Anthropic présente (réutilisée du
> Copilote, jamais affichée), job **`john-veille` armé à 03:00 Réunion**, `resume-matin` passe par
> John (avec repli). **Schéma de John posé AVANT le redémarrage en migration tracée** (7 tables).
> **Fumée complète verte** : John répond en citant ses sources à trois questions réelles, exécute et
> journalise un ordre, refuse un ordre hors liste, affiche le coût du mois, et son carnet porte les
> décisions de Vic ; le Copilote a un accueil, tient une conversation à contexte suivi, supprime une
> conversation (cloison OK), et ne régresse pas sur la recette COPILOTE-3. **Quatre défauts réels,
> révélés par la fumée en prod, ont été corrigés** (§3) — tous nécessaires pour que John fonctionne,
> **aucun ne touche le moteur du Copilote**. Deux réserves honnêtes au §6.

---

## 0. Note de branche — « sur main » tenu

Le mandat dit « sur main », et cette fois `main` **est** la ligne de travail : `main` (`4f7504e70`)
porte déjà les merges de John et COPILOTE-4 par-dessus la base prod `fcd545595`. Les quatre
correctifs de prod (§3) et ce rapport sont commités **sur `main`** (branche courante vérifiée avant
chaque commit). La prod **ne suit pas `main` par git** : elle est déployée par **rsync de la copie de
travail** (`deploy_app.sh`) ; le SHA servi est écrit dans `config/deploiement.json`. Le HEAD servi
est **`59ce629db`**.

---

## 1. Étape 0 — pré-vol (garde-fou)

- **Première tentative ~02:57 Réunion : REPORTÉE.** Le pré-vol a trouvé **`calcul-nuit` EN COURS**
  (passe q_v21, démarrée à 02:00). Le mandat interdit de déployer pendant une passe de nuit, et un
  rsync/redémarrage mid-run aurait cassé le calcul (il importe ses modules de scoring à chaud). **Je
  n'ai pas interrompu la passe** ; j'ai surveillé jusqu'à sa fin.
- **`calcul-nuit` terminé à 04:59 Réunion, statut `ok`** (run #9461, 10 735 s ≈ 3 h ; `PROMEUT=0`
  donc calcul+contrôle+mail, pas de bascule). `resume-matin` a tourné à 07:30 sur l'ancien code
  (normal — John arrivait ensuite ; repli prévu).
- **Pré-vol final ~08:00 Réunion** (`TZ=Indian/Reunion`), précondition désormais remplie :
  **aucune sauvegarde / dump / rsync / passe Radar / calcul-nuit / injection en cours** (`pgrep`),
  **0 VACUUM**, **0 backend client non-idle**. Sauvegarde < 24 h :
  `GARDE-labuse-labuse-20261103-133003.dump` **6 559,8 Mo**, âge ~18,5 h. `/readyz` 200,
  `NRestarts=0`, disque **32 G libres / 68 %**. Cible : prod **`fcd545595`** (ancêtre strict),
  served run **q_v20** (433 229 l.).

### Filets (`cp -al`, hardlinks ≈ 0 octet — disque 32 G inchangé)
- `/opt/labuse/app` → **`app-avant-john`** (inode partagé 4517014 vérifié sur `cli.py`).
- `/opt/labuse/venv` → **`venv-avant-john`**.
- `/etc/labuse/labuse.env` → **`labuse.env.avant-john`** (640 root:labuse) ;
  `/etc/caddy/Caddyfile` → **`Caddyfile.avant-john`**.

---

## 2. Schéma — migration tracée posée AVANT le redémarrage

**Constat.** Les 7 tables de John (`john_journal`, `john_carnet`, `john_resume`, `john_veille`,
`john_ecarts_acceptes`, `john_conversations`, `john_messages`) ont leur DDL dans les modules
`john/*.py` mais sont créées **paresseusement au premier appel API**, hors du heal pré-service. Le
mandat demande de les poser **avant le redémarrage, en migration tracée**. COPILOTE-4 n'a besoin
d'aucune migration : ses tables (`copilote_conversations` / `copilote_messages`), la contrainte
**FK `ON DELETE CASCADE`** et les colonnes (`sujet`) sont déjà posées par le heal pré-service (étape
`copilote_v2`) ; la **rétention 30 j** est une valeur de config (`copilote_v2_retention_jours`), pas
du schéma.

**Fait.** `deploy/migrations/2026-11-04-john-taylor-schema.sql` (commité `4df5f02b1`) — DDL copié à
l'identique des modules (`CREATE TABLE IF NOT EXISTS`, donc les `ensure()` paresseux deviennent des
no-op), appliqué en prod **avant le premier redémarrage** : 7 `CREATE TABLE` + `COMMIT`, FK CASCADE
`john_messages → john_conversations` vérifiée. **Correctif d'appartenance** (dans la migration, §3.0) :
les tables créées par `postgres` ont été **réassignées au rôle applicatif `labuse`** (tables +
séquences), sinon l'app a « permission denied ».

---

## 3. Déploiement + quatre correctifs de prod

Déploiement par `deploy/scripts/deploy_app.sh labuse-vps` (rsync copie de travail, venv, front bâti
sur le VPS, unit systemd AUTONOMIE-2, crontab reposé == registre, `deploiement.json`, `fiche_cache`
vidé, restart, attente `/readyz` stable). Served run **q_v20** intact à chaque passe.

La fumée en prod a révélé **quatre défauts réels** (jamais vus en recette dev : le chat de John
n'avait été testé en direct que sur des appels courts, et avec des données simulées). Chacun est
corrigé par un commit tracé sur `main` ; **aucun ne touche le moteur ni les verrous du Copilote**
(mandat COPILOTE-4 « forme seule » respecté).

### 3.0 Appartenance des tables de John (`permission denied`) — commit `d00e38b6e` (migration)
La migration jouée par `psql -U postgres` a créé les tables en `postgres` ; l'app se connecte en
`labuse` → **`permission denied for table john_carnet`** (même famille que l'incident
`pige_restauration_radarfix3`). Réassignation explicite de l'appartenance des objets `john_*`
(tables + séquences) à `labuse` (idempotent ; c'est ce que la création paresseuse aurait fait). Bloc
ajouté à la migration tracée + appliqué en prod. `/admin/john` repasse **200**.

### 3.1 Blocs *thinking* d'opus-5-5 non ré-émis → 400 — commit `d00e38b6e`
`claude-opus-5-5` déclenche l'**adaptive thinking** sur le gros system prompt de John (persona +
doctrine + carnet + actions, ~3 985 car.) et renvoie des blocs `thinking`. Le ré-envoi du tour
assistant dans la boucle d'outils (`_bloc_to_dict`) ne gérait que `text`/`tool_use` → un bloc
`thinking` retombait sur `{"type":"thinking"}` **sans `thinking`/`signature`**, et l'API rejetait au
2ᵉ round : `messages.N.content.0.thinking.thinking: Field required`. Jamais vu en dev (1 seul round).
Fix : `_bloc_to_dict` préserve `thinking`/`redacted_thinking` **tels quels**. Non affichés
(anti-invention ne lit que les blocs `text`).

### 3.2 `max_tokens` trop bas → réponses tronquées — commit `2d015ee10`
Les jetons de réflexion s'imputent sur `max_tokens`. À **1200**, la réflexion finale épuisait le
budget → tour sans texte (`stop=max_tokens`) → repli « je n'ai rien à dire de sourcé ». Monté à
**8000** (réflexion + réponse ; non-streaming, sous le garde-fou timeout du SDK). Prouvé par sonde :
round 1 = `thinking`+`tool_use`, round final = `end_turn` avec texte réel.

### 3.3 Anti-invention : décimales FR « 18,7 » — commit `59ce629db`
Le scanner de nombres du socle (`_NUM_RE`) n'a **pas la virgule** dans sa classe → une décimale FR
« 18,7 » se scindait en « 18 » et « 7 », et « 18 » (absent des lectures) déclenchait un **faux refus
anti-invention** sur un fait pourtant sourcé (tailles « 6 559,8 Mo », âges « 18,7 h », %…). Fix
**isolé à `john/chat.anti_invention`** (virgule décimale → point avant le scan) : le socle `_core`
partagé avec le Copilote **n'est pas touché**. Vérifié : sourcé→accepté, non-sourcé→**toujours
rejeté** (anti-invention intact), liste « 3, 4, 5 » non fusionnée.

### État de l'unit (AUTONOMIE-2 conservé)
`ExecStartPre=/opt/labuse/venv/bin/labuse schema-heal`, `Environment=LABUSE_SKIP_BOOT_HEAL=1`,
`TimeoutStartSec=180`. Journal du dernier redémarrage : `✓ heal schéma OK (18 steps, en série, hors
service)`, workers `heal : joué AVANT le port`.

### Environnement — inchangé sauf plafond John posé explicitement
`labuse.env` (exclu du rsync) : **`LABUSE_CALCUL_NUIT_PROMEUT=0` présent avant ET après**.
**`LABUSE_JOHN_PLAFOND_EUR=50` ajouté** (le mandat le nomme ; le défaut code est déjà 50, la pose
explicite le fige). Clé **`ANTHROPIC_API_KEY` présente** (108 car., jamais affichée) — la même que le
Copilote, réutilisée par John. Modèles : défauts `claude-opus-5-5` (chat/résumé/enquête) +
`claude-haiku-5-5` (veille), repli auto 4.x, `temperature` omise (modèles qui la refusent). Conversations
John 90 j, rétention Copilote 30 j (défauts confirmés).

---

## 4. Fumée (les points du mandat)

### John — onglet « John Taylor », admin seul
| Point du mandat | Résultat |
|---|---|
| **Onglet visible en admin seulement** | ✅ tous les points `/admin/john/*` passent `exiger_admin` (401/403 sinon) + filet middleware structurel `/admin`. L'onglet et le bouton « Demander à John » sont dans le bundle admin déployé (`AdminView-*.js`). |
| **Trois questions réelles, réponses sourcées** | ✅ (1) *« Tout est à jour ? »* → « Non… quatre sujets attendent ta décision » citant les incidents `verite-sources`/escalade (écart risques, 3 parcelles). (2) *« Quelle est la dernière sauvegarde ? »* → `GARDE-…-20261103-133003.dump`, **6 559,8 Mo**, **19,1 h (0,8 j)**, 4 dumps, pas de copie hors-serveur — tout lu de `lire_sauvegardes`. (3) *« Pourquoi le calcul a échoué le 3 novembre ? »* → « 02:00:04→05:59:05, **14 340 s ≈ 4 h**, `IdleInTransactionSessionTimeout` » lu de `lire_jobs`, et dit honnêtement ne pas connaître la cause racine. |
| **Un ordre simple exécuté et journalisé** | ✅ `relancer_job healthcheck` → `{ok:true, resume:"job « healthcheck » relancé"}`, ligne au journal (`ok=True`, compte). |
| **Un ordre hors liste refusé** | ✅ `supprimer_base` → `{ok:false, refuse:true}` « hors de la liste autorisée », **journalisé** (`ok=False`). |
| **Coût du mois affiché** | ✅ `/admin/john.cout` : plafond **50 €**, dépensé **~5,0 €**, reste **~45 €**, `en_pause:false`. |
| **Le carnet contient les décisions de Vic** | ✅ 10 lignes — 6 décisions (BDNB retirée · « Priorité » masqué · noms non masqués avant 1ᵉʳ client · 7 j de grâce · calcul de nuit sur le serveur · **1ʳᵉ promotion de q_v21 sous les yeux de Vic**) + 4 doctrines. |

### Copilote — l'écran devenu conversation
| Point du mandat | Résultat |
|---|---|
| **Accueil** | ✅ servi par le serveur (`/scenarios` : hero + sous-titre « Réponse courte, sourcée, datée — La Réunion uniquement » + 4 suggestions) ; le nouvel écran deux colonnes (`CopiloteView-*.js`) porte « Sur quoi on travaille », « Nouvelle conversation », « Continuez la conversation », le bandeau « Conservées 30 j ». |
| **Conversation de 3 questions, contexte qui suit** | ✅ `conversation_id` 315 : Q1 parcelle `97415000CV1186` (fiche servie) → Q2 « et si je démolis ? » (voie Outils, moteur inchangé) → Q3 « c'est en copropriété ? » **répond sur la même parcelle sans la répéter** (« non… pas répertoriée en copropriété », source **RNIC**). |
| **Suppression d'une conversation de test** | ✅ `DELETE /missions/316` → `{ok:true}` ; `GET` après → **404** ; `DELETE` d'un id étranger → **`{ok:false}`** (cloison lot 6 : on ne supprime jamais le fil d'un autre). |
| **Affichage mobile** | ✅ code du tiroir mobile présent dans le bundle déployé (`CopiloteView-*.js`), validé à 390 px en recette COPILOTE-4 (captures `mobile-accueil-390`, `mobile-drawer-390`). *Réserve honnête : non re-rendu dans un navigateur sur la prod — l'accès client exige la 2FA nominative de Vic et il n'existe plus de compte client partagé depuis POST-DEPLOY-1.* |
| **Aucune régression sur 2 questions COPILOTE-3** | ✅ « règles de la zone U à Saint-Paul » → voie Outils (moteur inchangé) ; « contester un refus de permis » → `EXPLIQUER`, réponse réelle de 632 car. (« deux mois pour contester… »). 200, `erreur:false`, moteur intact. |

### Jobs / crontab (tz Réunion, == registre)
`john-veille` **03:00**, `resume-matin` **07:30** (réécrit par John avec repli), `calcul-nuit` **02:00**
sous `PROMEUT=0`. Résumé matin : à la prochaine échéance (07:30 demain), John l'écrit ; si John
échoue (plafond/dégradé/anti-invention), le résumé actuel part tel quel.

### 10 minutes de journaux
✅ Fenêtre de ~10 min sur le code final (`59ce629db`, 08:54→09:05 Réunion) : **0 5xx, 0 ERROR,
0 Exception/Traceback, 0 heal échoué, 0 lock timeout, 0 « permission denied »** au journal du service ;
`/readyz` et `/healthz` **200** ; `NRestarts=0` ; **0** connexion idle-in-transaction résiduelle,
**0** verrou advisory. Le réchauffage `fiche-commune-cache` du déploiement a tourné sans contention
(pas d'avertissement idle-tx sur la fenêtre).

---

## 5. État final prod

Served run **q_v20** · SHA **`59ce629db`** · `NRestarts=0` · `/readyz` 200 stable · gate
`PROMEUT=0` · plafond John **50 €**. **Filets conservés** : `app-avant-john`, `venv-avant-john`,
`Caddyfile.avant-john`, `labuse.env.avant-john` + dump `GARDE-…-20261103-133003.dump`. **Aucun retour
arrière.**

---

## 6. Réserves honnêtes & dette

1. **Flap `NRestarts` 0→1, résolu.** En enchaînant deux `deploy_app.sh` rapprochés, le réchauffage
   détaché du premier (`fiche-commune-cache`) tenait des verrous sur `events`/`pige` quand le heal
   `ExecStartPre` du second a voulu son `ACCESS EXCLUSIVE` → 1 démarrage a échoué (lock timeout),
   l'auto-restart systemd a réussi juste après. Remédié par un **restart propre** (hors réchauffage) +
   `systemctl reset-failed` → **`NRestarts=0`**. *Leçon : laisser le réchauffage finir avant un
   redéploiement* (tenu pour les passes suivantes). Même famille que l'incident heal-concurrence de
   DEPLOY-FINAL.
2. **Affichage mobile du Copilote non re-rendu en navigateur sur la prod** (cf. §4) — bundle déployé +
   recette 390 px pré-merge font foi ; pas de compte client partagé pour un rendu live.
3. **Crédit API Anthropic** : John consomme Opus/Haiku (chat ~0,33 €/question observé, veille 03:00).
   Plafond posé à 50 €/mois (coupe proprement) ; surveiller le solde du compte Anthropic.
4. **`main` non poussé par PR → prod** : la prod suit la copie de travail, pas `main`. Les 4
   correctifs + ce rapport sont commités sur `main` et poussés sur `origin/main` (ou laissés en dette
   PR si le push direct est gardé — voir note de fin).
5. **Réchauffage idle-tx** (dette héritée de TABLEAU-1) : `labuse.rechauffage` peut buter sur
   l'idle-in-transaction timeout en fin de recalcul long — sans conséquence (communes calculées,
   verrou relâché), à traiter comme OPS-NUIT-1 l'a fait pour `calcul-nuit`.

### Phase R — retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-john  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-john /opt/labuse/venv
sudo cp -p /etc/labuse/labuse.env.avant-john /etc/labuse/labuse.env
sudo install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service /etc/systemd/system/labuse.service
sudo systemctl daemon-reload && sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Les 7 tables john_* restent (neuves, aucun lecteur de l'ancien code) — inoffensives ; aucune donnée
# client touchée. Le plafond LABUSE_JOHN_PLAFOND_EUR revient par labuse.env.avant-john.
```
