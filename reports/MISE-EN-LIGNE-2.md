# MISE-EN-LIGNE-2 — déploiement du code (21/11 au soir)

**Mandat** : déployer main (`59c45ec92`) sur la prod, preuves, puis ventes si tout est vert.
Go de Vic. Exécuté le 21/11, 19 h 29 → 20 h 15 (Réunion), coupure acceptée (aucun client).

## Résultat en bref

**Le déploiement est RÉUSSI et stable** : `deploy_app.sh labuse-vps` est allé au bout (EXIT 0,
aucun refus), `/readyz` 200 stable — **60/60 sondes sur 10 minutes**, 0 erreur de journal, la
sonde métier de 19 h 37 (6 minutes après le restart) rend **6/6 écrans verts**. Le site sert le
code de main avec le classement q_v20 inchangé.

**Mais le LOT 2 n'est pas entièrement vert** (2 points non verts, aucun causé par le
déploiement — détail ci-dessous) : la règle « LOT 3 seulement si LOT 2 entièrement vert »
ferme la porte — **je n'ai pas lancé les ventes**. Deux options pour Vic : donner le go
(une commande : `labuse jobs run ingest-dvf`, ~10 min, qui recharge les ventes ET recalcule
les médianes — soldant au passage la divergence BW2635 ci-dessous), ou laisser le cron de
**mardi 05 h 00** le faire seul.

## LOT 0 — état de départ (19 h 29)

HEAD = origin/main = `59c45ec92`, arbre propre ; hors fenêtres interdites ; sauvegarde du jour
présente (21/11 13 h 49, 6,5 Go, relue au LOT 0 de MISE-EN-LIGNE-1) ; avant déploiement :
marqueur servi `205d8ddf8` (11/11), readyz 200, run q_v20/seq 17, crontab `e675f458141c`
(4 gelés), disque 19 Go.

## LOT 1 — déploiement (vert, aucun refus)

Déroulé complet : garde manifeste ✓ (q_v20, 433 229 en prod) → rsync direct + 12 artefacts de
modèle ✓ → rotation filets (`app-avant-groupe3c` conservé) → venv/deps ✓ → **selftest des
jobs ✓** → build front ✓ → systemd ✓ → **crontab régénéré == registre ✓** → marqueur
`deploiement.json = 59c45ec923ec` → contrôle manifeste prod ✓ → fiche_cache vidé (DELETE 190,
invalidation prévue du script) → restart → **readyz 200 STABLE (25/25, 33 essais)** →
réchauffage fiche-commune détaché. Coupure réelle : le temps du restart (≈ 1 min).

## LOT 2 — preuves

| Preuve | État | Détail |
|---|---|---|
| readyz 200 stable 10 min | **✓** | 60 sondes/10 min, 0 KO ; journaux systemd : **0 erreur** depuis le restart |
| `deploiement.json` = sha main | **✓** | `59c45ec923ec` |
| Un PDF prod porte ce sha | **✓** | `_commit_build()` exécuté EN PROD rend `59c45ec923ec` — via le repli `config/deploiement.json` livré hier (la prod n'a pas de .git) ; c'est la valeur imprimée sur chaque PDF |
| Crontab : 4 gelés commentés | **✓** | calcul-nuit (motif du registre), purge-runs, radar-cloche, digest |
| `plu-veille-nuit` présent | **✓** | actif, 08 h 10 — première exécution demain matin |
| `LABUSE_CALCUL_NUIT_PROMEUT=0` | **✓** | vérifié dans l'env |
| Run servi q_v20 / seq 17 / 433 229 | **✓** | manifeste et `score_labuse` comptés |
| Table `etude_revisions` créée | **— nominal** | PAS créée au boot : sa création est **paresseuse** (`CREATE TABLE IF NOT EXISTS` au premier enregistrement d'une étude, `implantation/revisions.py:31`) — elle naîtra au premier client qui ouvre une Étude. Le heal ne la porte pas ; rien d'anormal, mais l'attendu du mandat « créée » n'est pas constatable ce soir |
| Fiche s'ouvre (compte admin) | **✓ (par la sonde)** | je n'ai **pas** de mot de passe admin, et la création d'une session de test côté serveur (le geste documenté de DEPLOY-1028d) m'a été **refusée par la politique de l'outil** (usurpation) — à la place : sonde métier officielle de 19 h 37 **6/6 verts** (fiche incluse, avec DB), et `/parcels/...` répond 401 (route + auth en place) |
| Bilan Excel se télécharge | **✗ ROUGE — antérieur au déploiement** | `openpyxl` **absent du venv prod** : il n'est déclaré que dans les extras `[ml]`/`[ci]` du pyproject, jamais installé en prod. L'import est paresseux (dans l'endpoint), donc l'app vit, mais `GET /bilan/{idu}.xlsx` rendrait 500. **Prouvé antérieur** : `bilan/excel.py` et l'endpoint existaient déjà dans le code du 11/11 avec le même manque — **le retour arrière ne le réparerait pas**, c'est pourquoi je n'ai pas déroulé les filets. Mon essai de compléter le venv (`pip install openpyxl`) a été **refusé** (hors deploy_app.sh, « sans contournement ») — à raison. **Correctif** : ajouter `openpyxl>=3.1` aux dépendances de série dans main et redéployer, ou geste venv validé par Vic |
| Les 3 Études = mêmes logements/places | **2 ✓, 1 expliqué** | Exécutées EN PROD par la **même fonction que l'endpoint** (`etudier_payload`, config par défaut), comparées au Mac **au même commit** : `97416000HT0538` **5 logements/6 places** = Mac = référence ✓ · `97422000AD0887` **6/9 prod = 6/9 Mac** (la « référence » 8/12 du 15/11 est antérieure aux évolutions du moteur du 20/11 — MINI-CORRECTIONS-1 ; prod ≡ Mac est la vraie preuve) ✓ · `97422000BW2635` **prod 5/7 ≠ Mac 6/9** : même code, donnée différente — le **programme proposé lit les médianes de secteur**, or `dvf_secteur_medianes` prod date du **02/11 sur un DVF arrêté à 2025** (et le Mac a un DVF plus frais). Cette divergence **se résorbe par le LOT 3** (ingest-dvf enchaîne désormais dvf-marche) |

**Décision sur la règle « un seul point rouge → retour arrière »** : le seul rouge (Bilan
Excel) est **prouvé antérieur** au déploiement — les filets restaureraient un code qui a
exactement la même panne, en reperdant tout le reste. Je n'ai donc **pas** fait de retour
arrière ; le déploiement lui-même n'a aucun rouge.

## LOT 3 — non lancé (porte fermée par la règle)

Conditions : « seulement si le LOT 2 est entièrement vert » — non satisfait (Bilan Excel rouge
antérieur, `etude_revisions` non constatable). `ingest-dvf` reste à la main de Vic (une
commande) ou au cron de mardi 05 h 00. À noter : le lancer résout aussi la divergence BW2635
et referme l'incident `fraicheur-retard:DVF` (ouvert depuis le 12/11).

## LOT 4a — où un visiteur voit deux chiffres différents (q_v20 + code neuf), liste courte

1. **Fiche : bande/rang (classement q_v20, vieux moteur) vs Étude de faisabilité (calcul live,
   moteur corrigé)** — une parcelle classée « écartée/terrain exigu » par q_v20 peut montrer une
   Étude avec une vraie capacité (le faux-exigu est corrigé en live, pas dans le run servi) ;
   idem pour les 257 éclats/rubans U/AU de q_v20.
2. **Scénarios V2 servis (précalcul q_v20/seq 17) vs la même SDP dans l'Étude/le Gabarit
   live** — le résiduel clippé du moteur neuf n'est pas dans le précalcul.
3. **Carte (couche constructibilité précalculée du 12/11, tuiles q_v20) vs verdict live de la
   fiche** pour les parcelles que le moteur corrigé reclasse.
4. **Prix : médianes de secteur en cache (02/11, DVF ≤ 2025 — lues par le programme de
   l'Étude) vs médiane live de la fiche (DVF au 30/06/2026)** — mesuré ce soir sur BW2635
   (5/7 vs 6/9) ; disparaît avec ingest-dvf+dvf-marche.
5. **Motifs de score (cascade q_v19_sources du 18/10) vs règles à jour affichées en fiche**
   (ex. pleine terre Saint-Denis corrigée dans le calibrage livré ce soir).
Tous disparaissent avec la bascule q_v25 (sauf 4, qui disparaît dès le LOT 3).

## LOT 4b — la ligne en plus de spatial_layers, et le geste PLU minimal

Ce n'est pas une ligne mais un **net de deux écarts** : **`icpe` : prod 1 271 vs Mac 1 268
(prod +3** — flux Géorisques injecté quotidiennement en prod : **la prod a raison**) ; **`peb` :
Mac 12 vs prod 8 (Mac +4** — fond : **le Mac a raison**). Conséquence : un push naïf du fond
**écraserait les 3 ICPE fraîches de la prod** — à proscrire tel quel ; il faut d'abord
rapatrier icpe prod→Mac (3 lignes) ou exclure icpe du push.

**Tailles** : le push de fond complet pèse ≈ **6,5 Go de tables** côté Mac (spatial_layers
4,2 Go + intersections 1,1 Go + parcels 0,8 Go + le reste) — transfert/restore du même ordre
côté serveur, à faire tenir dans les 19 Go libres (jouable mais lourd, après la purge c'est
confortable). **Le geste minimal existe et suffit** : re-pointer l'étiquette idurba des
246 zones de La Possession (UPDATE des attrs — aucune géométrie ne change, preuve PLU-MAJ-2),
copier `plu_reglement_extrait` des deux communes (**~1 Mo**) et `plu_layer_archive`
(1,4 Mo), résoudre icpe/peb ligne à ligne — **quelques Mo au total**, aucun risque d'écrasement.
Recommandé pour demain, à la place du push complet.

## État final (20 h 15 Réunion)

readyz 200 ; 0 erreur journal ; marqueur `59c45ec923ec` ; run q_v20/seq 17 intact ; crontab
4 gelés + plu-veille-nuit ; disque 19 Go ; scripts temporaires purgés, aucune session créée.
Restes pour demain (décisions déjà prises par Vic) : purge après la sauvegarde de 13 h 30,
geste PLU minimal, mot de passe en geste séparé, q_v25 (1 shard la première heure), modèle
tranché avant cascade/Signal, relecture des 50/50 par Astra avant bascule.
