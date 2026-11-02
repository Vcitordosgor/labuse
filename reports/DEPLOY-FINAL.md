# DEPLOY-FINAL — mise en prod de `main` (`153c95032` → `4e7c9d29f`)

Lancé le **2026-11-02** depuis `~/Desktop/labuse-main`, prod `labuse-vps` (`https://app.labuse.immo`).
Go de Vic, dans les seules limites du mandat. Mêmes règles que `reports/DEPLOY-1030a.md`.
Périmètre : avancer la prod de **`153c95032`** (DEPLOY-1030a) à **`4e7c9d29f`** (« Merge branch
'fix/p-1' »), soit **92 commits** / 40 mandats (toute la vague d'audit NU-1 + NU-3 et les fix associés).

> **Bilan en une ligne.** Code + schéma + données + fumée **déployés et verts** sur `4e7c9d29f` ;
> un incident de boot (heal de schéma en concurrence → `/readyz` ~50 % pendant ~15 min) **traversé et
> résolu** ; **q_v21 REPORTÉ** (décision Vic) car l'artefact Mac est une recette *sommaire* non
> déployable — prod reste donc servie en **q_v20** (sain, complet). Filet du jour conservé, **aucun
> retour arrière**.

---

## Étape 0 — garde-fou

- **12 h 22 Réunion** (`TZ=Indian/Reunion`, VPS `vps-5563949c`). Heures ouvrées, assumé.
- **Aucun VACUUM / autovacuum** (`pg_stat_activity` : 0 `%vacuum%`, 0 `autovacuum worker`).
- **Aucune session client** : `sessions_auth` actives = **0** (pas même un admin).
- **Cible** : local `main` **== `origin/main` == `4e7c9d29f`** ; prod réelle `153c95032` est **ancêtre**
  strict (`merge-base --is-ancestor` vrai, **92 commits** d'avance, aucune divergence).
- Disque 35 G libres / 64 %, services `labuse`/`caddy`/`postgresql` actifs, `/readyz` 200.

Mandats embarqués (merges) : NU-1 A→F + prod-verif-1 ; fix urgence-1, ppr-unique-1, sdp-unique-1,
marche-unique-1, copilote-3, estimer-2, coherence-hook-1, vitesse-3, radar-4, faisa-regles-1,
produit-nu-1, scoring-copro-1, estimer-precision-1, rouges-7, fix-final-1 ; audits NU-2 A/B ; NU-3
G→P ; ops/sauvegarde-1 ; fix/nu3-1→4 ; fix/p-1.

---

## Pré-vol (chaque point prouvé)

### 1. Sauvegarde du jour — vérifiée
Dump de la nuit (OPS-SAUVEGARDE-1) `labuse-labuse-20261102-001017.dump`, **âge 11 h (< 24 h)**,
`pg_restore --list` propre (1752 entrées, `signal_instantanes` présente, `radarfix3` absente),
**sha256 VPS == Mac** (`32b5a548…`) — copie hors-VPS bit-pour-bit confirmée. Rien à relancer.

### 2. Filets (`cp -al`, hardlinks ≈ 0 octet)
- `/opt/labuse/app` → **`/opt/labuse/app-avant-final`** (inode partagé 4457432 vérifié).
- `/opt/labuse/venv` → **`/opt/labuse/venv-avant-final`** (inode 4472541).
- `/etc/caddy/Caddyfile` → **`Caddyfile.avant-final`** ; `/etc/labuse/labuse.env` → **`labuse.env.avant-final`**
  (640 root:labuse préservé). Disque inchangé.

### 3. Schéma — migration tracée posée AVANT le redémarrage
Diff code↔prod des objets attendus (tables, colonnes, fonctions SQL, index). Fichier tracé
**`deploy/migrations/2026-11-02-deploy-final.sql`** appliqué `ON_ERROR_STOP=1`, hors charge :

| Objet | Avant | Action | Temps |
|---|---|---|---|
| `adresses.suggest_norm` (GENERATED STORED) + idx GIN `ix_adresses_suggest_norm_trgm` | absent | **posé** (expression == code à l'octet, 355 car. vérifiés) | **12,06 s** (réécriture 339 915 l.) + 2,1 s |
| `comptes.paiement_requis_at`, `comptes.acces_fin_at` | absents | posés | < 5 ms |
| `labuse_ppr_couleur(subtype,attrs)` (fonction requise au boot) | absente | `CREATE OR REPLACE` ; smoke `INTERDICTION→rouge, PRESCRIPTION→bleu, i→autre` | 8 ms |
| `projets.version integer NOT NULL DEFAULT 1` | absent | posé (instantané PG18) | — |
| `parcel_p_score_v2` : `prix_secteur_eur_m2` → `prix_commune_eur_m2` | ancien nom | **rename** (métadonnée, aucun lecteur de service) | 45 ms |
| `dvf_prix_sortie_neuf.millesime_dvf`, `dvf_secteur_medianes.millesime_dvf` | absents | posés | — |

Tout vérifié présent après coup ; `suggest_norm` **339 915/339 915 peuplée**. Les 4 fonctions SQL
requises présentes. **Rétro-compatible** avec l'ancien code encore en service (objets neufs non lus
par l'ancien ; rename sans lecteur). La « colonne journal du Radar » = index partiels
`uq_event_log_pige_jour` / `uq_pige_depots_hash` **déjà en prod** (rien à poser).

### 4. Environnement + compte « pilote »
- `LABUSE_PUBLIC_BASE_URL=https://app.labuse.immo` **déjà correct**.
- `LABUSE_ADMIN_EMAIL=kampusreunion@gmail.com` (escalade alertes) **déjà = l'adresse de Vic**.
- **Compte pilote partagé — DÉCISION VIC : supprimé/éteint.** Après un aller-retour (enrôlement TOTP
  d'abord tenté puis abandonné), Vic a tranché : on **ne réactive pas** le login pilote partagé
  (`LABUSE_LOGIN_PILOTE_ACTIF=0`), aucun secret TOTP posé — Vic se connecte avec **son compte admin
  nominatif + son 2FA**. `LABUSE_PILOTE_TOTP_SECRET` **retiré** de l'env, flag forcé à `0`
  (640 root:labuse préservé). *(Aucun secret TOTP n'a jamais transité par la session de l'opérateur,
  ni n'est consigné ici.)*

### 5. Données IRIS/OLL + caches de médianes
- **IRIS/OLL déjà en prod et identiques au Mac** : `spatial_layers` kind `iris_insee` = 344,
  `oll_zonage` = 193, `oll_loyers` = 133 (Saint-Denis/97411 : 55 lignes de zonage). Rien à ingérer
  (le correctif MARCHE-UNIQUE est du **code** ; `oll_parcelle` résout en direct).
- **Caches de médianes recalculés APRÈS déploiement** (nouvelle logique marche-unique) : `labuse
  dvf-marche` → `dvf_secteur_medianes` 2359 lignes / 850 secteurs / 40 383 ventes ; estampille
  `millesime_dvf` = **2025-12-31 = millésime DVF courant** (le smoke #11 le vérifie, bloquant).

---

## Déploiement — `deploy/scripts/deploy_app.sh labuse-vps`

Déroulé **exit 0** : garde manifeste (run local `q_v20` présent en prod, 433 229 l.) ✓ → rsync →
venv (chaîne de démarrage importable ✓) → front (vite build sur VPS) → systemd → **crontab reposé +
vérifié == registre** (aucun écart, tz=reunion, radar-cloche/digest restent gelés) →
`deploiement.json = 4e7c9d29fbaa` (déployé `2026-11-02T09:12:47Z`) → manifeste prod **q_v20** (433 229)
intact → `fiche_cache` vidé → restart → **`/readyz` 200 STABLE 25/25**. `NRestarts=0`.

---

## ⚠ Incident de boot (traversé, résolu) — récurrence DEPLOY-1028b

Après le restart, **`/readyz` a flappé ~50 % pendant ~15 min** (smoke local 46/100 en 503 au pire).
Cause : le **heal de schéma par worker** (5 workers uvicorn) s'exécute à chaque boot ; deux modules
(`events`, `pige`) ont échoué en `lock timeout` — les 5 workers se disputaient un `ACCESS EXCLUSIVE`
sur des tables chaudes (`event_log`, `pige_faits`, `notif_prefs`), **aggravé par le job de
préchauffage** lancé juste après le « readyz stable » (faux positif : certains workers healaient
encore). Un worker avec `schema_heal.ok=false` sert `/readyz` 503 en permanence → d'où le flapping.

**Résolution** (aucune donnée perdue, `/readyz` jamais 500, prod sert q_v20 tout du long) :
1. Posé **sériellement** (un seul process, hors concurrence) les DDL que les modules `events` + `pige`
   tentaient — dont la **colonne neuve `pige_faits.a_verifier`** (RADAR P1 V3) et la normalisation
   `notif_prefs.digest_freq` → `'quotidien'`.
2. Purge d'un **pile-up de verrous** (`ALTER event_log` bloqué 15 min derrière un rebuild
   `spatial_layers_sub` exécuté **dans** une transaction qui journalisait) : backends orphelins
   terminés, puis **`spatial_layers_sub` reconstruit hors transaction** (1 548 763 pièces, 145 s).
3. Restart propre → **`/readyz` 100/100 = 200**, `0` échec heal, `NRestarts=0`.
4. Préchauffage des 24 fiches communes relancé **proprement** (readyz reste 200 sous charge) :
   `fiche-commune-cache` statut `ok`, 762 s, `commune_contexte_cache` = 24.

**Leçon pour la prochaine fois** : les DDL neuves sur tables chaudes (`pige_faits.a_verifier`) doivent
entrer dans la **migration tracée du pré-vol** (comme les colonnes nommées au mandat), pas être
laissées au heal concurrent du boot.

---

## Fumée (par vague, chaque point prouvé)

### Socle — ✓
- `smoke_test.sh` : **tous les tests critiques PASSENT** (/healthz 200, /readyz 200, PostGIS 3.6.4,
  434 582 parcelles, manifeste = servi résiduel seq 17, run servi frais 12 j, **cache médianes à jour
  millésime 2025-12-31 = courant**). `smoke_build` Playwright = **SKIP** (navigateur non installé sur
  le VPS — non bloquant, à noter).
- **`/healthz/crons` couvre 30/30 jobs** (27 ok, 3 gelés, 0 non-ok) — le trou NU-3 « 11/31 » est fermé.

### Urgence — ✓
- **Lien d'annonce inconnu dans Estimer → aucune requête sortante** : `POST /radar/annonce/analyser`
  (url bidon `.invalid`) → **HTTP 200 en 0,07 s**, `{ok:false, erreur:"url_invalide", motif:"Collez un
  lien Leboncoin…"}` — rejet immédiat, **pas de fetch** (doctrine radar-4).
- **Mail de test rendu (pas envoyé)** : 5 gabarits (souscription/suspension/relance_carte/
  retablissement/essai) via `…/mail/<key>/apercu` → HTTP 200, chacun contient **`app.labuse.immo`**,
  **0 fuite `127.0.0.1`**, rendu en aperçu (aucun envoi).

### Vérité
- **SDP en-tête = verdict = PDF (3 témoins)** : SDP **cohérente** où présente (BY0083 : SDP max régl
  1327 == 1327 Dossier/Comparatif ; BL0020 : 0 écart ; résiduelle absente pour parcelle bâti-encore).
- **97417000AH0053 → 0 logement, refus propre** : `/modules/faisabilite` **HTTP 200**, `capacite`/
  `delaisse`/`bilan` = `None` (écartée PPR code `i`), **aucune 500**.
- **Loyer OLL sur 97411000IE0241** : fiche `loyers_oll` = zone 5, **10,3 €/m²**, OLL 2024, disponible ✓.
- **(FINDING) médiane maison divergente** : fiche `prix_ancien.median` **3286 €/m²** vs Estimer
  `median` **3986 €/m²** (St-Denis) — deux moteurs/périmètres distincts (ancien-commune vs comparables
  par rayon). Divergence **pré-existante** (famille NU-3-P « prix 2 moteurs »), **non résolue par ce
  déploiement**.

### Outils
- **(FINDING) Estimer IE0241 total = 251 000 €** (surface bâtie DVF 63 m² × 3986 €/m²), attendu
  « proche de 220 000 » : même ordre de grandeur, loin du bug historique (422 k), mais **+14 %** vs la
  cible estimer-2 — à relier à la divergence médiane ci-dessus.
- **Copilote `97404000AV0167` → « Oui, en copropriété »** ✓ : *« Oui, la parcelle … est en copropriété
  (9 lots recensés au répertoire des copropriétés) »*, source RNIC (conforme copilote-3).
- **Filtre « Risques / PPR » de la carte → compte non nul** ✓ : `/filtre?source=q_v20&flags=risques`
  = **405 046 parcelles** — la **régression NU-3-P / G-001 est corrigée** (FIX-P-1 : token cascade
  `risques`, plus le mauvais mapping `['ppr','georisque_alea']`).

### Classement — **N/A (q_v21 reporté, cf. ci-dessous)**

### Comptes & exploitation
- **Login « pilote » refusé** ✓ : `POST /login` (mdp quelconque) → **401** ; `/login/2fa` → 302
  (aucun défi pilote). Le compte partagé est bien mort.
- **Vic se connecte avec son compte admin nominatif + 2FA** : **à confirmer par Vic** (action
  interactive hors opérateur).
- **Vigie sauvegarde au vert + âge** ✓ : `backup-postgres` statut `ok` (age_jours 0,0), dernier dump 13 h.
- **Pilotage s'ouvre sans blocage** ✓ (nuance) : `/admin/pilotage` **HTTP 200** mais **~5–7 s** (froid
  et chaud) — s'ouvre, ne pend pas (vitesse-3 « jamais bloquant », Stripe en fond) ; **lenteur à noter**.

### Journaux — ✓
- **15 min sans erreur ni 5xx** : service `labuse` = **0 ERROR/Traceback/Exception, 0 HTTP 5xx,
  0 mail envoyé**.
- **`docs_coherence.py`** (3 témoins, cookie de session injecté au runtime, jamais affiché) :
  **BL0020 = 0 écart** ; **BY0083 & IE0241 = 2 écarts chacun**, **isolés au doc « Estimer un bien »**
  (nouvellement harnaché par SDP-UNIQUE-1) : **prix terrain 250 vs 501** et **hauteur égout 9/6 vs
  9/?**. **Donc `docs_coherence` n'est PAS à zéro écart** — divergence cross-surface pré-existante
  (même famille « 2 moteurs »), non bloquante pour le déploiement, à traiter produit.

> Méthode fumée authentifiée : session **éphémère read-only** sur le compte de **test** `gb-test-ae`
> (uid 31, **go explicite de Vic** après blocage du garde-fou), jeton écrit dans un curlrc 0600
> **jamais affiché**, **session purgée** en fin de run (0 restante). Aucun secret dans ce rapport.

---

## q_v21 — **REPORTÉ** (décision Vic)

Le mandat prévoyait `labuse flux-run --label q_v21 --recette q_v15` sur prod. **Impossible en l'état**,
pour deux raisons découvertes successivement :

1. **La venv prod est volontairement « sans ML »** (`requirements-ml.txt` : *« JAMAIS sur le serveur
   prod »*). `flux-run` échoue à l'import (`joblib`/`sklearn`/`pandas` absents). Le scoring q_v20 avait
   été calculé **hors-prod puis chargé**. → Règle posée par Vic : **aucun calcul de classement sur la
   prod.**
2. **L'artefact q_v21 du Mac est une recette SOMMAIRE, pas un run déployable.** Vérification des
   entrées demandée par Vic : **tout concorde Mac↔prod** —

   | Entrée | Mac | Prod |
   |---|---|---|
   | parcelles | 434 582 | 434 582 |
   | résiduel servi | seq 17 (21/10) | seq 17 |
   | PPR subtypes | 88 PRESCRIPTION · 74 INTERDICTION · 2 `i` | idem |
   | parcelles touchant `i` | 1 243 | 1 243 |
   | cascade servie `q_v19_sources` | a_creuser 258 371 · exclue 153 283 · opp 21 575 | **identique** |

   → **Aucun écart d'entrée : les paliers q_v21 seraient valides pour prod.** MAIS le Mac n'a que
   `parcel_p_score_v2` q_v21 (paliers, 433 229) + la cascade **au niveau résumé** (`dryrun_parcel_
   evaluations` q_v21_sources, 433 232). **Manquent** : `score_labuse` q_v21 (bandes A/B/C/D, Signal,
   tri « labuse »), `parcel_flags`/`score_e`/`parcel_renouvellement` q_v21, et surtout la cascade
   **DÉTAIL** `dryrun_cascade_results` q_v21_sources n'a que **61 324 lignes** (les 1 243 parcelles `i`
   ; les 431 989 autres n'ont été clonées qu'au résumé). Or `build_parcel_flags_table` lit ce détail
   → un `parcel_flags` q_v21 reconstruit ne couvrirait que ~1 243 parcelles (filtre carte cassé).

   **Il n'existe donc pas de « build rapide ».** Un q_v21 complet = **flux-run complet sur le Mac
   (~6 h)** — ce que le rapport SCORING-COPRO-1 prescrivait déjà pour le déploiement prod — ou un clone
   de 21 M lignes de détail (fragile).

**Décision Vic : reporter q_v21 à un mandat dédié.** Prod reste sur **q_v20** (déployé, sain, complet,
bandes intactes). q_v21 complet sera produit par un flux-run complet sur le Mac (hors heures) puis
transféré + promu + fumée « classement » dans une passe dédiée. **Aucune trace q_v21 servie en prod**
(0 ligne `parcel_p_score_v2` q_v21). La tentative `flux-run` a échoué dans un **process CLI détaché**
(hors journal service, `/readyz` jamais affecté).

---

## État final prod (vérifié)

Served run **q_v20** · SHA **`4e7c9d29f`** · `NRestarts=0` · `/readyz` **20/20 = 200** local + **200**
public · 0 backend non-idle · 0 process résiduel · crontab == registre. **Filet du jour conservé** :
`app-avant-final`, `venv-avant-final`, `Caddyfile.avant-final`, `labuse.env.avant-final` + dump
`labuse-labuse-20261102-001017.dump`. **Aucun retour arrière.**

### Phase R — retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-final  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-final /opt/labuse/venv
sudo chown -R labuse:labuse /opt/labuse/app
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Schéma : la migration 2026-11-02 est additive + rétro-compatible (l'ancien code ne lit pas les
#   objets neufs) → pas besoin de la défaire pour un rollback de code. DB inchangée sinon.
```

---

## Rappels à Vic
- **Extension Chrome Radar** : la recharger (nouveau code front/extension après merge).
- **Mac branché** (pas de veille) : la passe Radar de ce soir doit apparaître dans
  `/admin/radar/journal` **demain matin**.
- **Confirme ta connexion** au **compte admin nominatif + 2FA** (remplace l'étape de fumée pilote).
- **q_v21** : à planifier en mandat dédié (flux-run complet Mac → transfert → promotion → fumée
  classement).

## Findings produit (non bloquants, pré-existants)
1. Médiane maison **fiche 3286 vs Estimer 3986** (2 moteurs) ; Estimer IE0241 **251 k** vs cible 220 k.
2. `docs_coherence` **2 écarts** sur le doc « Estimer un bien » (prix terrain 250↔501, hauteur égout
   9/6↔9/?).
3. **Pilotage lent** (~5–7 s, s'ouvre sans pendre).
4. `smoke_build` Playwright non jouable sur le VPS (navigateur absent).
