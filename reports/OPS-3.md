# OPS-3 — un banc qui dit la vérité, un Courrier qui lit la fiche, une vérité permanente complète

Mandat Vic, **2026-11-09** (Réunion +04), worktree `~/Desktop/labuse-ops3`, branche `fix/ops-3`, Opus.
Prod via `ssh labuse-vps` (partie C). **Aucune écriture prod 01 h–05 h.** Hook vert, commit, **pas de
merge**. À lire d'abord : `reports/DEPLOY-GROUPE-2.md` (branche `fix/saint-leu-1`), `reports/QV22-1.md`.

---

## ★ VERDICT — en tête

| Lot | Objet | État |
|---|---|---|
| **A** | Le banc de cohérence dit la vérité (non achevé / vérification sautée = échec, nomme le run contrôlé) | ✅ fait + testé |
| **B** | Le Courrier lit la zone par `zone_servie` (comme tous les documents) + fait ajouté au banc | ✅ fait + testé (parcelle de l'incident) |
| **C — code** | Harnais C réécrit au modèle MAILS-1 ; A/B/F s'authentifient (compte de recette) | ✅ fait ; auth prouvée bout-en-bout en local |
| **C — prod** | Création du compte de recette + rejeu `verite-permanente` 6 lots en prod | ⏳ **dans la fenêtre sûre (après 05 h Réunion)** — procédure validée, §C.4 |

**Hook** : `test-unit` **3226 passed / 0 échec**, suite **cohérence 6/0** (0 écart témoins), **scan secrets**
propre. Front non modifié (aucun fichier `frontend/`). **Pas de merge.**

---

## A — Le banc de cohérence dit la vérité

**Mandat** : « Son résultat nomme le run contrôlé. Un passage qui n'est pas allé au bout, ou qui a sauté
une vérification, est un échec, jamais un vert : le résumé, les incidents et les contrôles de promotion
le lisent comme tel. »

**Diagnostic** (avant) : `coherence_runs` ne portait QUE `faux_client` / `erreurs_lecteur`. Un passage
**OOM-killé en cours**, un **banc2 dont une famille d'invariants était indisponible** (import en échec),
ou des **gardes toutes en SKIP** (base/app inatteignable) pouvaient écrire une ligne qui se lisait
**verte** (0 faux-client) — et le gate de promotion / le résumé / John la prenaient pour un vert.
La ligne ne disait pas non plus **quel run** elle avait contrôlé.

**Correctif** — la ligne du banc NOMME le run contrôlé et DÉCLARE si elle est allée au bout :

- `coherence_runs` + `run_servi` (le run que le banc a lu = run servi), `acheve` (bool, défaut `true`),
  `incomplet_motif` (`coherence_journal.py` : DDL + `ALTER … ADD COLUMN IF NOT EXISTS` pour les bases
  déjà créées). `journaliser_passage(... run_servi, acheve, incomplet_motif)` renvoie l'`id` ;
  `marquer_incomplet(db, id, motif)` scelle a posteriori.
- `scripts/coherence/banc.py` — `run()` trace les **phases achevées** (parcelles/communes/croisements/
  déterminisme) et renvoie `acheve` ; un **échantillon vide** (base/app inatteignable) → `acheve=False`
  + motif, jamais un `0/0` vert.
- `scripts/coherence/invariants2/banc2.py` — `executer()` renvoie `indisponibles` (familles dont
  l'**import** a échoué = vérification PRÉVUE qui n'a pas tourné), distinct d'une famille **hors scope**
  (lourde, réservée au `--tout` du dimanche — périmètre annoncé, pas un saut).
- `jobs_impl.coherence_banc` — orchestre banc + chasse + banc2, **agrège l'inachèvement** (balayage non
  achevé / illisible, gardes toutes en SKIP, invariants indisponibles ou non probants) et **persiste la
  ligne HONNÊTE AVANT de lever** : même si une sous-étape plante ensuite, le gate/résumé lisent
  `acheve=false` + motif. Puis `raise` → incident `job-echec:coherence-banc`.
- **Contrôles de promotion** (`autonomie.controler_run`) — un passage **frais mais non achevé** est un
  **échec** (`cohérence-achevée`), plus seulement « 0 faux-client ». `coherence_acheve=None` (vieille
  base non migrée) → ancien comportement (ne bloque pas à tort).
- **Résumé** (`mails_exploit`) — dernière ligne non achevée → point **rouge** « le contrôle de cohérence
  n'est pas allé au bout ». **John** (`john/contexte.controles`) — `vert` exige désormais `acheve` ;
  expose `run_controle`.

**Tests** (`tests/test_ops3_coherence.py`, 6) : gate refuse un banc non achevé (motif remonté), accepte
un banc achevé+vert, garde l'ancien comportement si `acheve` absent, reste rouge sur un écart ;
`banc.run` sur échantillon vide → `acheve=False` ; journal nomme le run + `marquer_incomplet` scelle.

---

## B — Le Courrier lit la zone par le lecteur de la fiche

**Mandat** : l'écart « courrier-zone-bizone » — le Courrier lisait la zone **en direct** (`parcel_zone_plu`)
quand la fiche sert la **dominante** (`zone_servie`). Le Courrier doit lire la zone par le lecteur de la
fiche (`zone_servie`), comme tous les documents.

**Correctif** (`courrier_compose._synthese`) : la zone vient désormais de
`faisabilite.zone_servie.zone_dominante(db, parcel_id)` — **exactement** le lecteur de la fiche, du
Gabarit, du Flash, du Bilan. Le libellé n'est plus qu'une décoration **appariée** à la zone servie
(lue pour la seule zone dominante), jamais une seconde vérité de zone.

**Vérification « aucun autre document ne lit la zone en direct »** : confirmé — les autres documents
lisent la zone via le payload fiche (`verdicts.zone_libelle`) ou appellent `zone_dominante`
directement ; **seul** le Courrier faisait une lecture SQL brute. (Les autres lectures de
`parcel_zone_plu` restantes sont des filtres/jointures de liste/carte et des modules de vérité-terrain,
pas la zone d'un document client.)

**Fait ajouté au banc des documents** (`scripts/coherence/documents.py` → `courrier_zone`) : pour chaque
témoin (dont la bizone de l'incident `97415000BZ0005`), la zone servie par le **Courrier composé**
(`/courrier/composer` → `synthese.zone`) doit être **égale** à la zone servie par la fiche
(`reglement_plu.zones[0].zone`). La garde `chasse_donnees.g06_courrier_zone` est **réécrite** pour
interroger le VRAI courrier (plus le proxy SQL brut, désormais obsolète).

**Test sur la parcelle de l'incident** (`tests/test_ops3_courrier_zone.py`) : BZ0005 est **à cheval**
(dominante « A », aucune zone ≥ 90 %) ; vérifié que `courrier.zone == zone_dominante.zone == « A »`.
Test unitaire (sans base) : `_synthese` prend bien sa zone de `zone_dominante` (sentinelle), pas d'une
lecture brute. Test `local` (base réelle) sur l'incident pour le banc de nuit. *(Sur la base q_v20,
`parcel_zone_plu` est 1 ligne/idu : Courrier et fiche concordaient déjà — le correctif supprime la
POSSIBILITÉ de divergence sur toute base où la table est incomplète/périmée ou la parcelle à cheval.)*

---

## C — Vérité permanente : A/B/F s'authentifient, lot C réécrit (MAILS-1)

**Mandat** : « Pas d'instance sans authentification. » Les lots A/B/F s'authentifient sur la prod avec un
compte de recette dédié `victorlaganepro+recette@gmail.com`, plan intégral, créé s'il n'existe pas ; mot
de passe dans `/etc/labuse/labuse.env`, jamais commité ; lecture seule. Lot C : réécrire le harnais au
modèle MAILS-1. Rejouer `verite-permanente` en prod, verdict des six lots.

### C.1 — Lot C réécrit au modèle MAILS-1 (`docs/audit-2026-11/nu-5/C/harnais_mails.py`)

L'ancien harnais appelait des fonctions **supprimées** (`emails.reset_password`, `digest_notifications`,
`annonce_email`, `maintenance_email`, `mise_en_vente_email`) et dépendait de **templates Brevo** qui 404 —
il échouait par construction (C rouge « harnais périmé », cf. DEPLOY-GROUPE-2 §A4). Réécrit : les **21
mails** (`mails_contenu.ORDRE_CATALOGUE` + `essai_fin_proche`) sont **rendus par l'app**
(`mails_contenu.rendre(clé, SPECIMENS[clé])` → gabarit unique), **Brevo = simple transport**. Contrôles
DURS : **expéditeur unique** (`settings.mail_from`), **liens** tous https + labuse.immo, **désinscription**
présente partout SAUF sécurité + transactionnels (abonnement/accès/maintenance), **0 `{{param}}`
non substitué**, **0 « None »**, **bouton** présent (sauf maintenance). **Résultat local : 21 mails,
expéditeur unique `LABUSE <contact@labuse.immo>`, 0 écart dur, rc=0.** Le skip « Brevo non configuré »
est retiré : le rendu est EN-PROCESS, sans prérequis réseau.

### C.2 — A/B/F s'authentifient (compte de recette, session partagée)

« Pas d'instance sans auth » : au lieu d'une instance auth-off (refus de sécurité, DEPLOY-GROUPE-2 §A4),
le runner `verite_permanente` **se connecte une fois** au compte de recette (`POST /login`), récupère le
cookie `labuse_session` et le **partage** aux lots A/B/F via `LABUSE_HARNAIS_COOKIE` :

- `scripts/verite_permanente.py` — `_cookie_recette(base)` (lecture seule : un `POST /login`, 303 sans
  suivre la redirection, cookie lu dans le jar). Identifiant fixe, mot de passe depuis
  `LABUSE_RECETTE_PASSWORD` (env, jamais commité). **Instance présente mais login en échec = ROUGE**
  (pas un saut : « pas d'instance sans authentification »). Pose aussi `NU5_BASE` (lot B) et
  `LABUSE_SOCLE` (lot F).
- Lot A (`A/harnais/harness.py`) et lot B (`B/harnais/harnais.py`) — header `Cookie` sur chaque requête.
- Lot F (`F/harness/audit_a11y.mjs`) — `context.addCookies(labuse_session)` sur chaque contexte (le
  front `/socle/` rend l'app au lieu de rediriger vers `/login`).

**Compte de recette** (`scripts/ops3_creer_recette.py`, idempotent) : compte **non administrateur** (un
vrai client), **plan intégral**, **statut actif**, rôle titulaire ; créé s'il n'existe pas, sinon remis au
vert + (ré)installe le mot de passe. Le mot de passe vient de `--password` / `LABUSE_RECETTE_PASSWORD`,
**jamais en clair dans le dépôt**.

### C.3 — Validation BOUT-EN-BOUT en local (de-risque le run prod)

En local (base q_v20, `TestClient` en-process, auth activée) : création du compte de recette (plan
intégral, actif) → `POST /login` **303 + cookie `labuse_session`** → endpoint protégé `/parcels/{idu}`
**200** avec le cookie. **Le chemin d'authentification A/B/F fonctionne de bout en bout.** Lot C :
**rc=0, 0 écart** (cf. C.1). Lots D/E : verts en local (SQL lecture seule).

### C.4 — Rejeu `verite-permanente` en prod — DANS LA FENÊTRE SÛRE (après 05 h Réunion)

Au démarrage du mandat il était **01 h 2x Réunion** — à l'intérieur de la fenêtre **01 h–05 h** où
**aucune écriture prod** n'est permise. La création du compte de recette (écriture base) et l'ajout du
mot de passe à `/etc/labuse/labuse.env` (écriture prod) sont donc **reportées après 05 h**. Procédure
(prod déployée `/opt/labuse/app`, venv `/opt/labuse/venv`, app `127.0.0.1:8000`, user `labuse` ;
constatés en lecture seule — node + chromium-1254 présents, `LABUSE_CHROMIUM` posé ; compte de recette
**absent**) :

1. Générer un mot de passe fort → `LABUSE_RECETTE_EMAIL` + `LABUSE_RECETTE_PASSWORD` dans
   `/etc/labuse/labuse.env` (0600, **jamais commité**).
2. `scripts/ops3_creer_recette.py` avec le venv prod → compte de recette (plan intégral, actif).
3. Stager (scratch, hors tree servi) le runner + les 5 harnais + `A/preuves/choix.json` + `npm install`
   dans `F/harness` (axe-core/playwright ; `package.json`/`node_modules` non déployés).
4. `LABUSE_HARNAIS_BASE=http://127.0.0.1:8000` + env prod (DB, Brevo, Chromium) → `verite-permanente`.
5. Verdict des **six lots** (consigné ci-dessous au retour dans la fenêtre sûre).

> **Verdict prod des 6 lots** : _à compléter après 05 h Réunion._

---

## Périmètre & preuves

- **Écritures prod prévues (dans le mandat, après 05 h)** : (a) compte de recette (base) ; (b)
  `LABUSE_RECETTE_*` dans `/etc/labuse/labuse.env` (non commité). **Tout le reste lecture seule.**
- **Aucune écriture prod 01 h–05 h** : seules des lectures ont eu lieu dans la fenêtre (état prod, temps,
  présence du compte, node/chromium).
- **Branche `fix/ops-3`** : A (banc vrai) · B (Courrier zone_servie + banc documents) · C (harnais C
  MAILS-1 + auth A/B/F + `ops3_creer_recette`). **Hook vert, aucun merge, aucun déploiement.**
- **Tests** : `test_ops3_coherence.py` (6), `test_ops3_courrier_zone.py` (2 unit + 1 local),
  `test_mails_1_gabarit.py` (catalogue 21 mails) verts ; `test-unit` **3226/0**, cohérence **6/0**.
- **Réserves honnêtes** : (1) le verdict LIVE prod des 6 lots est produit après 05 h (fenêtre) — le
  chemin d'auth est prouvé bout-en-bout en local. (2) A/B/F exigent, en prod, `A/preuves/choix.json`
  (lot A) et `npm install` (lot F) non déployés — stagés pour le rejeu ; à embarquer au déploiement pour
  que `verite-permanente` soit vert durablement (hors mandat « config »).
