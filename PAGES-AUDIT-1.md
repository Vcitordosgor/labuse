# PAGES-AUDIT-1 — Inventaire des pages : app vs dashboard, visible vs non

**Branche** `feat/couches-tuyau` · **départ** `e1d98ea5` (Étape 0) · lecture seule (aucune modification du produit) · preuve = captures.

## En tête

**17 pages de premier niveau, dont 8 côté client et 9 côté admin (dashboard).**

Le front n'a **pas de routeur d'URL** : c'est une SPA à *vue* (`store/useApp.ts : type View`). Toutes les pages vivent sur le **même chemin** (`/`, servi `/socle/` en dev) ; l'état est encodé dans le **hash** (`#…`), et **seules certaines vues** y survivent au rechargement. Le menu client est le **Rail** (`components/Rail.tsx`) ; le dashboard admin est **plein écran** (`components/admin/AdminView.tsx`), son propre rail à 8 sections + la LED santé.

Au-dessus des 17 pages s'ajoutent des **surfaces secondaires** (overlays montés *par-dessus* la carte, jamais routées seules) : la Fiche parcelle, la fiche commune (ContextePanel), le comparateur, les grands tableaux (Communes / Évolution / Radar / Densifier), la TimeMachine, le Parcours Tinder, le SourceDrawer, les **17 outils** (ModulePanel), et le détail admin « Destinations » (drill-down du Circuit). Elles sont listées après le tableau mais ne comptent pas dans les 17.

---

## Tableau complet

### Côté client (app) — 8 pages · accès : **client connecté** (tout le shell est derrière le login serveur ; navigation sans session → redirection `/login`)

| Route (URL réelle) | Fichier | Côté | Accès | Atteignable | Vivante |
|---|---|---|---|---|---|
| `/` (défaut) — aussi `#idu=`, `#f=`, `#c=`, `#m=`, `#v=1` | `components/map/MapView.tsx` + `components/panel/LeftPanel.tsx` | app | client connecté | Rail « **Carte** » | **Vivante** — tuiles + `getParcelsGeojson`/`getCommunes`/`getFiltreIdus` ; LeftPanel lit `/accueil/fraicheur` |
| `/` + tiroir Outils (un outil = `#m=<clé>`) | `components/Rail.tsx` (tiroir) → `components/outils/ModulePanel.tsx` | app | client connecté | Rail « **Outils** » | **Vivante** — catalogue `outils/registry.ts` (17 outils), chacun fetch son endpoint |
| `/` (pas de hash — état interne, remis à « cartes » au reload) | `components/copilote/CopiloteView.tsx` | app | client connecté | Rail « **Copilote** » | **Vivante** — `copiloteV2Ask`/`copiloteV2Missions` (+ **Journal** d'événements, cf. exploitation) |
| `/#radar=1` (survit au reload) | `components/outils/RadarView.tsx` | app | client connecté | Rail « **Radar** » | **Vivante** — `getRadarBiens`/`getRadarBienDetail` + mutations |
| `/#surveillance=secteurs\|parcelles\|criteres` (deep-link d'entrée) | `components/surveillance/SurveillancePanel.tsx` | app | client connecté | Rail « **Veille** » | **Vivante** — `getSuivis`/`getSavedSearches`/`getRadarVeilles` + mutations |
| `/` (pas de hash — état interne) | `components/projets/ProjetsPanel.tsx` (+ `ParcoursTinder.tsx`) | app | client connecté | Rail « **Projets** » | **Vivante** — `getProjets`/`getCourrierDemandes` + mutations |
| `/` (pas de hash — état interne) | `components/crm/Kanban.tsx` | app | client connecté | Rail « **CRM** » | **Vivante** — `getPipeline`/`getPipelineMeta` + mutations |
| `/` (pas de hash — état interne) | `components/sources/SourcesPage.tsx` | app | client connecté | Rail « **Sources** » (zone basse) | **Vivante** — `getSources`/`getSourcesCouverture`/`getSourcesCouches` (registre en direct) |

### Côté admin (dashboard « Tour de contrôle ») — 9 sections · accès : **admin seulement** (`exiger_admin` = 403 client + 2FA TOTP au login ; visibilité front conditionnée au rôle)

Toutes sur `/#admin=1` (le hash restaure le shell, ouvre « Pilotage » par défaut) ; la **section** est un état interne (`adminSection`), sans URL propre par section.

| Route | Fichier | Côté | Accès | Atteignable | Vivante |
|---|---|---|---|---|---|
| `/#admin=1` (défaut) | `components/admin/AdminView.tsx` (`PilotageSection`) | dashboard | admin | menu admin « **Pilotage** » | **Vivante** — `getAdminPilotage`/`getAdminCircuit`/`getRadarCheck`/`getAdminLicences`/`getOffres` (8 jauges, à-faire, journal) |
| `/#admin=1` → Comptes | `components/admin/Licences.tsx` (`LicencesSection`) | dashboard | admin | menu admin « **Comptes** » | **Vivante** — `getAdminLicences`/`getAdminMails`/`getOffres` + mutations comptes/mail |
| `/#admin=1` → Données | `components/admin/Donnees.tsx` (`DonneesSection`) | dashboard | admin | menu admin « **Données** » | **Vivante** — le **Circuit** (`circuit/*` : `getAdminCircuit`/`getAdminCircuitTaches`/`postAdminCircuitVerifier`) ; a **absorbé** les anciennes sections Sources + Flux |
| `/#admin=1` → Courrier | `components/admin/Courrier.tsx` (`CourrierSection`) | dashboard | admin | menu admin « **Courrier** » | **Vivante** — `getAdminCourrierDemandes` + dépôt/statut |
| `/#admin=1` → Radar | `components/admin/Radar.tsx` (`RadarSection`) | dashboard | admin | menu admin « **Radar** » | **Vivante** — `getRadarExtraction`/`getRadarCheck`/`getRadarReverif` + mutations |
| `/#admin=1` → Produit | `components/admin/Produit.tsx` (`ProduitSection`) | dashboard | admin | menu admin « **Produit** » | **Vivante** — `getAdminProduit`/`getAdminSignalements` + statuts |
| `/#admin=1` → IA | `components/admin/Ia.tsx` (`IaSection`) | dashboard | admin | menu admin « **IA** » (surface mauve) | **Vivante** — `getAdminIa` + `postAdminLicenceQuota` |
| `/#admin=1` → Contacts | `components/admin/Contacts.tsx` (`ContactsSection`) | dashboard | admin | menu admin « **Contacts** » | **Vivante** — `getContactsInstitutionnels` + CRUD contacts communes |
| `/#admin=1` → Horloge | `components/admin/Cron.tsx` (`CronSection`) | dashboard | admin | **hors menu** — atteinte via la jauge « Système » / une ligne à-faire du **Pilotage** | **Vivante** — `getAdminCron` (refetch 5 s)/`getAdminCronLog` + `postAdminCronRun` |

---

## Les deux questions à traiter explicitement

### 1) Les pages « Sources » — combien, où, cliente vs admin, laquelle lot 3 a modifiée

**Il y en a deux, une par côté :**

- **Cliente** — `components/sources/SourcesPage.tsx`, vue `sources`, titre à l'écran **« Sources & fraîcheur »** (vitrine client de traçabilité). Reachée par le Rail « Sources ».
- **Admin** — la section **« Données »** (`components/admin/Donnees.tsx`, le **Circuit**). Il n'existe **plus** de section admin « Sources » nommée : elle a été **fusionnée** dans « Données » (ADMIN-1 · AD2 — les anciens deep-links `sources`/`flux` y sont redirigés). C'est la page « sources » côté admin.

**COUCHES-REGISTRE-2 lot 3 a modifié la page CLIENTE** : `SourcesPage.tsx`. Ajout du **sens inverse** — pour chaque source, les **couches carte** qu'elle alimente, en pastilles cliquables qui allument la couche et basculent sur la carte (`versCouche`, lignes 55‑60 et 133‑146 ; query `getSourcesCouches` → endpoint back `/sources/couches`). Visible sur la capture cliente (« Couches carte : Lignes moyenne tension (HTA) ↗ », « Téléphérique ↗ », « Pôles d'échange ↗ »…). La section admin « Données » n'a pas été touchée par ce lot.

### 2) Chaque page cliente : donnée du registre d'aujourd'hui, ou liste figée ?

**Aucune page cliente ne porte de liste figée d'une version antérieure — toutes lisent le back en direct (react-query / fetch).** En particulier :

- **Sources** lit le **registre du jour** : `getSources` (94 sources servies au moment de la capture), `getSourcesCouverture` (431 663 parcelles · 24/24 communes), `getSourcesCouches`. Le compteur « 91 à jour » est **dérivé** de `etat_client`, aucun chiffre en dur ; la borne DVF et la licence sont **lues en base**, pas codées.
- **Carte, Copilote, Radar, Veille, Projets, CRM** : idem, tout est fetché (voir colonne « Vivante »).
- Les **seules** structures « en dur » côté client sont des **catalogues de navigation**, pas de la donnée de registre : la liste du Rail (`RAIL`) et le registre des outils (`MODULES`, 17 outils). Ce sont des menus, pas une copie gelée des sources.

Conclusion : la question « registre du jour vs figé » ne trouve **aucun cas figé** côté client.

---

## Liste 1 — Pages orphelines (aucun lien n'y mène)

- **`ProgrammesSection`** (`components/admin/Programmes.tsx`) — **orpheline**. Exportée mais **jamais importée ni rendue** (vérifié par grep : 0 usage hors sa propre définition). Le deep-link `programmes` ne l'ouvre pas : il **sort** de l'admin vers l'outil « Scan patrimoine » (`setModule('patrimoine')`). Seul son sous-composant **`CollecteProgrammes`** survit, réutilisé dans l'outil `components/outils/VeillePromoteurs.tsx`. La section elle-même est un **vestige** du modèle admin précédent (LOT S1).

**À ne pas confondre avec des orphelines :**
- `Cron.tsx` (Horloge) n'est **pas** orpheline : hors menu, mais atteinte depuis le Pilotage (jauge « Système » + lignes à-faire).
- `DestinationsDetail` (`components/admin/Destinations.tsx`) n'est **pas** orpheline : atteinte en **drill-down** dans « Données » (Circuit → détail du réservoir `plu_destinations`). Elle a quitté le rail (DASHBOARD-2 · Lot 7) mais reste reliée.
- **Routes fantômes** (redirigées, sans page propre — pas des pages, à signaler) : côté admin `sources`, `flux`, `destinations` → `donnees` ; `programmes` → outil patrimoine (via `_rediriger` / le `useEffect` d'AdminView).

## Liste 2 — Pages qui exposent au client de l'information d'exploitation (ce qui devrait vivre côté dashboard)

- **Sources — « Sources & fraîcheur »** (`SourcesPage.tsx`) — le cas le plus net, **par conception** (promesse de traçabilité) : **états de fraîcheur par source** (« à jour » / « mise à jour en cours »), **fiabilité** (« à confirmer » / « sous convention » / « accès légal restreint »), **couverture** (parcelles, communes), millésime de publication. C'est littéralement une page de fraîcheur/états de sources exposée au client.
- **Carte — bandeau d'accueil du LeftPanel** (`LeftPanel.tsx`, `data-accueil-fraicheur`) : pastille **ton `ok`/`warn`/`error`** + phrase sur l'état des sources, lue de **`/accueil/fraicheur`** — *le même champ que la page Sources et que le dashboard admin*. Un état d'exploitation (santé/fraîcheur) posé sur l'écran d'accueil.
- **Copilote — bloc « Journal »** (`CopiloteView.tsx`, `data-journal`) : rend le **log d'événements** interne (numéro de séquence `seq`, `kind`, `payload` JSON). Diagnostic technique visible côté client.

*Note d'arbitrage :* Sources est une vitrine **volontaire** (le mandat produit veut la traçabilité) ; les deux autres (bandeau fraîcheur, journal Copilote) sont les vraies **fuites** d'information d'exploitation à trancher lors du rangement.

---

## Ce qu'on n'a pas fait

Aucun déplacement, aucune correction, aucun nettoyage. Le produit n'a pas été modifié. Ce rapport sert à écrire le mandat de rangement.

## Preuve

- **8 captures clientes** : `captures/pages-audit/client/` (`00_cartes`, `00_outils`, `00_copilote`, `00_radar`, `00_veille`, `00_projets`, `00_crm`, `00_sources`).
- **9 captures admin de premier niveau** : `captures/pages-audit/admin/` (`01_pilotage` … `08_contacts`, `09_cron`).
- Harnais Playwright (Chrome) : `frontend/qa/pages_audit.mjs` (+ `pages_audit_fix.mjs` pour re-saisir Sources et Données après chargement complet — 94 lignes de source, Circuit « 12 choses à regarder »).
- **`tsc -b` vert** (exit 0).
