# RAPPORT M85-B — La politique d'envoi : registre, préférences, suivi de parcelle

Branche `feat/m85b-politique`. La règle du mandant : un client reçoit un mail SSI (1) une parcelle
SUIVIE a changé, (2) une ZONE de veille a bougé, (3) LABUSE a quelque chose d'important à dire.
Cadence : chaînes 1+2 → un mail/jour max (digest du matin, J-1) ; chaîne 3 → quand le mandant décide.

---

# PHASE A — Le registre et les préférences (LIVRÉ, commit `fcbb8bf0`)

## A1 — Le registre (`src/labuse/notif_registry.py`) : l'inventaire UNIQUE

| Type | Chaîne | Producteur | Canaux | Cadence | Désactivable | Gabarit |
|---|---|---|---|---|---|---|
| `parcelle_suivie` | 1 | suivi_parcelle (SQL, ingestion + bascule run) | cloche + mail | digest quotidien J-1 | oui | digest |
| `veille_zone` | 2 | evaluer_toutes / saved_searches (SQL) | cloche + mail | digest quotidien J-1 | oui | digest |
| `annonce_produit` | 3 | pilote (CLI/écran) | cloche + mail | immédiat (décision mandant) | oui | annonce |
| `maintenance` | 3 | pilote (CLI/écran) | cloche + mail | immédiat | **NON** (conséquences réelles) | maintenance |
| `systeme_pilote` | — | ingestion/fraîcheur (M84) | cloche seule | à l'événement | oui | — |

**Garde-fou** : `creer_notification` lève `ValueError` sur tout `kind` non déclaré — personne n'ajoute
un envoi hors registre (testé). Le **marché** (bascule/BODACC/match partagés, compte NULL) n'est PLUS
un type de mail : flux cloche informatif, **hors des 3 chaînes → jamais d'e-mail** (« rien d'autre »).

## A2 — Préférences par type de registre (remplacent `notif_canaux` {veille, suivi, marche})
Migration `labuse migrer-prefs` : `veille→veille_zone`, `suivi→parcelle_suivie`, `marche` SUPPRIMÉ.
Défaut nouveau compte : tout activé. **`maintenance` affiché mais VERROUILLÉ** (e-mail toujours actif,
la case est cochée-désactivée avec la raison). Désinscription globale : coupe les désactivables, garde
`maintenance`. Écran in-app (cloche) + page serveur à jeton. **grep : zéro résidu de l'ancien schéma.**

---

# PHASE B1 — Le suivi de parcelle : mesure (STOP)

## Ce qui existe déjà
- **Le bouton « Suivre » EXISTE** : `WatchButton` sur la fiche (M14) — icône **cloche, verte quand
  suivie, PAS mauve**. Table `watched_parcels (compte_id, idu)` + endpoints `/events/watch/{idu}`.
- **Un producteur PARTIEL existe** : `detect_events` insère déjà, pour une parcelle suivie, les
  **permis à ≤ 300 m** (`kind='permis'`, cloisonné au compte). MAIS : (a) il tourne seulement sur un
  **diff de run** (`detect-events`), pas à chaque ingestion ; (b) il capte la **proximité (≤ 300 m)**,
  pas le changement SUR la parcelle ; (c) il ne couvre que les permis (ni mutation, ni BODACC, ni zonage).

## Les changements DÉTECTABLES sur une parcelle (source × fréquence)

| Changement | Source en base | Lien parcelle | Fréquence de détection réelle |
|---|---|---|---|
| **Nouveau permis** | `sitadel_permits` (geom + `idu_codes`) | ON la parcelle (`idu_codes`) OU ≤ 300 m (secteur) | mensuelle amont (SDES) — **figée au 30/06** faute de cron |
| **Mutation (vente)** | `dvf_mutations` (geom, commune) | point-dans-parcelle / ≤ x m | **semestrielle** (dernier T4 2025 ; prochain ~oct. 2026) → 0 récent |
| **Procédure BODACC** | `bodacc_procedures` (SIREN propriétaire) | via propriétaire de la parcelle | ~4-5/mois **sur toute l'île** → très rare sur une parcelle donnée |
| **Changement de zonage (GPU)** | `spatial_layers` plu_gpu | intersection | **cascade gelée** — réingestion = grande passe Mac, PAS un cron → rare |
| **Passage de tier (bascule)** | diff de deux runs servis | `parcel_p_score_v2` | seulement à une **nouvelle grande passe** (type M81) → rare, événementiel |

## Estimation de volume (MESURÉE sur les données réelles)
Rythmes mesurés : permis **50-140/mois** sur l'île (2026 : jan 142 … mai 53, juin 80) ; DVF **~1 300/
semestre** mais **0 récent** (cadence) ; BODACC **~4-5/mois** île entière ; bascule **0 entre deux
passes**. Test spatial direct : pour **5 parcelles**, permis à ≤ 300 m **sur 90 jours = 1** (mesuré).

**Un client avec 5 parcelles suivies + 3 zones de veille recevrait, avec les données réelles :**
- parcelles suivies : **≈ 0,3 événement/mois** (1 permis / 5 parcelles / 3 mois) → **< 1 mail/semaine**,
  souvent **0 pendant des semaines**. Mutation : 0 (cadence). BODACC sur SON propriétaire : quasi nul.
- zones de veille : **0 entre deux grandes passes** (les matchs de bascule n'arrivent qu'à un rejeu de run).

→ **Bilan : bien moins d'un mail par semaine, typiquement zéro plusieurs semaines d'affilée.** Le
plafond « un mail/jour » ne mord quasiment jamais. C'est cohérent avec la doctrine (la retenue) — le
digest ne part que quand quelque chose bouge. **Caveat** : mesuré SOUS le retard d'ingestion ; même au
rythme historique (crons actifs), l'ordre de grandeur reste **~1-2 mails/mois** depuis les suivis.

## Ce que tu dois arbitrer (STOP)
1. **Le périmètre du « une parcelle suivie a changé »** — deux choix, cumulables :
   - **quels changements** : permis · mutation · BODACC-propriétaire · zonage GPU · bascule de tier ?
   - **quelle maille pour les permis** : **SUR la parcelle** (strict, `idu_codes`) OU **≤ 300 m**
     (le secteur bouge, comme aujourd'hui) ? Ma recommandation : **permis SUR la parcelle** (fidèle à
     « votre parcelle a changé ») + une mention distincte « secteur » plus tard si tu veux.
2. **Où consulter la liste des parcelles suivies** : une **section « Suivis »** (à côté de « Secteurs »
   dans le rail), un onglet de la fiche, ou l'accueil ? Ma proposition : une entrée **« Suivis »** près
   de « Secteurs » (les deux sont des périmètres de surveillance du client).

## Garde-fous (Phase A + B1)
tsc 0 · vitest 36/36 · build vert · pytest 155 (+ refus hors registre + maintenance verrouillée testés) ·
golden 119/119 diff 0 · console 0. **NE PAS MERGER.** STOP — j'attends ton arbitrage (périmètre des
changements + maille permis + emplacement de la liste) avant de construire le producteur (B2).
