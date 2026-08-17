# AUDIT M104 — la surveillance : mesures, STOP

Mesuré le 17/08/2026 (code + base réelle + écrans). **Aucune fusion, aucun déclencheur
construit — Vic arbitre le nom, la structure et les déclencheurs à retenir.**

## 1. Le mot « veille » — SIX objets distincts, quatre servis à l'écran

| # | objet | où | ce que c'est | servi à l'écran ? |
|---|---|---|---|---|
| 1 | **veilles Copilote** | `copilote_v2/veilles.py`, cron `evaluer-veilles`, event_log kind=`veille` | critères sauvegardés depuis le Copilote, évalués après ingestion → notifications cloche | oui (15 événements réels en base, liens `/copilote?veille=`) ; l'écran de gestion = BACKLOG (M78-quater) |
| 2 | **« Mes veilles » / panneau Secteurs** | `VeillesPanel.tsx`, tables `watch_zones` + `alertes` | zones DESSINÉES sur la carte + alertes `dvf_in_zone` | oui — le rail dit « Secteurs » (M85-B) mais le panneau titre encore « Mes veilles », et tout son vocabulaire interne dit « veille » (« Nouvelle veille géographique », « Enregistrer la veille », `data-veilles-panel`) |
| 3 | **encart cloche « Vos veilles — alertes sur mesure »** | `Header.tsx:406` | recherches sauvegardées (saved_searches, traduction NL M17-B) → notifications `match` à la bascule | oui — c'est l'encart que la Phase 3 supprime de la cloche |
| 4 | **veille documentaire PLU** | `veille_plu.py`, `config/veille_plu.yaml` | procédures d'évolution des PLU (radar_procedure de la fiche, vigilance AU) | oui (fiche) — concept sans rapport avec la surveillance client |
| 5 | **veille succession** | `parcel_veille_succession`, flag `veille_succession` | radar patrimonial M1 (dirigeants ≥ 70 ans / SCI dormantes), filtre `f.veille` de la carte | oui (filtre) — encore un autre sens |
| 6 | **type de registre `veille_zone`** + kind historique `veille` | `notif_registry.py` | le TYPE de notification des chaînes zone/critères | interne (préférences l'affichent comme « Vos zones de veille ») |

**Verdict mesuré : le mot est SATURÉ.** Le réutiliser comme nom de la section unifiée
recréerait le flou nettoyé par M85-B (interdit du mandat, confirmé par la mesure).
Le vocabulaire déjà en place pointe ailleurs : les deux boutons du rail disent
« parcelles surveillées » et « zones de surveillance » — **« Surveillance » est le
candidat naturel** (un mot, aucun homonyme en base ni à l'écran, et c'est le geste :
« ce que je surveille »).

## 2. Proximité des deux écrans

| | **Suivis** (`SuivisPanel`, 42 lignes) | **Secteurs** (`VeillesPanel`, 117 lignes) |
|---|---|---|
| objet | parcelles suivies (plafond 50) | zones dessinées (3 en base) |
| création | sur la FICHE (cloche « Suivre ») — pas dans le panneau | dans le panneau (outil dessin carte, nommage) |
| liste | nom + date du dernier changement (« jamais bougé » = dit) | zones (renommer/supprimer) + compteur d'alertes |
| alertes | AUCUNE dans le panneau — la cloche les porte (`parcelle_suivie`) | liste d'alertes INTÉGRÉE (ack, refresh) — pipeline dédié |
| position | popup GAUCHE | aside DROITE pleine hauteur |
| store | `suivisOpen`/`toggleSuivis` | `veillesOpen`/`toggleVeilles` |

Les deux écrans sont **le même geste à deux échelles** (le commentaire du rail le dit
déjà) mais leurs mécaniques diffèrent sur UN point structurant :

**Découverte de tuyauterie (famille M96 G3 — double tuyau).** Les alertes Secteurs
(`dvf_in_zone`) sont écrites dans une table `alertes` PARALLÈLE (5 776 lignes réelles)
et ne passent JAMAIS par `event_log` : elles n'apparaissent ni à la cloche, ni au
digest, ni au brief. Le commentaire EXPO-2 (« le kind permis a été retiré : la cloche
le couvre déjà ») est trompeur — la cloche couvre les permis des parcelles SUIVIES,
pas ceux des zones. La boucle promise (« je surveille → je reçois des alertes → je
les vois dans la cloche ») est donc VRAIE pour les parcelles et FAUSSE pour les zones.

**Structure proposée** : une seule entrée de navigation, UN panneau à deux volets
(Parcelles / Secteurs) — compatibles car même geste ; les gestes de création restent à
leur place (fiche pour les parcelles, dessin pour les zones). L'encart de la cloche
(recherches sauvegardées, sens n° 3) déménage dans ce panneau (Phase 3.1) comme
troisième volet « Critères » — sa config n'a rien à faire dans un flux d'événements.

## 3. Les déclencheurs : détectable vs branché

### Branchés sur event_log (la boucle complète cloche + digest)

| déclencheur | producteur | événements réels |
|---|---|---|
| vente (mutation DVF) sur parcelle suivie | `evaluer_suivis` | 0 — **cron VPS non posé** |
| permis sur parcelle suivie | `evaluer_suivis` | 0 — idem |
| procédure BODACC (propriétaire) sur suivie | `evaluer_suivis` | 0 — idem |
| changement de zonage sur suivie (empreinte) | `evaluer_suivis` | 0 — idem |
| bascule de statut + match recherches sauvegardées | `detect_events` (au changement de run servi) | 0 depuis M81 (aucun nouveau run servi) |
| veilles Copilote | `evaluer_toutes` | **15** |
| décrochage de fraîcheur (retard source) | `fraicheur.py` → `systeme_pilote` (cloche pilote seule) | **1** (« Source en retard : DPE ADEME ») |
| annonce / maintenance | CLI pilote | 0 (à la décision du mandant) |

**Les zéros de la colonne de droite ne sont PAS des défauts de branchement** : le code
est présent et exécutable (`evaluer-suivis`, `evaluer-veilles`, `detect-events` en
CLI) ; il manque les crons VPS (M85/M98 — dormant connu). À dire séparément, ne pas
le compter comme écart.

### Branché HORS event_log (le double tuyau)

| déclencheur | état |
|---|---|
| vente DVF dans un secteur (`dvf_in_zone`) | **5 776 alertes réelles** dans la table `alertes` — jamais cloche, jamais digest. Refonte de tuyau, pas une création. |

### Détectables, NON branchés (l'écart)

| déclencheur manquant | la donnée existe | coût de tolérance estimé |
|---|---|---|
| permis déposé dans un secteur | `sitadel_permits` (géocodés) | moyen (volumes réels par zone) |
| procédure BODACC dans un secteur | `bodacc_procedures` × parcelles de la zone | faible (rare, signal fort) |
| changement de zonage dans un secteur | `parcel_zone_plu` (empreinte, comme les suivis) | faible (événement rare) |
| source enrichie / nouvelle publication amont | radar `nouvelle_publication` (M105) — écrit `source_radar`, AUCUNE notification | à cadrer : client ou pilote ? (le pilote a déjà healthz/Sources) |
| bascule de tier d'une parcelle suivie, nommée comme telle | `detect_events` produit `bascule` GLOBAL (compte NULL) mappé `parcelle_suivie` — pas filtré sur les suivis du compte | nul si on ne fait que raccorder |

## 4. La cloche (état pour la Phase 3)

- L'encart « Vos veilles — alertes sur mesure » (config complète : NL + exemples +
  liste/suppression) vit au PIED du panneau notifications — à déménager, pas à perdre
  (aucune régression).
- L'en-tête est bien DÉRIVÉ du registre (M87 P5, `libelles_entete_cloche`) ✓ — il le
  restera ; « Le point du jour → » déborde sur deux lignes dans l'en-tête serré
  (constaté), la refonte reprend les classes du panneau brief
  (`docs/DA-ACCUEIL-BRIEF-v1.html`).

**STOP — Vic arbitre : (1) le nom de la section (« Surveillance » proposé — « veille »
est éliminé par la mesure) ; (2) la structure (panneau unique à volets proposé) ;
(3) quels déclencheurs manquants construire, et le sort du double tuyau `alertes`
(raccordement event_log = la boucle honnête pour les secteurs).**
