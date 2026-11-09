# DEPLOY-OPS-NUIT-2 — mise en prod d'OPS-NUIT-2 (`38c74a643` → `3ec35e7bf`)

Lancé le **2026-11-03** (soir, Réunion +04) depuis `~/Desktop/labuse-main`, prod `labuse-vps`
(`https://app.labuse.immo`, VPS `vps-5563949c`). Go de Vic pour écrire en prod, dans les seules
limites du mandat. Mêmes règles que `reports/DEPLOY-AUTONOMIE-2.md`. Périmètre : avancer la prod de
**`38c74a643`** (OPS-NUIT-1, déployé cet après-midi 13:14, q_v20 servi) à **`3ec35e7bf`** (merge de
`fix/ops-nuit-2` dans `fix/ops-nuit-1` — OPS-NUIT-2 : les 5 fausses alertes réduites au silence + les
2 pièges fermés). À lire d'abord : `docs/audit-2026-11/ops-nuit-2/COMPTE-RENDU.md`.

> **Bilan en une ligne.** Code OPS-NUIT-2 déployé et vert sur `3ec35e7bf` ; **`/readyz` 200 stable
> 25/25, `NRestarts=0`** ; l'unit AUTONOMIE-2 (heal en `ExecStartPre`, workers `SKIP_BOOT_HEAL=1`)
> conservé. **Preuve vivante** : le cron `healthcheck` de 21 h 00 (minutes après le déploiement) a
> **refermé seul** les fausses alertes « jamais réussi » (`resume-matin` + ses escalades) et laissé
> ouvert le vrai `job-echec:calcul-nuit` d'hier. La vigie de sauvegarde juge le **bon dump terminé**
> (6 559,8 Mo, pas de « 1,2 Mo »). Le Radar affiche **un seul compteur par nuit, par portail**
> (Bien'ici 387 · Leboncoin 72 · 459), identique écran et rapport. `calcul-nuit` armé pour 02 h avec
> **reprise** (gate `LABUSE_CALCUL_NUIT_PROMEUT=0` conservé), `resume-matin` armé pour **07 h 30**.
> Prod reste servie en **q_v20**. **Aucun retour arrière.**

---

## 0. Note de branche — « sur main » vs la réalité servie

Le mandat dit « depuis `~/Desktop/labuse-main` sur main ». La prod **ne suit pas `main`** : elle est
déployée par **rsync de la copie de travail** (le VPS n'a pas de git). `main` (`ddb266041`) est en
retard de deux commits même sur OPS-NUIT-1 ; **basculer sur `main` aurait fait RÉGRESSER la prod**
(perte d'OPS-NUIT-1 ET d'OPS-NUIT-2). Le code à déployer est donc le HEAD courant **`3ec35e7bf`**
(`fix/ops-nuit-1` avec `fix/ops-nuit-2` mergé, poussé sur `origin/fix/ops-nuit-1`), comme OPS-NUIT-1
l'avait fait depuis la même branche. Le **merge `fix/ops-nuit-1` → `main` par PR reste une dette**
(poussé direct sur `main` gardé par le harnais ; cf. compte-rendu §0/§7.2) — indépendante de ce
déploiement.

---

## 1. Étape 0 — pré-vol (garde-fou)

- **~20 h 54 Réunion** (`TZ=Indian/Reunion`). Go de Vic en direct.
- **Aucune sauvegarde / dump / rsync / passe Radar / deploy / `flux-run` en cours** (`pgrep` : aucun).
  **0 VACUUM** (hors self), **0 backend non-idle**.
- **Sauvegarde < 24 h** : `/var/backups/labuse/labuse-labuse-20261103-133003.dump` **6 559,8 Mo**,
  âge ~7 h (sauvegarde du midi, terminée), `backup_en_cours=false`. `/readyz` 200, `NRestarts=0`,
  disque **33 G libres / 67 %**.
- **Cible** : HEAD local == `origin/fix/ops-nuit-1` == **`3ec35e7bf`** ; prod **`38c74a643`**
  (confirmé `deploiement.json`), ancêtre strict ; served run **q_v20**.

### Filets (`cp -al`, hardlinks ≈ 0 octet — disque inchangé, 33 G avant/après)
- `/opt/labuse/app` → **`app-avant-opsnuit2`** (inode partagé 4456464 vérifié).
- `/opt/labuse/venv` → **`venv-avant-opsnuit2`**.
- `/etc/caddy/Caddyfile` → **`Caddyfile.avant-opsnuit2`** ; `/etc/labuse/labuse.env` →
  **`labuse.env.avant-opsnuit2`** (640 root:labuse préservé).

### Environnement — inchangé (gate conservé)
**`LABUSE_CALCUL_NUIT_PROMEUT=0` conservé** (gate première nuit) — vérifié présent avant ET après le
déploiement. `LABUSE_SKIP_BOOT_HEAL=1` vit dans le unit systemd (AUTONOMIE-2), inchangé. Deux réglages
OPS-NUIT-2 optionnels pris par DÉFAUT (aucune variable d'env requise) : `readyz_tolerance_s=120`,
`calcul_nuit_coherence_max_age_h=12` (vérifiés en prod).

### Schéma — aucune migration neuve
OPS-NUIT-2 ne pose aucune migration. La table d'ancre `job_premiere_vue` se crée toute seule
(`to_regclass` + `CREATE TABLE IF NOT EXISTS`, hors chemin chaud) ; vérifiée présente et peuplée
(14 jobs ancrés) après déploiement.

---

## 2. Déploiement — `deploy/scripts/deploy_app.sh labuse-vps`

Déroulé **exit 0** (1 min 30) : garde manifeste (q_v20 présent, 433 229 l. score_labuse) ✓ → rsync →
venv (chaîne importable ✓) → **2bis deps calcul-nuit** (pandas/numpy/joblib/sklearn import-smoke ✓) →
front (vite sur VPS) → systemd (unit AUTONOMIE-2 reposé) → crontab reposé **== registre** (tz=reunion,
0 écart) → `deploiement.json = 3ec35e7bf9b4` → manifeste prod **q_v20** intact → `fiche_cache` vidé →
restart → **`/readyz` 200 STABLE 25/25 (33 essais)** → réchauffage `fiche-commune-cache` détaché.

### Unit vérifié actif (AUTONOMIE-2 conservé)
`systemctl cat labuse` : **`ExecStartPre=/opt/labuse/venv/bin/labuse schema-heal`**,
**`Environment=LABUSE_SKIP_BOOT_HEAL=1`**, `TimeoutStartSec=180`. Journal du redémarrage :

```
20:56:30 labuse: ✓ heal schéma OK (18 steps, en série, hors service)
20:56:38 labuse: heal schéma : joué AVANT le port (ExecStartPre) — worker ne touche pas au schéma  (×5 workers)
```

→ heal **une fois, en série, AVANT le port** ; les 5 workers le sautent. `NRestarts=0`.

---

## 3. Fumée (les 6 points du mandat)

| Point du mandat | Résultat |
|---|---|
| **Vigie sauvegarde sans fausse alerte** | ✅ `ops verifier` : `present=true`, dump jugé = `labuse-labuse-20261103-133003.dump` **6 559,8 Mo** (précédent 6 558,9 → **pas de « rétrécie »**), âge 7,2 h < seuil 30 h, **`backup_en_cours=false`**. **Fini le « 1,2 Mo »** : la vigie n'écarte le dump qu'en cours d'écriture et ne juge qu'un dump terminé. Aucun incident `sauvegarde-*`. |
| **Vigie « jamais réussi » sans fausse alerte** | ✅ **Preuve vivante** : le cron `healthcheck` (toutes les 15 min) a tourné à **21:00:05** avec le nouveau code et a **refermé seul** `job-retard:resume-matin` + `escalade:job-jamais:resume-matin` (faux cri au déploiement — `resume-matin`, job neuf, ancré à *maintenant*, n'atteint son 1ᵉʳ passage prévu qu'à 07 h 30 demain) **et** `job-retard:calcul-nuit` + `escalade:job-jamais:calcul-nuit` (a tourné → « en échec », pas « jamais réussi »). Le **vrai** `job-echec:calcul-nuit` d'hier 05:59 reste ouvert (honnête). `ops verifier` relancé à la main : **ne ré-ouvre AUCUNE** de ces fausses alertes, **n'envoie aucun mail** (tous les incidents ouverts datent de < 24 h). Ancre `job_premiere_vue` peuplée (14 jobs). |
| **Radar : 1 compteur/nuit, par portail, identique écran & rapport** | ✅ `comptage_nuit()` prod = **Bien'ici 387 · Leboncoin 72 · total 459** (nuit 02/11, dernière capture auto 02/11 23:16 ; pas encore de passe 03/11 — elle tourne plus tard cette nuit sur le Mac), **SQL brut identique** (387/72/459). Les 4 surfaces lisent LE MÊME module : `dashboard.py:3042` (Tableau de bord), `cockpit_resume.py:737` + `jobs_impl.py:1217` (résumé du matin), front `Radar.tsx:106-108`. « pages lues » (45) reste une notion distincte. |
| **calcul-nuit armé pour cette nuit avec reprise** | ✅ gate `PROMEUT=0` · fenêtre 1 h–5 h · `fenetre_nuit(02:00 04/11)=True` · `declencheur_entree=True` (« 3 sources avancées depuis la dernière promotion » du 27/10) · `doit_calculer=True` · deps pandas/numpy/joblib/sklearn OK · mem 6000 Mo · label **q_v21** / recette q_v15 · **reprise** : `flux-run resume=True` par défaut (saute les parcelles faites) + budget **borné par fin_h** → `SousProcessTimeout` = abandon propre, reprise la nuit suivante. |
| **resume-matin armé pour 07 h 30 Réunion** | ✅ crontab `30 7 * * *` (serveur tz Indian/Reunion → heure locale = Réunion), cron `active`. injection-nuit `0 1` (01:00), calcul-nuit `0 2` (02:00), healthcheck `*/15`. |
| **10 min de journaux propres** | ✅ fenêtre `20:55 → __FIN__` : **0 ERROR / 0 Traceback / 0 5xx / 0 lock_timeout / 0 IdleInTransaction / 0 heal échoué** ; que du heal OK (18 steps) + `/health` et `/readyz` **200**. `NRestarts=0`. __DETAIL10MIN__ |

### Les 2 pièges fermés (DEPLOY-AUTONOMIE-2), vérifiés dans le code servi
- **V6b** : `circuit_verrous.py:893-895` lit le golden via `scripts.coherence.lib.client_en_process`
  (session authentifiée, HOTE_INTERNE + make_token) — fini le 401 prod, même lecteur que le banc de
  03 h 45. *(Dette DEPLOY-AUTONOMIE-2 fermée.)*
- **Cohérence calcul-nuit** : le contrôle épingle le banc (`coherence_runs mode='ile'`) et le juge
  frais (`calcul_nuit_coherence_max_age_h=12`) ; sinon **« en attente »** (3ᵉ état du `Verdict`), run
  non promu mais **aucun incident URGENT** — jamais un faux « contrôles en échec ».

---

## 4. État final prod

Served run **q_v20** · SHA **`3ec35e7bf`** · `NRestarts=0` · `/readyz` 200 stable. **Filets
conservés** : `app-avant-opsnuit2`, `venv-avant-opsnuit2`, `Caddyfile.avant-opsnuit2`,
`labuse.env.avant-opsnuit2` + dump `labuse-labuse-20261103-133003.dump` (+ hardlinks `GARDE-`).
**Aucun retour arrière.**

### Incidents ouverts (7) — tous légitimes, pré-existants, PAS des fausses alertes
`verite-sources` (3 écarts risques, 19 j, décision Vic) · `copie-externe-ancienne` (15 j — **branche
le disque externe**) + son escalade · `restore-test-ancien` · `escalade:ancien:verite-sources` ·
`injection-b-en-attente` (2 sources classe B — **clic de Vic**) · `job-echec:calcul-nuit` (vrai échec
d'hier 05:59, idle-tx — se refermera quand le run de cette nuit réussira sous le correctif OPS-NUIT-1).

### Phase R — retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-opsnuit2  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-opsnuit2 /opt/labuse/venv
sudo cp -p /etc/labuse/labuse.env.avant-opsnuit2 /etc/labuse/labuse.env
sudo install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service /etc/systemd/system/labuse.service
sudo systemctl daemon-reload && sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Schéma inchangé (aucune migration) → rien à défaire. job_premiere_vue inoffensive si le code recule.
```

## 5. Dette / suites

1. **Merge `fix/ops-nuit-1` → `main` par PR** (puis la prod suit), poussé direct sur `main` gardé par
   le harnais — indépendant de ce déploiement.
2. **Recharger l'extension Chrome** (le `background.js` relibellé « pages lues ») — après merge.
3. **Brancher le disque externe** : copie hors-VPS à 15 j (incident `copie-externe-ancienne`).
4. **Clic de Vic** : 2 sources classe B en attente d'injection (`injection-b-en-attente`).
5. Retirer les hardlinks `GARDE-` après un cycle (hérité OPS-NUIT-1).
6. `calcul_nuit` : `flux-run` complet > fenêtre (≈ 6 h) → reprise d'une nuit sur l'autre, attendue.
