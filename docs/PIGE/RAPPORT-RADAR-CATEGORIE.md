# RAPPORT — RADAR : LA CATÉGORIE

Branche `feat/radar-categorie` (base `f3f75d24` = main + mandat). Refonte de l'interface CLIENT du
Radar en catégorie de premier niveau ; le back (`pige/*`, `client.py`) est réutilisé, pas réécrit.
Référence : `docs/PIGE/maquette-radar-v2.html` (écrans 1/2/3), suivie fidèlement. Captures :
`docs/PIGE/captures/radar-cat-*` et `radar-veille-*` / `radar-marche-*`.

## Findings
- **RC-001** — la maquette `docs/PIGE/maquette-radar-v2.html`, désignée LA référence par le mandat,
  n'était **pas committée** : le commit du mandat (`f3f75d24`, « mandat RADAR categorie + maquette v2
  validee ») ne portait que le `.md`. Le fichier existait en local non suivi dans le worktree
  `labuse-merge` ; récupéré et committé dans T1-T3. (Aucun blocage — le fichier a été retrouvé.)
- **RC-002** — des 6 tuiles « Étudier ce bien », 5 avaient déjà une entrée parcelle directe
  (`calcPrefill` pour Étudier/Calculette, `parcelPrefill` pour Remonter le temps, `selectedIdu` pour
  Taxe et Pièges & risques). **Solaire** n'en avait aucune → ajout d'un `solairePrefill` minimal au
  patron établi (consommé par `ProspectionSolaire` au montage, mode ensoleillement). Pas de bricolage,
  patron identique aux deux prefills existants.

## T1 — La promotion en catégorie
**Demandé** : Radar dans le rail entre Recherche et Veille (icône radar), hors du menu Outils, route
plein écran (rail · panneau 434px · carte), wording de la maquette, bug « deux catégories ouvertes »
valable pour Radar.
**Traité** : `view: 'radar'` (store) — catégorie plein écran, montée dans `App`. Entrée dans le rail
principal (`Rail.tsx`, ZONES) juste après « Cartes » avec l'icône radar de la maquette (adaptée au
viewBox 20) — le rail réel n'a pas d'entrée « Recherche » distincte ; placement le plus fidèle à
l'intention (catégorie de 1er niveau, adjacente à la Veille du bas). Radar **sort du menu Outils** :
retiré de `registry.ts` et du MODMAP de `ModulePanel` ; l'ancien `RadarClient.tsx` est supprimé.
Deep-link `#radar=1` (rétro-compat `#m=radar`) + survie au reload (sérialisation). Bug « deux
catégories » : `setView`/`openRadar` ferment la Veille et les overlays ; réciproquement
`toggleSurveillance`/`toggleOutils` ferment Radar (une seule catégorie ouverte). Wording maquette
partout (« Les biens en vente — Repérés sur les portails… Des faits et un lien — jamais le contenu de
l'annonce »), plus aucun « vus par Victor ».

## T2 — L'écran (maquette écran 1)
**Demandé** : filtres commune/type/prix/surface + segments Tous-Rattachés et Tous-Particulier-Pro,
bug commune corrigé, retrait encart veille, compteur + tri, cartes du listing de la maquette, carte
pins rattachés seuls + légende + hint, état vide écran 3.
**Traité** : filtres exacts de la maquette. **BUG commune corrigé** — le sélecteur listait seulement
les communes des biens déjà chargés ; il liste désormais les **24 communes** (source unique
`CP_COMMUNES`) + « Toute l'île » et filtre réellement (vérifié : Les Avirons → 2 biens). Segments à
deux/trois positions (« Non rattaché » disparaît). Encart veille RETIRÉ (la veille a sa catégorie, T4).
Compteur « N biens · N sur la carte », tri (Plus récentes / Prix croissant / Prix décroissant /
Ancienneté / Baisses). Cartes du listing à la structure verrouillée de la maquette (titre mono
TYPE·Commune, prix à droite, specs, pied pastille « Sur la carte »/« Non localisé — voir l'annonce »
+ badges baisse/vente-longue + méta portail·jours, liseré vert de sélection). Carte : pins rattachés
seuls (couleur par statut — mint en vente, amber en vente longue), légende + hint de la maquette
(overlays `MapView` gated `view==='radar'`). État vide « Le Radar démarre » (écran 3).

## T3 — La fiche d'un bien (maquette écran 2)
**Demandé** : ordre exact — en-tête, prix + baisse + sparkline, « Voir l'annonce » sous le prix, LES
FAITS étiquetés, PARCELLE RATTACHÉE, ÉTUDIER CE BIEN (6 tuiles pré-remplies), Signaler + note ; un
bien non rattaché n'a ni outils ni parcelle.
**Traité** : fiche en overlay (398px à droite desktop) dans l'ordre exact de la maquette. « Voir
l'annonce sur [portail] ↗ » juste sous le prix, visible sans scroller. LES FAITS étiquetés
Sourcé/Estimé/Absent (l'étiquette suit le champ). PARCELLE RATTACHÉE → « Ouvrir la fiche parcelle → »
(bascule sur 'cartes' + sélectionne). ÉTUDIER CE BIEN : 6 tuiles pré-remplies avec la parcelle
rattachée (Étudier le bien, Remonter le temps, Calculette foncière, Taxe d'aménagement, Pièges &
risques, Solaire — mappings vérifiés, cf. RC-002). Bien NON rattaché : fiche qui s'arrête aux faits
+ bouton portail, **sans** section outils ni bloc parcelle. Réconciliation T2/T3 : un clic de listing
ouvre toujours la fiche ; pour un non-localisé, le seul chemin sortant est le bouton portail (logué).
Zéro mauve, couleurs source unique (mint/amber).

## T4 — La veille à deux portes
**Demandé** : la catégorie Veille s'ouvre sur un écran d'entrée à deux chemins (patron Communes R3) :
Veille interne (le foncier, inchangé) · Veille externe (les annonces Radar). Veilles existantes et
digests P4 intacts (tests).
**Traité** : `SurveillancePanel` s'ouvre sur deux portes door-hot. « Le foncier » = l'écran existant
INCHANGÉ (boucle + volets Parcelles/Secteurs/Critères, extrait dans `VeilleInterne`). « Les annonces »
= créer + gérer ses veilles Radar (commune/type/prix/surface terrain/particuliers + événements
nouvelle·baisse·retour), liste + suppression. Store `surveillancePorte` (accueil/interne/externe) :
le clic rail ouvre l'accueil, les deep-links de notif ciblent la porte interne (aucun lien cassé).
Back : le **prix** rejoint les critères de veille (T4 le liste) — extension mineure de `VeilleIn` +
`veille.matche` ; les veilles existantes sans prix restent valides. **Non-régression P4 : 79 tests
pige/veille/digest verts** (digests + alertes intacts, anti-portail vert).

## T5 — Le Marché déménage
**Demandé** : l'onglet Marché disparaît du Radar ; ses stats (`pige/marche.py`) s'installent dans
Communes → Évolution, en section « Marché des annonces (Radar) » sous les stats existantes.
**Traité** : l'onglet Marché a quitté le Radar (retiré de l'écran en T2). Le composant `RadarMarche`
(corrigé RETOURS-1 R9 : sort du chargement infini, état d'erreur honnête) est monté dans `M18`
(Évolution) sous les séries (ancien bâti · terrain nu · permis), en section « Marché des annonces
(Radar) » : agrégats par commune, le n partout, « échantillon insuffisant » sous 5, état de démarrage
digne. `pige/marche.py` réutilisé tel quel.

## T6 — Mobile et recette
**Demandé** : mobile 390 utilisable (listing plein écran, carte accessible, fiche plein écran, dire le
choix) ; recette [RADAR-TEST] purgée SQL exerçant tous les cas ; captures 390 + 1440.
**Traité (mobile)** : sur ≤ 767px, **une seule vue à la fois, plein écran** (patron tiroir P3) —
listing (défaut), carte (bouton « Voir la carte »/« Voir la liste »), fiche du bien (plein écran).
`RadarView` monte lui-même `MapView` pour piloter ce responsive ; la carte est montée/démontée sur
mobile (évite un canvas maplibre 0×0). Desktop inchangé.
**Traité (recette)** : `qa/radar/seed_recette.sql` — jeu [RADAR-TEST] (bien_id ≥ 900000, purgeable) :
rattaché Sourcé, Estimé, non rattaché, 4 types, baisse, vente longue, particulier/pro, 2 communes, IDU
réels. `qa/radar_categorie_recette.mjs` — **19 assertions VERTES** : filtre commune réel, tri baisses,
fiche rattachée + 6 tuiles + parcelle + portail + baisse, fiche non rattachée SANS outils ni parcelle,
état vide filtré, veille externe créée qui matche puis supprimée, veille interne intacte, Radar hors
du menu Outils. `qa/radar/purge_recette.sql` purge les 5 tables `pige_*` + les veilles radar de test.
**[RADAR-TEST] purgés — vérifié SQL : 0 bien (bien_id ≥ 900000), 0 veille radar.**
**Captures (15, 1440 + 390)** : écran, carte mobile, fiche (rattachée/estimée/mobile), filtre commune,
veille 2 portes (+ externe / interne), Évolution + section Radar, état de démarrage (desktop/mobile).

## Gardes
- tsc 0 · build OK · anti-portail P0 vert (10/10) · 79 tests pige/veille/digest verts (P4 intact).
- Zéro mauve côté client (seul le commentaire de doctrine le nomme). Couleurs source unique
  (mint `#4ADE80` canonique / amber via tokens ; le `#4ADE80` en dur de la sparkline est le vert de
  marque, comme les pins de `MapView`).
- Golden : 120 FAIL PRÉ-EXISTANTS (ancre `q_v10_m129` vs run servi `q_v11_m137`, branch-indépendant ;
  le diff ne touche AUCUN fichier de scoring — pige/* et front only) ; GARDE-RUN OK.
- Aucune donnée de test résiduelle (seed + veilles de test purgés, vérifié SQL).
- Suite pytest branche vs base (worktree) — chiffres au compte-rendu.
