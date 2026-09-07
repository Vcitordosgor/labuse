# DASHBOARD-2 — Lot 2 (raccord Comptes/mail_queue, après merge de COMPTE-2)

`feat/dashboard-2` **rebasée sur `origin/main`** (COMPTE-2 mergé). Un seul conflit de rebase,
complémentaire, dans `dashboard.py` (les colonnes de contexte « Signaler » de COMPTE-2 + le
`compte_plan` de mon Lot 5) — résolu en gardant les deux. **Rail et CSS partagée : intacts**
(AdminView.tsx et les fichiers CSS n'étaient pas dans la surface de conflit ; vérifié : LEDs
Horloge/Verrous, compteurs de nav, `.cxp`, build vert).

Vérifié sur la base réelle `labuse` (uvicorn + Vite, `#admin=1`).

## 1. Jauge Clients → « à toucher »

**Changé** : la jauge affiche le **« à toucher »** (clients hors test ayant une action en attente),
plus le nombre de licences. Elle lit le **même endpoint** (`/admin/licences`) et la **même fonction**
(`prochaineAction`, exportée de la page Comptes de COMPTE-2) que le **segment par défaut « À toucher »**
de la page — donc le même nombre. Le clic ouvre la page Comptes, qui s'ouvre par défaut sur ce segment.

**Preuve** : jauge `18 · Clients · à toucher · 2 actives` ; clic → page **Comptes**, segment
**« À toucher » (18)** actif. Le nombre de licences (2) reste sur le rail, la page et l'Argent.

## 2. Jauge Système → + échecs mail_queue du jour

**Changé** : la jauge Système compte toujours les lignes rouges de « À faire », et **y ajoute les
échecs d'envoi du jour** lus dans `mail_queue` via `mailfile.echecs_du_jour` (fonction déjà fournie
par COMPTE-2, dont la docstring dit « jauge Pilotage » — une seule source). Un échec du jour ajoute
une ligne rouge « Rejouer N échec(s) d'envoi de mail » → Comptes ; **zéro échec = rien de plus**.

**Preuve** : `/admin/pilotage.mail_echecs_jour = 0` en local → Système = `2` (2 lignes rouges :
horloges + sauvegarde), rien d'ajouté. La ligne rouge et le décompte partagent la même source.

## 3. Compteur de licences — une fonction, trois lectures

**Constat** : COMPTE-2 a livré `comptes.licences_actives` (LE compteur unique : actif, hors essai,
hors interne/test) et l'a **déjà branché au Pilotage, au rail ET à la page Comptes**
(`admin_licences` sert `compteurs.licences_actives`). C'est cette fonction — mieux définie que le
`comptes_actifs` que j'avais modifié en attendant — qui est la source unique.

**Fait** : j'ai **restauré `plateforme.comptes_actifs`** à son sens d'origine (compteur métier
« comptes au statut actif », registre/témoin) que ma recette avait modifié en attendant COMPTE-2 —
sinon il aurait cassé la garde `comptes_actifs inchangé` de COMPTE-2. La jauge/rail/Argent lisent
`data.licences_actives` (= `comptes.licences_actives`).

**Preuve** : `/admin/pilotage.licences_actives = 2` **==** `/admin/licences.compteurs.licences_actives
= 2` **==** `comptes.licences_actives()`. Une fonction, trois lectures (test
`test_dashboard2_cloture::test_clients_le_meme_9`).

## Qualité

`tsc -b` 0 · `vitest` 191 · `vite build` OK. Backend : `test_dashboard2_cloture` (7), COMPTE-2
`test_compte2_comptes` + `test_compte2_mailfile`, `test_comptes_actifs` (témoin restauré),
`test_dashboard` 22/1 (1 échec pré-existant `test_ia_log_attribue_au_compte`, FK de seed, confirmé
sans rapport). Rien d'autre touché que le Lot 2 (+ résolution de rebase). Rail/CSS non modifiés.
