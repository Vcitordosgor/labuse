# MISE-EN-LIGNE-5 — préparer le serveur pour le classement (dim 22/11)

**Exécuté** dimanche 22/11, 09 h 27 → 10 h 50 Réunion (fenêtre ouverte, hors 13 h 30-14 h).
Un lot après l'autre. **ARRÊT au LOT 3** sur une preuve rouge (détail § LOT 3) — **le LOT 4
(mot de passe) n'a PAS été entamé**.

## LOT 1 — sauvegarde fraîche : VERT

`labuse jobs run backup-postgres` (le job habituel) — **ok en 18 min**. Dump
`labuse-labuse-20261122-092713.dump`, **6,2 Go**, **relu** (`pg_restore --list` : 1 849 lignes
TOC, **308 tables**). Place restante : **25 Go (74 %)** — suffisante.

## LOT 2 — purge des runs morts : DÉJÀ FAITE (no-op prouvé)

Revérifié aujourd'hui contre l'état réel : **aucun label de la liste figée MENAGE-PROD-1 §A
n'existe plus** (q_v11_m137, q_v13_sources1, q_v16, q_v21, q_v22, q_v24, seq 1/2/13 : 0 ligne
partout). La purge a eu lieu lors de MENAGE-PROD-1 (commit `6559b1fd4`). Ce qui subsiste : les
gardés (q_v20 servi, q_v19_sources, q_v18/seq 15, seq 17, q_v18_sources) **et q_v23** (hors
liste §A — intouché). **Rien à supprimer** : je n'ai pas exécuté de transaction vide. Manifeste
et gardés intacts.

## LOT 3 — PLU, geste minimal : APPLIQUÉ, mais preuve finale ROUGE (hors périmètre)

**Correction en cours de route (décision Vic, intégrée au script)** : le volet **peb a été
retiré**. L'écart « peb Mac 12 / prod 8 » n'était pas 4 manquants en prod mais **4 doublons côté
Mac** — les 4 zones Roland Garros A/B/C/D existent déjà en prod (une chacune) ; le Mac les a en
double. La prod fait foi ; pousser aurait dédoublé. (Cela corrige mon analyse erronée de
MISE-EN-LIGNE-2.)

**Appliqué en une transaction** (sauvegarde des lignes touchées d'abord, contrôles d'entrée ET
de sortie, empreintes géométriques zones+prescriptions vérifiées identiques Mac=prod le jour
même) :
- étiquette idurba : 97408 zones 246 + prescriptions 86 → `97408_PLU_20260625` ; 97411
  prescriptions 2 908 → `97411_PLU_20260805` (UPDATE 332 + 2 908, géométries intouchées) ;
- règlements des 2 communes = miroir Mac (397 → 553 ; l'ancien texte 97408 conservé = archive) ;
- table `plu_layer_archive` créée + 332 lignes ;
- ICPE **intouchées** (contrôle 1 271 dans la transaction) ; peb **intouchés** (contrôle 8).

**Preuves** :
1. ✅ la prod sert **`97408_PLU_20260625`** (zonage) et **`97411_PLU_20260805`** (règlement 241 +
   zones 259 + prescriptions 2 908) ;
3. ✅ empreinte parcelle→zone **inchangée** (97408 `e0ebb7f9…`, 97411 `b347cf4e…` = avant) ;
2. ⚠️ **`plu-veille-nuit` (lancé à la main, ok 56 s) : 21 communes à jour, mais 2 désynchronisées
   — Bras-Panon et Saint-Joseph.** Saint-Denis et La Possession sont bien **résolus**
   (`incidents_resolus: 2`). Les 2 restants **ne viennent pas de mon geste** : leur zonage servi
   en prod **= le Mac** (Bras-Panon `20260428`, Saint-Joseph `20251210`) — ce sont **2 nouveaux
   retards détectés par la sonde** (le GPU a publié plus récent que ce que le Mac *et* la prod
   servent). Les corriger suppose une ré-ingestion GPU sur le Mac — **hors de ce mandat**.

La preuve 2 étant formulée « aucun écart sur les 24 communes », elle est **rouge** → **ARRÊT**
(le LOT 4 touche l'authentification de toute la prod ; je ne l'entame pas sur un LOT 3 dont une
preuve n'est pas verte). Mon geste PLU est, lui, un **succès** (Saint-Denis + La Possession à
jour, zéro parcelle déplacée).

**Retour arrière du LOT 3** si besoin : lignes d'avant dans
`/var/backups/labuse/ml5-plu-20261122/` (reglement_avant, etiquettes_avant, peb_avant).

## LOT 4 — mot de passe : NON ENTAMÉ (arrêt au LOT 3)

## État final (10 h 50)

readyz 200 · run q_v20 / seq 17 intacts · disque 25 Go · temporaires purgés (sauvegarde LOT 3
conservée). **Décision pour Vic** : les 2 desync Bras-Panon/Saint-Joseph sont des retards GPU
préexistants hors périmètre — si tu les juges sans objet pour ce mandat, dis-le et j'enchaîne
sur le LOT 4 (mot de passe) ; sinon ils feront un geste PLU à part (ré-ingestion GPU côté Mac
puis même script).
