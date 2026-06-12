# LA BUSE — AUDIT COMPLET, CHIRURGICAL ET IMPITOYABLE

> Audit en aveugle, posture « promoteur réunionnais sceptique qui doit signer un chèque ».
> Réalisé sur le pilote local (Saint-Paul, 3 000 parcelles, healthcheck 13/13, démo PRÊTE).
> **Aucune correction appliquée** — tout est documenté pour tri par lots.
> Captures dans `audit_shots/` (commitées). Méthode : navigation réelle (Chromium/Playwright),
> orthophotos IGN avec contour parcellaire superposé, empreintes bâties OSM réelles (8 765
> bâtiments chargés), requêtes PostGIS, mesures de latence, sondes d'entrées invalides.
>
> **Ce que je peux AFFIRMER** (mesuré) est séparé de **ce qu'un promoteur doit VALIDER**
> (réalisme des €/m², coûts, marge). Je ne tranche jamais à sa place sur le métier.

---

## ⚠️ VERDICT EN UNE LIGNE
Le produit est **beau, honnête dans le discours, rapide… et repose sur un trou béant** :
il est **incapable de distinguer un terrain nu d'un terrain déjà bâti**, et sa parcelle
vedette de démo (BP0571, vendue avec un CA de 23,5 M€) est **une résidence existante
occupée**. En l'état, un promoteur qui connaît Saint-Paul ferme l'app en 2 minutes.

---

# 🔴 BLOQUANT POUR VENDRE

## R1 — « Déjà bâti » non détecté : la parcelle vedette est une résidence existante
**Où :** moteur de déclassement (`scoring/declassement.py`) + fiche/bilan de toute
opportunité. **C'est le défaut n°1.**

**Ce que j'affirme (preuves) :**
- Le déclassement ne teste QUE : surface, pente, et 4 sous-types OSM (parking, pitch,
  cimetière, école). Il n'existe **aucune détection de bâti existant**. OCS GE
  « artificialisé » est traité en PASS (neutre) : **813 des 814 opportunités** sont sur
  sol « artificialisé » (requête PostGIS).
- **BP0571** (vedette de la démo, du one-pager, de tous les mails — CA bilan **23,5 M€**) :
  l'orthophoto IGN avec le contour cadastral superposé (`audit_shots/overlay_BP0571.jpg`)
  montre **4 immeubles d'habitation existants + leurs parkings pleins** À L'INTÉRIEUR de la
  parcelle. C'est une **copropriété occupée**, pas du foncier mobilisable.
- Empreintes bâties **OSM réelles** (8 765 bâtiments) croisées sur les 814 opportunités :
  **47 % ont ≥30 % de bâti**, **16 % ont ≥50 % de bâti**, couverture bâtie moyenne **31 %**.
  Seules **5 opportunités sur 814** font ≥1 000 m² ET 0 % de bâti OSM.
- Pire : BP0571 ne ressort qu'à **18 %** bâti dans OSM alors que l'orthophoto la montre
  largement construite → **OSM sous-cartographie La Réunion**, donc le taux réel de
  « déjà bâti » est **supérieur** à 47 %.

**Reproduire :** ouvrir la fiche BP0571 → bilan « CA 17,3–26,0 M€, surface vendable
5 616 m² » ; comparer à l'orthophoto (bouton « Vue du ciel » de la fiche, ou
`overlay_BP0571.jpg`). Le bilan propose de **construire à neuf sur une résidence habitée**.

**Méthode validée (contre-épreuve) :** le même pipeline d'overlay appliqué à **BO0845**
(`overlay_BO0845.jpg`) tombe **exactement sur un parking plein de voitures** — ce qui
correspond au verdict « parking 82 % » de LA BUSE. La méthode d'overlay est donc fiable :
quand elle montre BP0571 remplie d'immeubles, c'est réel. **Le détecteur de parkings marche ;
il manque seulement un détecteur de BÂTIMENTS** — c'est précisément le trou.

**Nuance honnête (à valider par un promoteur) :** un terrain bâti n'est pas toujours sans
valeur — démolition/reconstruction ou surélévation existent (surtout sous servitude de
mixité sociale qui pousse à densifier). MAIS le produit présente ces parcelles comme du
**terrain nu** avec un **bilan « construction neuve sur emprise vide »**, sans jamais
signaler qu'il y a déjà des bâtiments ni intégrer le coût de démolition/éviction. Le défaut
n'est pas « BP0571 vaut zéro », c'est « LA BUSE ne voit pas qu'elle est bâtie et ment sur le
bilan ».

**Correction proposée (non codée) :**
1. Ingérer une couche **bâti** fiable (BD TOPO IGN « bâtiment », ou cadastre bâti) — OSM
   seul est trop incomplet ici.
2. Calculer la **couverture bâtie** par parcelle (comme la couverture OSM existante) et :
   soit déclasser/flaguer au-delà d'un seuil (ex. ≥30 % → « bâti existant — opération de
   renouvellement, à étudier »), soit **afficher un badge « déjà bâti »** + ajouter un
   coût de démolition au bilan.
3. **Choisir une autre parcelle vedette de démo** (ex. BK0023, **vacante et accessible**,
   `overlay_BK0023.jpg`) et refaire le pack commercial autour d'elle.

## R2 — Dépendance CDN runtime : écran noir TOTAL si unpkg est injoignable
**Où :** `api/web/index.html` (Leaflet chargé depuis `unpkg.com`), `app.js` `main()` →
`initMap()` appelle `L.map(...)` en premier, **sans garde**.

**Ce que j'affirme (preuves) :** lors du tout premier chargement (capture
`audit_shots/01b_landing_after8s.png`), `unpkg.com/leaflet@1.9.4/...` a échoué
(`net::ERR_CERT_AUTHORITY_INVALID`, ici à cause d'un proxy TLS). Conséquence : `L` est
indéfini → `initMap()` jette → **`main()` s'arrête net** → **KPIs vides, carte noire, liste
vide, aucune donnée**. Pas seulement la carte : **toute l'app** est morte, car Leaflet est
un script bloquant et le crash stoppe toute l'initialisation.

**Pourquoi c'est un vrai risque commercial (pas juste un artefact de sandbox) :** beaucoup
de réseaux d'entreprise / d'agences / de mairies font de **l'inspection TLS** (proxy qui
réémet les certificats) → Chromium rejette unpkg exactement comme ici. Idem si unpkg est
momentanément down, bloqué, ou en démo hors-ligne. Le promoteur voit un **écran noir** et
conclut « c'est cassé ».

**Reproduire :** charger `/app/` avec unpkg bloqué (ou TLS intercepté) → écran noir total.

**Correction proposée :** **vendre (vendoriser) Leaflet en local** (`web/vendor/leaflet.*`,
~150 Ko) au lieu du CDN ; et envelopper `initMap()`/`main()` pour qu'un échec carte
**n'empêche pas** le reste (KPIs, liste, fiches restent utilisables). Les tuiles resteront
externes (inévitable), mais l'app ne doit jamais être un écran noir.

---

# 🟠 MAJEUR

## O1 — L'enclavement n'est jamais signalé (et la majorité des opportunités semblent sans accès)
**Où :** `cascade/layers/phase1.py::AccesLayer`. Elle donne un **bonus** quand une voirie
touche, mais **ne pénalise/flague jamais** son absence.
**Preuve (PostGIS) :** opportunités sans voirie à proximité — **<1 m : 660/814 · <3 m :
516/814 (63 %) · <6 m : 161/814 · <10 m : 81/814**. Même en tolérant 6 m (les axes BD TOPO
ne longent pas la limite), **161 opportunités n'ont aucune voirie détectée** → enclavement
probable. L'accès est LA condition n°1 d'un projet ; ici elle est récompensée mais jamais
réclamée.
**À valider par un promoteur :** la voirie BD TOPO est un filaire d'axes, pas la limite ;
certaines parcelles ont un accès par servitude non cartographié. Mais 161 sans accès <6 m
mérite au minimum un flag.
**Correction :** ajouter à la cascade un signal « **accès non identifié** » (flag, pas
exclusion) quand aucune voirie n'est à < X m ; le remonter dans la vigilance du résumé.

## O2 — Bilan : coût de construction sous-évalué pour La Réunion, et calculé sur la mauvaise surface
**Où :** `faisabilite/bilan.py` (hypothèses par défaut), bloc bilan de la fiche
(`audit_shots/10_bilan.png`).
**Ce que j'affirme :** le coût de construction par défaut est **1 800–2 200 €/m²** et il est
appliqué **au m² HABITABLE** (« 5 616 m² × 1 800–2 200 »). Or (a) en collectif à La Réunion
— île, matériaux importés, normes para-cycloniques et sismiques — les coûts tout compris
sont plutôt de l'ordre de **2 200–2 800+ €/m²** ; (b) le coût se rapporte normalement à la
**surface de plancher** (SHON, > habitable de 10–20 %), pas à l'habitable. **Les deux biais
vont dans le même sens : ils SOUS-estiment le coût → SUR-estiment la charge foncière** (ce
qu'on peut payer le terrain). Un bilan « optimiste par défaut » est exactement ce qui fait
fuir un promoteur expérimenté.
**À valider par un promoteur :** ses propres ratios. C'est honnêtement signalé « hypothèse
configurable » — mais **le défaut devrait être prudent, pas optimiste**.
**Correction :** relever le coût par défaut à une fourchette Réunion crédible, le baser sur
la surface de plancher, et l'écrire ; idéalement, sourcer un repère local (FRBTP/observatoire).

## O3 — Charge foncière : fourchette inexploitable (−0,2 M€ → 8,1 M€) et bas négatif anxiogène
**Où :** bilan, ligne « Charge foncière acceptable ». **Preuve :** pour BP0571,
**−216 k€ à 8,1 M€** (médiane 5,2 M€). Un écart de **37×**, du négatif au multi-millions :
ça ne dit rien d'actionnable (« le terrain vaut entre rien et 8 millions »). Le bas négatif
(prix bas × coûts hauts) **alarme** sans informer. La largeur vient du produit de deux
fourchettes (prix DVF ±20 % × coûts) qui se composent.
**Correction :** présenter d'abord la **médiane** (5,2 M€ ≈ 566 €/m² terrain) comme chiffre
de référence, mettre la fourchette en second, et **borner le bas à 0** avec une note (« en
hypothèse défavorable, l'opération ne dégage pas de valeur foncière »).

## O4 — La démo « pipeline de prospection » est peuplée de FAUX POSITIFS
**Où :** `demo.py::seed_demo_pipeline` (sélectionne les 4 premières parcelles **par IDU**,
pas par verdict) → kanban de démo (`audit_shots/05_kanban.png`).
**Preuve :** les cartes du pipeline de démo sont : **B00877 « faux positif probable », 63 m²**
(micro-parcelle suivie en prospection !), **BC0103 « faux positif », 196 396 m²** (19,6 ha),
**BC0076 « faux positif », 67 332 m²**, **BD0005 « à creuser », opp = 1**. On **vend la valeur
prospection en montrant qu'on prospecte du déchet**. Un promoteur le remarque immédiatement.
**Correction :** seeder le pipeline avec de **vraies opportunités** (idéalement des parcelles
VACANTES après correction R1), pas les 4 premières par ordre alphabétique.

## O5 — `/parcels/%00` renvoie 500 (erreur serveur non gérée)
**Où :** route `/parcels/{idu}`. **Preuve :** `curl /parcels/%00` → **HTTP 500** (attendu :
404 ou 422). Les autres entrées invalides sont bien gérées (`limit=abc` → 422, `format=pdf`
→ 422, `min_opportunity=999` → 422). Un octet nul casse la route.
**Correction :** valider/normaliser l'IDU en amont (longueur/charset) → 404 propre ; et un
handler d'exception global qui ne renvoie jamais de 500 brut.

## O6 — Servitude « logements aidés » (mixité sociale) enfouie, alors qu'elle change le projet
**Où :** fiche BP0571, bloc « PLU détaillé » (lazy, `audit_shots/12_promoteur.png`) :
prescription **« Clause logements aidés — zone reg(it) Forte »**. C'est une **servitude de
mixité sociale** : elle **impose un % de logements sociaux** → elle change radicalement le
bilan d'un promoteur privé. Or elle apparaît tout en bas, dans le bloc enrichi chargé en
différé, **pas dans le résumé ni dans la vigilance**.
**Correction :** quand une prescription « logements aidés / mixité sociale / emplacement
réservé » est interceptée, la **remonter dans la vigilance du résumé** (« % de logements
aidés imposé — à intégrer au bilan »).

## O7 — VALEUR CLIENT : retard structurel face à Kel Foncier sur tout ce qu'un promoteur paie
**Constat (recherche) :** [Kel Foncier](https://kelfoncier.com/logiciel/) propose **50+
critères** (réglementation, risques, prix, **propriétaire**), **l'identification des
propriétaires** (et leur patrimoine, conforme RGPD), une **préfaisabilité validée par des
instructeurs permis** (250 réglementations, taxe d'aménagement, coûts environnementaux), des
**alertes PLU/faisabilité**, **toute la France**, et une **app mobile** stores.
**LA BUSE, en face :** **pas de propriétaire** (choix légal assumé, mais c'est LA douleur n°1
du promoteur — « le propriétaire, vous l'avez ? »), **1 commune** (vs France entière),
faisabilité **non validée par des instructeurs**, **pas de taxe d'aménagement**, pas d'app
mobile native. **Différenciateurs réels de LA BUSE :** la **traçabilité** (chaque verdict
pointe sa source — Kel Foncier est plus opaque), le **déclassement motivé** des faux
positifs, la **calibration Réunion** (SAR/PPR/EPSG:2975), et le **ton honnête**. Mais ces
edges sont **minces** et largement **annulés par R1** (un outil qui confond bâti et nu n'a
pas de crédibilité « pré-tri fiable »).
**Implication commerciale :** vendre LA BUSE comme « le Kel Foncier péi » est intenable
aujourd'hui. L'angle tenable est « **pré-tri local honnête et traçable** » — mais seulement
après avoir réglé R1.

---

# 🟡 MINEUR

## J1 — `/discover` lent (~2 s) : scanne tout l'historique d'évaluations
**Preuve :** `/discover?limit=50` mesuré à **1 841–1 992 ms** (vs fiche 56 ms, geojson
160–227 ms). La requête fait un `DISTINCT ON (parcel_id)` sur **toute** la table
`parcel_evaluations` (≥189 k lignes, qui grossit à chaque rebuild). Pas sur le chemin
principal de l'UI (la liste latérale est construite côté client depuis le geojson), mais
l'endpoint Découverte (offre B) et `labuse discover` traînent, et ça empire avec l'historique.
**Correction :** index `(parcel_id, evaluated_at DESC)` + éventuellement une vue
matérialisée « dernière éval par parcelle », ou purge de l'historique.

## J2 — La liste latérale n'affiche que 80 des 2 592 résultats, sans pagination
**Preuve :** capture `01_landing.png` → « **80 AFFICHÉES / 2592** ». Pas de « charger plus »
ni de tri visible au-delà des 80. Le promoteur ne voit jamais 97 % des résultats depuis la
liste (il doit passer par la carte/filtres).
**Correction :** pagination ou défilement infini ; ou au minimum un message + accès au reste.

## J3 — « Continuité foncière » affichée sur ~99 % des opportunités = bruit
**Preuve :** mesuré — **809/814 opportunités** ont au moins une voisine contiguë en
opportunité/à creuser (tissu urbain dense). Le bandeau « un assemblage peut être étudié »
apparaît donc quasi partout → il ne **discrimine rien** et dilue les vrais signaux. (Wording
déjà neutralisé lors d'une passe précédente, mais le critère reste non sélectif.)
**Correction :** ne déclencher que sur une vraie cohérence (ex. ≥2 voisines vacantes même
zone), ou retirer le bandeau et garder seulement la liste des voisines.

## J4 — Le résumé liste « Pourquoi elle ressort » (positifs) même pour un faux positif
**Preuve :** fiche BO0845 (`audit_shots/07c_mobile_fiche.png`) : verdict « Faux positif
probable », puis « **POURQUOI ELLE RESSORT** : Zonage favorable, Surface mobilisable, Vocation
SAR compatible ». Lister 3 raisons « pour » juste après l'avoir déclassée est déroutant.
**Correction :** pour un faux positif/exclue, renommer en « Signaux bruts (avant
déclassement) » ou masquer la colonne positifs.

## J5 — Saisie de contact par `window.prompt` (UX prototype)
**Où :** `app.js` `wireSheetActions` → bouton « Ajouter / modifier contact » ouvre des
`window.prompt()` successifs (nom, puis tel/mail). C'est fonctionnel mais ça **fait
prototype** ; aucune validation de format, pas d'annulation propre.
**Correction :** un petit formulaire inline dans la fiche prospection.

## J6 — DVF : un min à 1 304 €/m² dans un échantillon dit « fiable »
**Preuve :** bilan BP0571 — « médiane 4 184 ; **min 1 304** / max 5 488 €/m² ». 1 304 €/m²
pour un « appartement » est suspect (parking vendu en lot ? vente familiale ?). Le filtre
Tukey + plancher 600 €/m² le laisse passer. N'altère pas la médiane mais entame la confiance.
**Correction :** afficher le n après nettoyage et resserrer le plancher, ou signaler la
dispersion quand min/médiane < 0,4.

## J7 — « 2 couches non vérifiées » anxiogène sans dire lesquelles (en tête de fiche)
**Preuve :** fiche BP0571 (`02_fiche_opportunite.png`) : bandeau « **2 couches non vérifiées
à ce jour — verdict partiel** » très haut, avant même le résumé, sans nommer les couches
(il faut descendre tout en bas). Pour un prospect, « verdict partiel » en gros dès le départ
sème le doute plus qu'il ne rassure.
**Correction :** nommer les 2 couches inline (ex. « ABF, ENS non vérifiés ») et adoucir la
formulation, ou descendre le bandeau sous le résumé.

## J8 — Jargon interne exposé + fonctionnalité « Veille (offre C) » vide dans l'UI
**Preuve :** capture `01_landing.png`, bas de la barre latérale : « **VEILLE (OFFRE C) —
SIGNAUX** » suivi d'un « — » (aucun signal). Deux problèmes : (a) le vocabulaire interne
« offre B / offre C » du brief **fuit dans l'interface client** (« offre C » ne veut rien
dire pour un promoteur) ; (b) on **expose une fonctionnalité vide** en permanence → effet
« inachevé / coquille ».
**Correction :** retirer « offre B/C » du front (parler de « Veille » tout court) et masquer
le bloc tant qu'il n'y a pas de signal (ou afficher un état vide pédagogique).

## J9 — Le bucket « à creuser » est noyé sous des parcelles < 250 m²
**Preuve :** les 10 premières « à creuser » par score sont **toutes** des « surface réduite
**106 à 248 m²** — sous le seuil d'un programme » (mesuré). Un promoteur qui clique sur le
KPI « à creuser » (1 778 parcelles) pour chercher des pistes tombe d'abord sur des
micro-parcelles. La nuance « à creuser » perd son sens si elle est dominée par du trop-petit.
**Correction :** soit déclasser plus bas les 100–250 m² (ils n'ont pas d'intérêt promoteur),
soit les regrouper / les sortir du tri par score, soit les marquer distinctement.

---

# 🔵 COSMÉTIQUE

- **B1 — Démo guidée inaccessible sur mobile :** le bouton « 🎬 Démo guidée » est dans
  `.side-nav`, masquée en < 900 px (`07_mobile_carte.png`). Le panneau « État de la démo »
  n'est donc pas atteignable depuis un téléphone. (Mineur : la démo se fait sur portable.)
- **B2 — Badge « Opportunité vérifiée » + sous-texte long** sous le verdict : le sous-texte
  « vérifiée sur les couches disponibles (PLU, PPR, littoral, forêt, SAR partiel)… » est
  honnête mais lourd visuellement en tête de fiche.
- **B3 — Kanban : défilement horizontal** des colonnes sur écran moyen (8 colonnes) ;
  la dernière colonne « Abandonnée » est hors champ sans scroll.
- **B4 — Carte : zones sombres** = parcelles non-opportunité quasi invisibles ; un promoteur
  pourrait croire que « la commune est presque vide » alors que c'est un choix de mise en
  avant (radar). Acceptable, mais à expliquer en démo.
- **B5 — Les faux positifs ne sont visibles que sur la carte**, jamais dans la liste latérale
  (`renderList` exclut `exclue` et `faux_positif_probable`). Cohérent, mais un sceptique qui
  veut « voir ce que vous écartez » (argument de vente !) doit le chercher au filtre carte.

---

# CE QUE JE PEUX AFFIRMER vs CE QU'UN PROMOTEUR DOIT VALIDER

| J'affirme (mesuré) | Le promoteur doit valider (métier) |
|---|---|
| BP0571 est bâtie (orthophoto + contour) ; 47 % des opps ≥30 % bâti (OSM) | Si telle parcelle bâtie est une vraie opération de renouvellement |
| 63 % des opps sans voirie <3 m (161 sans <6 m) | Si l'accès réel existe par servitude non cartographiée |
| Coût construction défaut 1 800–2 200 €/m² habitable | Le bon ratio €/m² SHON pour SES projets à La Réunion |
| Charge foncière BP0571 : −0,2 à 8,1 M€ (médiane 5,2) | Si 566 €/m² terrain colle au prix vendeur réel |
| Prix DVF 4 184 €/m² fiable, 60 ventes, neuf/ancien séparés | Si le comparable « appartement collectif » est le bon |
| `/parcels/%00` → 500 ; `/discover` ~2 s ; écran noir si CDN KO | — |
| Pas de propriétaire, 1 commune, vs Kel Foncier (national + propriétaire) | La valeur d'usage pour SON équipe |

---

# PERFORMANCE (mesurée, serveur local chaud)

| Action | Temps | Verdict |
|---|---|---|
| Fiche core (cache chaud) | **56–64 ms** | excellent |
| Fiche core (enrichment FROID) | ~70 ms | excellent (enrichment lazy) |
| Bloc enrichment FROID (ALTI+GPU) | **~5,3 s** en arrière-plan | acceptable (loader visible, non bloquant) |
| Export HTML | 54–57 ms | excellent |
| Carte geojson (3 000 parcelles) | 160–227 ms | bon |
| `/discover?limit=50` | **1 841–1 992 ms** | 🟡 lent (cf. J1) |
| `/demo-status` | 233–270 ms | bon |

La performance n'est PAS le problème de LA BUSE — la crédibilité métier l'est.

---

# UI / UX — SYNTHÈSE

**Le bon :** direction artistique premium et cohérente (radar sombre + fiche éditoriale
ivoire, serif Fraunces) ; fiche très lisible, double score, résumé « business » clair ;
mobile soigné (fiche pleinement lisible, `07c_mobile_fiche.png`) ; panneau « Démo guidée »
+ « État de la démo » rassurant ; honnêteté du discours partout. **C'est visuellement au
niveau d'un produit payant.**

**Le mauvais :** la qualité visuelle **survend** la fiabilité réelle des données (effet
« joli donc on y croit ») → R1 n'en est que plus dangereux ; « verdict partiel » anxiogène
en tête (J7) ; liste tronquée à 80 (J2) ; bandeau assemblage non discriminant (J3) ; positifs
affichés sur les faux positifs (J4) ; saisie contact par prompt (J5).

---

# 📊 NOTE — « Vendable aujourd'hui à un promoteur ? »

## **3,5 / 10**

- **Démontrable** (joli, rapide, scénario rodé) : ~7/10.
- **Crédible auprès d'un promoteur qui connaît le terrain** : **2/10** — la première
  parcelle vedette est une résidence existante, ~la moitié des « opportunités » sont
  bâties, le tiers potentiellement enclavé, et le bilan est optimiste par défaut.
- **Vendable en pilote payant aujourd'hui** : **non** sans corriger R1. On vendrait une
  promesse (« pré-tri fiable ») que le produit ne tient pas — et le premier promoteur
  averti le verra en ouvrant 3 fiches.

La note n'est pas basse parce que le produit est mauvais — il est **bien construit et
honnête**. Elle est basse parce que **le cœur de la promesse (« voici des opportunités
foncières ») est faux pour ~la moitié des cas**, et que ça se voit à l'œil nu sur la
parcelle de démo.

---

# 🎯 LES 5 CHANTIERS PRIORITAIRES (dans l'ordre)

1. **Détecter le bâti existant (R1)** — ingérer BD TOPO « bâtiment », calculer la couverture
   bâtie, déclasser/flaguer « déjà bâti », et **changer la parcelle vedette de démo** pour
   une vacante (BK0023). **Sans ça, rien d'autre ne compte.** Refaire ensuite le pack
   commercial autour d'une vraie parcelle nue.
2. **Flaguer l'enclavement (O1)** — un signal « accès non identifié » dans la vigilance.
   Couplé à R1, ça transforme « 814 opportunités douteuses » en « ~quelques dizaines de
   vraies pistes nues et accessibles » — beaucoup plus crédible, même si le chiffre est plus
   petit.
3. **Assainir le bilan (O2+O3)** — coûts Réunion réalistes sur surface de plancher, médiane
   mise en avant, fourchette resserrée, bas borné à 0. Un bilan prudent inspire plus
   confiance qu'un bilan flatteur.
4. **Vendoriser Leaflet + dégrader proprement (R2)** — pour qu'aucun réseau client ne donne
   un écran noir ; et corriger la démo pipeline (O4) + le 500 sur `%00` (O5).
5. **Décider le positionnement face à Kel Foncier (O7)** — assumer « pré-tri **local,
   honnête et traçable**, sans prétention propriétaire ni couverture nationale », et le dire
   au client ; ne jamais se présenter comme un équivalent Kel Foncier.

---

*Audit en lecture seule. Données analysées : 3 000 parcelles Saint-Paul, 814 opportunités,
8 765 bâtiments OSM, orthophotos IGN. 19 captures dans `audit_shots/`. Aucune correction
appliquée — à trier et corriger par lots.*
