# RAPPORT — RETOURS VISUELS 2 (après le déploiement)

Branche `fix/retours-visuels-2` (base `f1e73834`). Corrections après vérification de Vic en production
(deploy 28/08, commit 7eea236b). Captures : `docs/audit-2026-08/RETOURS-VISUELS/captures/rv2-*`.

## V1 — 🔴 Le dépôt de capture échouait en production
**Demandé** : diagnostic (chemin, existence VPS, utilisateur, droits) ; chemin configurable hors app ;
créer le répertoire s'il manque, message qui NOMME le chemin fautif ; vérif au démarrage + alerte
admin ; procédure serveur pour Vic ; lister les autres écritures disque (finding).
**Diagnostic** : chemin par défaut `/srv/labuse/pige/captures` (déjà **hors** `/opt/labuse/app`, donc un
deploy ne l'efface pas), configurable par `LABUSE_PIGE_CAPTURES_DIR`. Le code fait déjà `mkdir -p` — la
cause est les **droits** : l'utilisateur `labuse` (systemd `User=labuse`) ne peut pas créer sous `/srv`
(parent appartenant à root). D'où l'échec `OSError` → refus propre (RD-501, rien de faux en base) mais
Radar inutilisable, et un message générique.
**Traité** (front + back seulement) :
- `captures_dir_writable()` (tables.py) — tente `mkdir -p` + un témoin d'écriture, retourne `(ok, detail)`
  où `detail` NOMME toujours le chemin. Ne lève jamais.
- Message d'échec du dépôt (intake.py) NOMME le chemin fautif.
- Vérif AU DÉMARRAGE (lifespan) : `log.error` BRUYANT si non écrivable (pas un crash), état exposé.
- `radar_check` expose `captures_dir_ok` + `captures_dir` ; l'écran admin affiche un **bandeau rouge**
  « Dépôt de captures indisponible » avec le chemin, AVANT le premier dépôt.
- `docs/EXPLOITATION.md § captures` : procédure serveur exacte (mkdir, chown labuse, chmod 700, test
  d'écriture, restart).
- Test `test_pige_captures_dir.py` (3) : ok accessible / ko nomme le chemin / hors répertoire applicatif.
**Prouvé en vif** : répertoire OK → `radar_check.captures_dir_ok=true`, pas de bandeau ; répertoire
inaccessible → `log.error` bruyant nommant le chemin + bandeau admin (`rv2-v1-admin-captures-{ok,defaut}`).
**Procédure serveur pour Vic** (root, dans l'ordre) :
```bash
sudo mkdir -p /srv/labuse/pige/captures
sudo chown -R labuse:labuse /srv/labuse
sudo chmod -R 700 /srv/labuse
sudo -u labuse bash -c 'touch /srv/labuse/pige/captures/.probe && echo ok && rm /srv/labuse/pige/captures/.probe'
sudo systemctl restart labuse
```
Après ça, le bandeau disparaît et le dépôt aboutit. (Le dépôt COMPLET valide ensuite l'extraction par la
vision IA — testable sur le VPS avec la clé LIVE ; le STOCKAGE, lui, est prouvé.)
**Finding RV2-001 — mêmes familles d'écriture disque** (répertoire hors app + droits), NON corrigées :
(1) `backup_dir` `/var/backups/labuse` (pg_dump ; le deploy en dépend) ; (2) `flash/report.py` +
`flash/carte.py` (PDF + cache du rapport Flash public servi aux clients) ; (3) exports CLI. Les jobs
d'ingestion créent leurs dossiers (cron admin, hors chemin client).

## V2 — Taxe d'aménagement : vérité et utilité
**Demandé** : re-vérifier chaque valeur 2026 DOM ; exonérations manquantes ; taux communal (open data ?
sinon aide) ; 3-5 cas de test figés ; rester une estimation indicative.
**Re-vérifié** (28/08 contre service-public A15416) : toutes les valeurs 2026 sont EXACTES (892/1011 €/m²,
piscine 251, PV sol 10, éolienne 3000, stationnement 2928/5857, abattement 50 % 100 m² RP + logements
aidés, exonération < 5 m², communal 1-5 %, départemental 2,5 %).
**Corrections de fond** :
- **Base légale corrigée** : le YAML citait le code de l'urbanisme (L.331-*, ABROGÉ) ; la TA est au
  **CGI art. 1635 quater A à V** depuis la réforme 2022. Références précises dans le YAML, servies à
  l'écran (source + note).
- **DOM/Réunion** : la valeur forfaitaire hors-IdF s'applique (aucune valeur DOM spécifique) — dit à l'écran.
- **Exonération < 5 m² AJOUTÉE** (CGI 1635 quater D) : surface taxable < 5 m² → part surface exonérée
  (ligne explicite, jamais un zéro muet).
- **Taux communal** : pas de source open data exploitable par commune (recherche data.gouv : aucun
  dataset ; les taux viennent des délibérations). Saisie manuelle conservée + **aide concrète** (où
  trouver le taux : délibération du conseil municipal, service urbanisme, avant le 1er juillet ; défaut
  légal min 1 %).
- **5 cas réels** calculés à la main et figés (`test_taxe_cas_reels.py`) : maison simple (3 434,20 €),
  maison + piscine + stationnement (7 693,95 €), logement aidé (2 319,20 €), projet sous seuil (0 €),
  taux communal manquant (pas de total). 11 tests taxe verts.
**Finding RV2-002 — exonérations NON ajoutées** (nuancées) : locaux agricoles (le logement de
l'exploitant reste taxable), reconstruction à l'identique après sinistre (conditionnel), service
public/intérêt général (hors promoteur privé). À traiter avec des entrées UI dédiées si Vic le souhaite.

## V3 — Veille : même patron que Radar
**Demandé** : Veille plein écran à GAUCHE (patron Radar), deux portes ; Foncier → Parcelles avec barre
IDU+adresse ; retirer « Secteur » (sans détruire les données) ; Critères = filtres de base de la
recherche ; retirer l'IA ; prouver que les alertes partent vers l'e-mail du compte.
**Traité** :
- La Veille devient une CATÉGORIE plein écran (`view: 'veille'`, panneau 434px + carte), plus un overlay
  à droite. Deux portes (Le foncier / Les annonces) conservées. Store, App, Rail adaptés ; les
  consommateurs (notifs, copilote) restent fonctionnels (mêmes actions, redirigées vers `view:'veille'`).
- **Parcelles** : barre **IDU + adresse** (`ParcelInput` partagé, comme Étudier un bien) → `toggleWatch`
  (suivi cloisonné au compte, plafond 50) + liste des suivis + « retirer ».
- **« Secteur » retiré** (l'outil secteur n'existe plus). Données CONSERVÉES : aucune veille de type
  'secteur' dans `veilles` (types présents : permis, bodacc) ; **3 `watch_zones`** en base locale
  conservées, back `createWatchZone`/`getWatchZones` intact — **finding RV2-004** (rien détruit).
- **Critères** : les MÊMES filtres que la carte (composant `FiltreLabuse` réutilisé — pas un jeu réduit) :
  communes, surface min/max, zonage (familles U/AU/A/N + zones exactes), état du sol, signaux de vie, +
  l'interrupteur d'analyse LABUSE ; son bouton « Créer une veille » enregistre la recherche (saveSearch).
  Liste des critères enregistrés + suppression.
- **IA retirée** de la création de veille : l'entrée de traduction en langage naturel (`veilleNL`) ne
  s'affiche plus ; le back `/events/veille-nl` reste (décision Vic).
- **VÉRIFICATION e-mail — PROUVÉE (vert)** : les alertes partent vers l'e-mail du COMPTE (la licence).
  Chemin : `digests._clients_actifs` sélectionne `min(u.email) FILTER (WHERE u.role='titulaire')` de
  `utilisateurs` (JOIN `comptes`, `WHERE c.statut='actif'`) → `_envoyer` → `brevo.envoyer_template(email,…)`.
  Aucune adresse en dur/config. Test `test_alerte_veille_part_vers_email_du_compte` : capture le
  destinataire réel et vérifie qu'il est l'e-mail titulaire d'un compte actif (5 tests digests verts).
Captures : `rv2-v3-veille-{avant,portes-apres,foncier-apres,criteres-apres}-d` + `-m`.

## V4 — Radar : le sélecteur de tri
**Demandé** : aligner le sélecteur « Plus récentes » (blanc, hors DA) sur les autres contrôles ; vérifier
les autres `<select>`.
**Traité** : le select de tri du Radar reçoit `bg-surface-1 text-txt focus:border-mint` (fond sombre,
bordure, texte) — il était le seul sans `bg-surface`. **Finding RV2-003** : les autres `<select>` de
l'app (moteurs, Communes, ModulePanel/CommuneScope, Sources, Kanban, ProspectionSolaire) ont TOUS déjà
un fond (`bg-surface-2/3` ou `bg-bg`) ; aucun autre ne souffrait du défaut. Captures :
`rv2-v4-radar-tri-{avant,apres}-d`.

## V5 — Recette
- Dépôt de capture : répertoire OK → `radar_check.captures_dir_ok=true`, pas de bandeau ; inaccessible →
  alerte bruyante + bandeau admin (prouvé) + procédure serveur écrite. Le stockage aboutit ; l'extraction
  IA du dépôt complet est testable sur le VPS (clé LIVE) après la procédure.
- Taxe : 5 cas calculés main, figés (verts).
- Veille : plein écran gauche, deux portes, barre IDU+adresse, critères étendus, sans Secteur ni IA
  (captures).
- E-mail de veille = e-mail du compte : test vert.
- Sélecteur de tri conforme (avant/après).
- Données de test purgées — vérifié SQL : 0 pige_biens ≥ 900000, 0 compte RT, 0 veille radar sans compte,
  0 utilisateur @rt.test, 0 saved_search orpheline.

## Gardes
- tsc 0 · build OK · tests store 9/9 · mes 9 nouveaux tests verts (captures_dir 3, taxe cas 5,
  e-mail veille 1).
- **Suite pytest : branche 1939 passed / 4 failed** ; base (worktree `f1e73834`) 1927 passed / 4 failed.
  **Au niveau de la base** — les 4 échecs sont PRÉ-EXISTANTS et IDENTIQUES sur la base (vérifié en
  worktree) : `test_pige_digests::test_echec_envoi_bruyant` et
  `test_notifications_m85::test_producteur_systeme_dit_sa_source_et_son_lien` (environnement local :
  la config Brevo/notifications de la base de dev fait diverger l'attendu). Aucune régression : les +12
  passed de la branche sont mes nouveaux tests.
- Golden inchangé (aucun fichier de scoring touché).
