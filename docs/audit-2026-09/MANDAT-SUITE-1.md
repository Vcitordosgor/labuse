# MANDAT SUITE-1 — retours ADMIN-1 + tout ce qu'on avait remis à plus tard

**Branche : `feat/suite-1`** (depuis `main` après merge de `feat/admin-1`). Bloc commun habituel.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

Le mandat est long ; les lots sont **indépendants** et ordonnés du plus petit au plus lourd. Si la session s'épuise, commiter ce qui est terminé et rendre le compte-rendu des lots faits — le reste part en Partie B. **S9 est le seul lot lourd** ; il se fait en dernier.

---

## S0 — Retours immédiats sur ADMIN-1

**S0.1 · IA, les unités (encore).** « 0,56 € » et « 0,79 centime » côte à côte, Vic lit 56 centimes et 79 centimes — la fraction de centime est illisible. On arrête de parler en centimes :
- carte 1 : **« 0,56 € »** — conso du mois · 71 appels ;
- carte 2 : **« 7,90 € pour 1 000 questions »**, sous-titre « ≈ 0,008 € l'une » — c'est le chiffre qui parle.
Aucune décimale de centime nulle part sur la page. Le même format s'applique à la colonne « coût 30 j » de la table des plafonds.

**S0.2 · Contacts, un seul bouton.** Le bouton « + Ajouter un contact » répété sur chaque carte de commune est laid. Un **seul** bouton en haut à droite de la page, dont le formulaire commence par le choix de la commune (recherche). Sur une carte, seulement un « + » discret dans le pied de carte, visible au survol (desktop) ou toujours sur mobile. Les communes qui ont des contacts nommés remontent en premier ; les autres restent en dessous, plus compactes (une ligne).

## S1 — Programme → Scan patrimoine

Décision Vic : la page « Programme » disparaît du menu, sa collecte se replie dans Scan.

1. Dans Scan patrimoine, **propriétaire choisi** → l'onglet « Ce qu'ils construisent » gagne, sous l'en-tête, un geste admin discret « Collecter ses programmes depuis son site » (visible admin seulement) qui ouvre la collecte existante (coller l'URL → extraction IA → validation ligne à ligne → rattachement), **préremplie avec le SIREN courant**. Aucune réécriture de `promo.py`.
2. Les programmes déjà collectés d'un propriétaire s'affichent dans ce même onglet, sous ses opérations (« Programmes publiés sur leur site (N) »), avec le lien de rattachement à l'opération quand il existe.
3. L'entrée de menu « Programme » est retirée ; l'ancienne URL redirige vers Scan. Les routes `/admin/programmes/*` restent.
4. Le compteur de l'onglet devient réel : « Ce qu'ils construisent (14) », pas générique.

## S2 — « Relancer l'ingestion », rendu intuitif

Constat ADMIN-1 : Relancer et Injecter lancent la même commande (retélécharger ce que la source publie aujourd'hui) ; seule la trace diffère. Résultat : cliquer Relancer sur DVF chargerait 2026-S1 sans passer par la trace de nouvelle version.

1. **Un seul bouton par état**, jamais deux qui font pareil :
   - nouvelle version détectée → **« Injecter 2026-S1 »** (X6, tracé) ; le bouton Relancer n'apparaît pas ;
   - pas de nouvelle version → **« Recharger »** avec confirmation qui dit exactement ce qui va se passer : « Retélécharge DVF depuis la source et recharge la base. Version attendue : 2025-S2 (identique à celle servie). ~N min. »
   - si la sonde n'a pas tourné depuis > 48 h, Recharger lance d'abord une vérification et bascule sur Injecter si une version plus récente apparaît.
2. **Une seule trace** : tout lancement manuel d'ingestion, quel que soit le bouton, écrit `injection_lancee_at` + qui + version constatée après chargement. Le journal est visible dans la ligne (dernier chargement manuel : date, résultat).
3. Infobulles réécrites en conséquence, pied « Qui fait quoi » mis à jour.

## S2 bis — Données › Catalogue : reconstruire selon la maquette, pas empiler

Constat Vic (captures du 02/09) : le Catalogue est l'ancienne table Sources (millésime amont · ingéré le · cadence · état · deux boutons par ligne) avec, **en dessous**, l'ancien panneau « Cron nocturne » et l'ancienne table « Agent de veille des sources » — trois blocs empilés, la même source apparaît deux fois. C'est flou, et ce n'est pas la maquette.

1. **Une seule table**, celle de `maquette-admin-donnees.html` : source (nom + fournisseur + méthode de veille en petit) · **servi** (millésime en base) · **amont** (ce que l'agent a vu, badge) · dernier passage · fraîcheur · **alimente** · actions. Chaque source **une fois**. Le panneau « Agent de veille des sources » séparé disparaît : ses colonnes sont dans la ligne.
2. **Nouvelle colonne « Alimente »** : les moteurs et surfaces que la source nourrit, en chips courtes (DVF → `sector_price` · scoring · fiche · exports · Radar), lues depuis la matrice réelle de `flux.py` — jamais écrites à la main. Une source sans consommateur affiche « non câblée ». Un clic ouvre l'onglet Circuit avec la source surlignée.
3. **Une action principale par ligne, le reste dans un menu « ⋯ »** : Injecter (si nouvelle version) ou Recharger (S2) en bouton ; Vérifier · cadence · suspendre la veille · désactiver la source dans le menu. Fini les deux boutons empilés.
4. « Cron nocturne » et « Dernières exécutions » vont dans l'onglet **Horloge** uniquement. Le Catalogue ne montre pas de jobs.
5. Groupement par fournisseur avec en-têtes repliables, chips de filtre en tête (toutes · nouvelle version · en erreur · rappels · non surveillées), recherche.
6. Vérifier que l'onglet **Circuit** montre la page Flux complète (bandeau, fourmilière, compteur Radar, garde), telle que validée.

Ce lot ne réutilise pas `SourcesSection` : il la remplace. Les endpoints ne changent pas.

## S3 — La bascule à chaud

Constat FLUX-1 : `Q_A_RUN_LABEL` est lu à l'import → une bascule n'est effective qu'au redémarrage du serveur. C'est le contraire de ce que le bouton promet.

1. Le run courant devient une **fonction** relue à la requête (`runs.current()`, mise en cache quelques secondes), plus une constante d'import. Tous les lecteurs de `Q_A_RUN_LABEL` passent par elle — `grep` exhaustif au compte-rendu.
2. La bascule prend effet **immédiatement**, sans redémarrage, et la garde de cohérence lancée juste après le prouve. Test : basculer sur une base de test → la requête suivante lit le nouveau run.
3. Même traitement pour les autres constantes « lues à l'import » qui bloquent une prise d'effet à chaud, si CC en trouve (les nommer).

## S4 — Sentinelle : deux petits restes

1. **Notification par mail optionnelle, par source** : case « m'alerter aussi par mail » sur une ligne de veille (défaut : off). Utile pour DVF et PPR. Passe par la façade `mail.py` unique.
2. **Second canari** : les 5 sondes `temoin` (PPR, cavités, mouvements, sites pollués, catalogue Région) n'interrogent que Saint-Denis. Ajouter une seconde commune témoin (Saint-Pierre) : une alerte si l'un des deux change. Appels toujours légers et espacés.

## S5 — Rattachement des annonces Radar : le goulot des paires

Constat FLUX-1 : 7 annonces rattachées sur 108 → 0 paire annonce ↔ vente. Sans rattachement, l'estimateur ne s'affinera jamais.

1. **Rattachement automatique proposé** à l'extraction : quand l'annonce porte une adresse, le géocodeur BAN unique (`geocode_ban`) propose l'IDU ; quand elle porte une surface de terrain + commune, proposer les parcelles candidates (même commune, surface ±10 %). La proposition s'affiche dans la file d'extraction avec un clic « rattacher » — **jamais automatique sans validation**.
2. Dans la re-vérification, une chip « non rattachée » et un tri « à rattacher d'abord ».
3. Un compteur sur la page Données › Circuit et sur Pilotage : « annonces rattachées N / M » — c'est le chiffre à faire monter avant les paires.
4. Compte-rendu : sur les 108 annonces existantes, combien la proposition automatique sait rattacher avec confiance (adresse BAN exacte), combien avec candidats, combien pas du tout.

## S6 — Les deux tests rouges pré-existants

`test_pige_socle` (import `requests`/`httpx` dans le one-shot pige) et `test_zone_donnees` (jointure SIRENE). Ils masquent de vrais échecs depuis des semaines. Les réparer ou, si le test teste quelque chose qui n'existe plus, le retirer avec justification. **La suite doit être 100 % verte** à la clôture, et le dire.

## S7 — Hygiène : code mort et obsolètes

Liste accumulée depuis CONNEXIONS-2 (V3.3, Z11, lots 6-9) : `cascade_results` LIVE, `parcel_evaluations.status`, constantes `q_v8_calibre` (`lignee_tete`/`bascule_gardes` inertes), `courrier_envois`, `copilote_v2_missions_jour`, table `veilles`, `_parse_hash_filters`, `SOURCES_MASQUEES`, `csvExportUrl` + `/parcels/export.csv`, endpoints Copilote v1 après S9.

1. **Code et endpoints sans appelant** : supprimés, avec `grep` prouvant l'absence d'appelant au compte-rendu.
2. **Tables obsolètes** : **pas de DROP**. Renommées `_obsolete_<nom>` avec un commentaire de table datant la mise au rebut ; l'app ne les référence plus. Suppression physique après déploiement + sauvegarde, dans un mandat ultérieur.
3. Le pipeline qui **écrit** encore `cascade_results` LIVE (`cascade/pipeline.py:172`) cesse de l'écrire si aucun lecteur ne subsiste après S9 — sinon le dire.

## S8 — Outils d'exploitation pour la production

Deux commandes CLI, pour le déploiement :
- `labuse admin-list` — liste les comptes admin (email, id, créé le).
- `labuse admin-set <email> --on|--off` — promeut ou rétrograde, avec confirmation, journalisé.
Sur la base locale, retirer le rôle admin des deux comptes de test (`qa-m23@labuse.test`, `gb-test-ae@labuse.local`) via cette commande — première utilisation réelle.

## S9 — Copilote : un seul Copilote, le v2 (lot lourd, en dernier)

Décision Vic : ne garder que v2. Constat CONNEXIONS-3 : v2 ne porte pas les missions lourdes (RECHERCHE, VERIFICATION) — elles passent par v1 depuis `CopiloteView`.

1. **Porter la cascade lourde dans v2** : les missions RECHERCHE et VERIFICATION deviennent des intentions du routeur v2, exécutées par le même moteur de mission (`copilote/moteurs.py`, déjà run-scopé), avec le même rendu progressif (événements) que v1 offrait. L'utilisateur ne doit rien perdre : mêmes résultats sur les 3 parcelles témoins de CONNEXIONS-3, même quota unique `quota_du_compte` (le plafond v1 distinct disparaît).
2. **Retirer v1** : `CopiloteView` n'appelle plus `/api/copilote/runs` ; les endpoints v1 sont retirés (S7) ; `useCopiloteRun` disparaît ou se rebranche sur v2.
3. Registre IA (Z7) : la ligne « Copilote v1 (missions) » disparaît, les missions lourdes ont leur propre surface dans le registre (`copilote_mission`, sonnet-4-6).
4. Test de non-régression : une mission RECHERCHE et une VERIFICATION via v2 rendent tier, parcelles et sources identiques à l'écran ; le quota décrémente sur le compteur unique.
5. Si le lot ne tient pas dans la session : **commiter S1-S8, rendre le compte-rendu, et laisser S9 en Partie B** — ne pas livrer un Copilote à moitié migré.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : S2 les deux libellés finaux des boutons · S2 bis description de la ligne DVF (servi · amont · alimente · action) et confirmation qu'aucune source n'apparaît deux fois · S0.1 les deux libellés de la page IA · S3 le `grep` des lecteurs du run courant et la preuve de bascule à chaud · S5 la ventilation des 108 annonces (rattachables / candidats / impossibles) · S6 « suite 100 % verte » · S7 la liste de ce qui a été supprimé et de ce qui a été renommé · S8 la sortie de `admin-list` après nettoyage · S9 fait ou reporté. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/suite-1
```
