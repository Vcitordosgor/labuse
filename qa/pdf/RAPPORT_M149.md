# M149 — L'attestation ne s'émet plus par accident (`fix/m149-attestation-cloison`)

Branché sur `origin/main` @ `111f2376`, périmètre intact. Applique la reco E de l'audit M148 (F4).
**CC ne merge jamais.**

**Résumé : la référence officielle `LZ-` n'est plus émise que derrière une session (sans compte, le PDF
se rend mais SANS numéro, et le dit) ; la numérotation passe d'un `count(*)+1` collisionnable à une
SÉQUENCE Postgres atomique et non réutilisable. Un déploiement laissé en `env=local` fait désormais
échouer le boot (garde symétrique de `exiger_secret_prod`). Lettre et argumentaire rejoignent le
rate-limit 60/min. 3 fichiers de code + 2 de tests ; ruff 0 nouvelle ; contrôles verts.**

---

## Lot 1 — la numérotation LZ- (cloison + séquence)

`src/labuse/api/lettre_zonage.py`.

**Cloison `compte_id`.** `_ref_attestation(db, idu, compte_id)` : sans compte → renvoie `None`, **aucune
écriture**. Le compte vient de `request.state.compte_id` (posé par `_auth_guard`), threadé
endpoint → `_build_pdf` → `_ref_attestation`. Sans numéro, la lettre **se rend quand même** mais le DIT :
- couverture (`_identification`) : « Édition **sans référence enregistrée** (générée sans compte) » au
  lieu d'un « Référence LZ-… » forgé ;
- clôture (`_cloture`) : « …**sans référence enregistrée** : cette copie n'est pas une attestation
  numérotée et son authenticité n'est pas vérifiable auprès de LABUSE. »

Une attestation numérotée au nom de LABUSE ne s'émet donc plus par accident — ni anonyme, ni si `env`
est mal posé (defense-in-depth : ce point ne dépend plus du seul garde global).

**Séquence Postgres.** Remplace le `count(*) + 1` (constat M148 : collisionnable sous concurrence,
débordant, sensible aux suppressions) par une **séquence dédiée** `lettre_zonage_ref_seq` :
`nextval` atomique, jamais réutilisé. Alignée **une seule fois** à la création (`WHERE is_called=false`)
au-dessus de l'espace de numérotation hérité (`max(split_part(ref,'-',3)::int)`) → aucune collision avec
les réfs `count(*)` déjà en base. Colonne `compte_id` ajoutée à `lettre_zonage_refs` (traçabilité de
l'émetteur, `ALTER … ADD COLUMN IF NOT EXISTS`).

**Contrôles (base réelle, vrai code) :**
```
0) compte_id=None      -> ref=None, écriture=0                       ✓
1) deux gén. CONCURRENTES (2 threads/connexions)
   -> A=LZ-2026-0020  B=LZ-2026-0021   distinctes                    ✓
2) réf LZ-2026-0022 SUPPRIMÉE -> suivante LZ-2026-0023
   (numéro 22 NON réutilisé — la séquence ne recule pas)             ✓
   (nettoyage : réfs de test supprimées, base rendue à l'état initial)
```
Unitaires ajoutés (`tests/test_lettre_zonage.py`, sans DB) : couverture et clôture rendues sans numéro
quand `ref=None` (aucun « LZ- » forgé). **11/11 verts.**

## Lot 2 — garde-fou d'environnement (ops, gratuit)

`src/labuse/api/auth.py` + `app.py`. `exiger_env_deploiement()` — **jumeau symétrique** de
`exiger_secret_prod`, appelé au boot (`_lifespan`). Invariant : **clé de signature persistante ⟺
déploiement**. Un `LABUSE_SECRET_KEY` posé en `env='local'` trahit un déploiement laissé en dev (auth
désactivée = routes ouvertes, dont l'émission d'attestations) → **le boot échoue** (RuntimeError, message
actionnable) plutôt que d'ouvrir.

Signal choisi = `secret_key` (et non le host — la prod bind `127.0.0.1` derrière nginx, cf.
`deploy/systemd/labuse.service:28` ; ni `auth_password` — dont la config encourage l'usage local) :
**les deux exemples de déploiement (`.env.pilot.example:28`, `deploy/env/labuse.env.example:27`) posent
la clé**, aucun dev pur ne la pose (clé éphémère par défaut documenté). Aucun test ne boote avec
`(local + secret_key)` (le seul test `(local + secret_key)`, `test_pay_token_sans_secret_en_dur`, ne
déclenche pas le lifespan). Test ajouté `test_env_local_avec_secret_key_refuse_le_boot` (verts : local+clé
lève, local sans clé passe, pilot+clé passe).

## Lot 3 — rate-limit sur les deux routes lourdes

`src/labuse/api/protection.py`. `/lettre-zonage` et `/argumentaire` rejoignent `PREFIXES_PROTEGES` →
régime 60/min existant. Vérifié dans `garde_protection` (l.296-406) : pour ces chemins, seul le
rate-limit s'applique (le `_FICHE_RE` `^/parcels/…$` ne matche pas, la branche `/map|/parcels/export` non
plus) — pas de faux comptage de quota-fiche.

---

## Contrôles finaux

- **py_compile** vert (5 fichiers). **ruff** : **0 erreur nouvelle** — delta 0 sur les 6 fichiers vs
  `origin/main` (lettre_zonage 3=3, auth 0=0, app 16=16, protection 0=0, tests 0=0 / 52=52 ; dette
  préexistante inchangée).
- **Tests** : `test_lettre_zonage` 11/11 ; `exiger_env_deploiement` (local+clé lève / local nu passe /
  pilot+clé passe) ; contrôles Lot 1 empiriques sur base réelle (concurrence + suppression + sans-compte),
  nettoyés.
- **tsc** : sans objet (aucun fichier TypeScript touché).
- **Non-régression** : la lettre AVEC compte est inchangée (même réf `LZ-AAAA-NNNN`, même clôture
  vérifiable) ; multi-zones / gel / RNU / disclaimers (M147) intouchés.

## Hors périmètre (arbitrage séparé, non traité — rappel M148)

- **Lien signé expirant** pour le partage notaire (patron token Flash) — **fonctionnalité produit**, pas
  un correctif. C'est ce qui permettrait « un lien s'ouvre sans compte » sans rouvrir la route.
- **« Un abonné peut-il attester une parcelle qu'il n'analyse pas »** — **décision produit** (cloison
  d'attestation, aujourd'hui inexistante : `parcels` non cloisonnées).

---

*Push `fix/m149-attestation-cloison`. Vic arbitre le merge — CC ne merge jamais.*
