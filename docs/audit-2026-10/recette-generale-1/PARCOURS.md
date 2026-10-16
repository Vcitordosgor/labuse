# PARCOURS — Recette générale 1 (16/10/2026)

Chaque écran : OK ou anomalie (→ voir ANOMALIES.md pour le détail).
Run servi : q_v18. Backend :8798, Frontend :5998 (/socle/). Lecture seule.

## Famille 1 — Carte

Testée en DESKTOP (1440×900). MOBILE (390px) : l'app entière est **volontairement bloquée**
par un écran-barrage « LABUSE est disponible sur ordinateur » (`main.tsx` → `EcranOrdinateur`,
décision CHARGEMENT-1 point 6) — aucun panneau/carte sur mobile, donc les sous-contrôles mobiles
(panneaux utilisables, texte coupé) sont SANS OBJET. Le barrage lui-même est propre : 0
débordement, 0 erreur, même via deep-link `#idu=…`. → informatif, voir A-01-3.

Sur l'ensemble de la famille : **0 erreur console JS, 0 réponse HTTP 4xx/5xx** (hors bruit connu).

### 1. Chargement initial
- Desktop `aller('')` : **OK** — carte Réunion + 24 communes, panneau gauche (COUCHES/FILTRES +
  « Par où commencer »), barre haute (recherche, Toute l'île, Sombre, 3D, Signaler). Cold start
  ~9 s (dev server froid), 0 erreur. Capture `001_desktop-chargement-initial.png`.
- Mobile : **OK (barrage attendu)** — `001_mobile-chargement-initial.png`, load ~0,8 s, 0 débordement.

### 2. Couches — **OK** (60 couches, toutes 200, 0 erreur)
13 catégories : REPÈRES · URBANISME · RISQUES · ENVIRONNEMENT · FONCIER · ÉNERGIE · RÉSEAUX ·
TRANSPORT · DISPOSITIFS · PATRIMOINE · ÉQUIPEMENTS · MARCHÉ · FOND DE PLAN.
Les 60 couches énumérées et activées une par une — chacune déclenche ses tuiles/`couches-info`
en **200**, rendu visuel qui change, pas de spinner infini, pas d'erreur :
Limites communes · Limites parcelles (contour cadastral) · Zonage PLU par parcelle (calibré) ·
Limites officielles du PLU (GPU) · 50 pas géométriques · Artificialisation (OCS GE) · DPU ·
Servitudes d'utilité publique (SUP) · Emplacements réservés (ER) · Espaces boisés classés (EBC) ·
TRI zones inondables · Aléa inondation · Aléa mouvement de terrain · CASIAS · Cartes de bruit ·
Classement sonore · PEB · Systèmes d'endiguement · Érosion côtière · Ravines et reculs (DPF) ·
PPR multirisque · ICPE · SIS · Cavités souterraines · Courbes de niveau · Parc national ·
Bassins versants · Mesures compensatoires (ERC) · ZNIEFF · Espaces naturels protégés · Zones
humides · Forêts publiques · SAR proxy · Foncier agricole (RPG/SAFER) · Zones d'activité ·
Friches (Cartofriches) · EnR interdites hors toiture (APER) · Contraintes EnR près habitations ·
HTA · HTB · Pylônes · Postes de transformation · TCSP · Axes structurants · Transport public ·
Téléphérique · Pôles d'échange · ZFANG · FRR · TVA réduite primo-accédant · QPV · ANRU/NPNRU ·
Cimetières · Périmètres ABF/monuments · Équipements INSEE (BPE) · Équipements/services (OSM) ·
Prix du logement neuf (VEFA) · Barrages/ponts/dalles · Murs de soutènement.
Captures représentatives : `002_couche-courbes-niveau.png` (contours rendus), `001_couche-50pas`,
`003_couche-zonage-plu`, `004_couche-transport`.

### 3. Filtres — **OK** (compteur SQL-exact qui bouge, filtre combiné OK)
Facettes : Communes (24 codes INSEE + Ajouter/Retirer tout) · Surface min/max (m²) ·
Familles de zone U/A/N/AU (avec compte parcelles+zones par famille) · Terrain nu/bâti ·
AFFINER LA RECHERCHE (repli : Sans copropriété, Saturé, Renforcée/Standard/Totalité/En partie/
Hors dispositif ZFANG-FRR, Détenu par société, Procédure collective, Permis actif/abandonné,
Friche recensée, Sortie de défisc, Succession, hauteur/emprise) · PROPRIÉTAIRE (denom/SIREN/
forme/APE) · Réinitialiser.
- Commune (97410 Saint-Pierre) : compte 432 350 → **42 435** (req `communes=Saint-Pierre`) ✓
- Famille A : → 42 435 ; + Terrain nu : → 25 014 ✓
- Surface min 5000 : compte → **40 820**, égal à l'`compte` renvoyé par `/filtre?surface_min=5000`
  (vérifié API) ✓  Capture `filtre-surface-final`.
- Combiné (commune + famille + terrain nu) : compteur décroît de façon cohérente ✓
- Réinitialiser : revient à 432 350 ✓
- Note : le compteur est **débattu ~400 ms + latence back (1–4 s)** → il peut paraître « figé »
  quelques secondes après un clic ; ce n'est pas un bug (vérifié : la requête part, la réponse
  revient, le chiffre se met à jour). Captures `001_filtres-panneau-ouvert`, `filtre-combines-applique`.

### 4. Recherche — **OK** (4 modes + vide + absurde propres)
- IDU `97401000AC0428` → résultat PARCELLE « AC 428 — Les Avirons · 8 313 m² » ✓ (`001_search-idu`)
- Adresse « Saint-Denis » → rues (Rue Foch…), LIEU-DIT, PROPRIÉTAIRE catégorisés ✓ (`search-adresse`)
- Propriétaire « SCI » → SCI OMEGA (26 parcelles), SCI SELATAN INDAH… ✓ (`search-proprietaire`)
- Absurde « zzzqwerty » → dropdown ne montre que les communes-raccourcis (pas de faux résultat) ;
  sur **Entrée**, toast honnête « Aucun résultat (IDU, SIREN, propriétaire ou adresse) pour
  « zzzqwerty » » ✓ (`search-absurde`, `search-absurde-enter`). Voir A-01-1 (cosmétique : pas de
  message « aucun résultat » dans le dropdown live, seulement au submit).
- Vide → aucun dropdown, pas de plantage ✓

### 5. Zoom — **OK**
- Île entière `001_zoom-0-ile-entiere` → zoom molette progressif : tuiles chargent à chaque niveau
  (105 tuiles, 0 erreur). `zoom-1-intermediaire`, `zoom-2-parcelle`.
- Clic sur une parcelle → **fiche s'ouvre à droite** (97401000AC0428 : surface, zone N, pente,
  sections Identité/Terrain/Bâti/Urbanisme/Risques, « Demander à LABUSE ») ✓ (`clic-parcelle-fiche`).

### 6. Boutons de la carte — **OK**
- « Toute l'île » : sélecteur de vue → liste des 24 communes (code INSEE + « voir la fiche → ») ;
  choisir Saint-Pierre recentre la carte + pose le contexte commune (bouton devient « Fiche
  commune ») ✓ (`toute-ile-menu`, `vue-commune-saint-pierre`).
- « Sombre » : en fait un **sélecteur de fond de plan** (Sombre / Plan IGN / Ortho IGN / Ortho
  Express 2025 / SCAN 50 1950 / orthos historiques 1950-65, 2000-05, 2006-10, 2011-15) ; le fond
  change réellement (bascule vérifiée vers Plan IGN) ✓ (`fond-de-plan-menu`, `fond-de-plan-change`).
- « 3D » : bascule active (bouton passe en vert `bg-mint`, panneau relief apparaît) ✓
  (`3d-avant`, `3d-apres`).

### 7. « Par où commencer » — **OK** (4 portes bien câblées, `LeftPanel.tsx:333-343`)
- Explorer la carte → masque l'accueil, ouvre le plan de travail carte (FILTRES) ✓ (`porte-explorer-la-carte`)
- Suivre le marché — Radar → `#f=1&radar=1` (vue Radar) ✓
- Demander au Copilote → vue Copilote ✓ (`porte-demander-au-copilote`)
- Ouvrir un outil → ouvre le tiroir Outils (16 outils) ✓ (`porte-ouvrir-un-outil`)

### Note informative (pas une anomalie bloquante)
Compteur « total foncier » : la barre « Voir les N parcelles » oscille entre **433 229**
(`/accueil/chiffres`, parc vivant) et **432 350** (`/filtre?limit=0`, base scorée q_v18) — écart
879. Voir A-01-2 (cosmétique).

## Famille 2 — Fiche parcelle
Méthode : chaque témoin ouvert via `#idu=<IDU>` + reload (SPA : le hash seul ne remonte pas la
fiche). Les 11 tiroirs (Identité, Terrain, Bâti · Urbanisme, Risques, Réseaux · Fiscalité,
Marché, Quartier · Potentiel, Simulation) sont un ACCORDÉON EXCLUSIF (`RefDrawer`,
`primitives.tsx:87`, `aria-expanded`, `acc.openId`) : ouverts UN PAR UN, contenu `.t-open` lu.
Le verdict/bande (« Analyse incomplète », « À étudier »…) n'apparaît qu'APRÈS clic « Demander à
LABUSE » (`verdictRevele`, Fiche.tsx:1058) — ce bouton révèle la carte en place, il NE navigue
pas (normal). **20/20 témoins : fiche ouverte à droite, 0 erreur console, 0 erreur réseau,
chargement 4–9 s (1ʳᵉ nav froide ~8 s), les 11 tiroirs se déplient, « Poser une question »
ouvre l'AskBar inline, « Demander à LABUSE » révèle la bande.** 0 ligne vide muette. 1 seule
anomalie (cosmétique, A-02-1).

- **97415000DT0397** (bizone, Saint-Paul) — **OK**. Urbanisme : « Parcelle à cheval sur 2 zones
  du PLU » U6c 73 % / Ncor 27 % (= API 72,8/27,1) ; verdict « À étudier · Signal faible » ;
  SDP 1 635 m² R+1. Risques : PPR zone rouge/bleue. (`003_97415000DT0397.png`)
- **97401000AC0428** (bizone variante N, Les Avirons — IDU 97401, note dit « Saint-Benoit » à
  tort) — **OK**. Zone Nr naturelle, aléa rédhibitoire 9 vigilances, SDP RESTANTE « — zone non
  constructible ». Bizone non constructible rendu honnêtement. (`005_97401000AC0428.png`)
- **97415000CY1134** (zone rouge partielle PPR, Saint-Paul) — **OK**. Risques : « PPR — zone
  rouge 35 % · zone bleue 62 % » ; Potentiel : « Pas de SDP résiduelle exploitable, R+0 ». Zone
  U2d calibrée mais capacité réduite à 0 par le PPR — cohérent. (`007_97415000CY1134.png`)
- **97415000CH0065** (Hors classement NC, Saint-Paul) — **OK**. Après « Demander à LABUSE » :
  bande « Analyse incomplète — zone non résolue » (= API `analyse_labuse.bande=NC`). Pas de
  score faux. La faisabilité affiche zone A agricole « Construction neuve non autorisée en A »
  (honnête). (`009_97415000CH0065.png`, `analyse-revelee`)
- **97411000AY0015** (emprise saturée 19569 %, Saint-Denis) — **OK**. Bâti : emprise 2 482 m² /
  6 963 m² « Parcelle déjà bâtie probable » ; Potentiel : « Pas de SDP résiduelle exploitable ».
  AUCUN chiffre absurde (le 19569 % interne n'est pas servi tel quel). (`011_97411000AY0015.png`)
- **97411000IO0059** (>2 ha, Saint-Denis) — **OK**. Surface 6,40 ha ; SDP restante 25 427 m²
  R+0 — capacité à l'échelle du terrain. 0 débordement. (`lot2`)
- **97416000IE0438** (disparue du cadastre, Saint-Pierre) — **OK (bien géré)**. L'UI N'ouvre PAS
  de fiche active : elle affiche le garde « Parcelle disparue du cadastre (version du
  2026-09-01). Remplacée par 97416000IE2074 (55 %) / IE2075 (45 %) » (Fiche.tsx:567,
  `/parcels` renvoie `cadastre_disparue`). L'anomalie redoutée (fiche normale sans avertissement)
  N'A PAS LIEU côté app, même si `/modules/faisabilite` sert encore une capacité.
  (`001_97416000IE0438-disparue.png`)
- **97416000EW0446** (propriétaire société, Saint-Pierre) — **OK**. Identité : « DECORASUD SA
  propriétaire depuis 2021 », SIREN 538897976, « Personne morale — fichier DGFiP », BODACC aucune
  procédure. (`lot2`)
- **97415000BW1877** (sans vente, Saint-Paul) — **OK**. Marché affiche l'agrégat DVF secteur
  (terrain nu 244 €/m², 68 ventes) ; ne fabrique AUCUNE vente sur la parcelle, pas de vide muet.
  (`lot2`)
- **97403000AP2099** (sans vente, Entre-Deux) — **OK**. Marché secteur (190 €/m², 25 ventes,
  tendance hausse) ; idem, honnête. (`lot2`)
- **97424000AE1040** (Hauts + bizone, Cilaos) — **OK**. Terrain : pente/exposition RGE ALTI, pas
  de plantage ; Urbanisme : « à cheval Ub 53 % / Uah 47 % » avec articles cités. (`lot3`)
- **97424000AI1980** (Hauts simple, Cilaos) — **OK**. Zone Ub calibrée, fiche complète, aucun
  plantage en altitude. (`lot3`)
- **97410000AE0144** (Saint-Benoît non calibré) — **OK**. Zone Ub, verdict R+2 ~2-3 logts ;
  provenance mixte explicite (steps « calibrage validé » pour emprise/reculs, « estimation
  générique (PLU non outillé) » pour les niveaux) ; marqueur « Estimation » présent ; le détail
  « Étudier quand même » montre les badges de provenance (4 estimé / 12 sourcé). Le chiffre
  n'est PAS présenté comme pleinement sourcé. (`noncalibre`, `faisabilite-detail`)
- **97413000DE1451** (mixité sociale, Saint-Leu) — **OK**. « MIXITÉ SOCIALE (LLS) — Quota 20 %
  logement social » avec citation intégrale de l'article UA2 (p.19, seuil 600 m²). (`lot3`)
- **97417000BD0967** (Saint-Philippe RNU) — **OK fond / A-02-1 forme**. Bannière RNU ⚠ « Commune
  au règlement national d'urbanisme — pas de PLU local » (`data-rnu-banner`) ; Urbanisme : « Zone :
  Non publié au GPU », « Aucun PLU — RNU » ; Potentiel : « Pas de SDP résiduelle ». Pas d'écran
  vide/erreur. SEUL défaut : la tuile « Non publié au GPU » est tronquée par ellipsis (A-02-1,
  cosmétique). (`001_97417000BD0967-rnu-banner.png`, `deb-gpu`)
- **97422000BX1106** (saine, Le Tampon) — **OK**. SDP 582 m² R+6 (= API). AskBar + porte
  « Calculette foncière » (hash `m=calculette-fonciere&idu=…`) réagissent. (`lot4`)
- **97411000AT0427** (saine, Saint-Denis) — **OK**. (`lot4`)
- **97414000DL0765** (saine, Saint-Louis) — **OK**. (`lot4`)
- **97412000BM1315** (saine, Saint-Joseph) — **OK**. (`lot4`)
- **97407000AS0421** (saine + société, Le Port) — **OK**. Identité « SOCIETE ANONYME
  D'HABITATIONS A LOYER MODERE DE LA REUNION » SIREN 310895172 (nom long tronqué par ellipsis
  dans la valeur d'en-tête repliée, complet dans le tiroir — même mécanique que A-02-1). (`lot4`)

### Boutons de la fiche — OK
- « Demander à LABUSE » : révèle la carte Analyse (bande + cause) EN PLACE (ne navigue pas,
  comportement voulu, Fiche.tsx:1058-1074). Révèle « Analyse incomplète » pour les NC.
- « Poser une question » : ouvre l'AskBar Copilote inline (placeholder « Expliquez un point… »).
- Portes outil depuis Simulation : « Calculette foncière » → `#m=calculette-fonciere&idu=…` (sur
  la parcelle) ; « Densifier l'existant » / « Ouvrir le Gabarit » présentes dans Potentiel.
  (destination vérifiée sans entrer dans l'outil = Famille Outils.)

## Famille 3 — Fiche commune

Testé en DESKTOP uniquement (1440×900), visiteur anonyme, run servi q_v18.
Les 24 communes passées au harnais (`frontend/qa-recette/commune_sweep.mjs` + `_commune_lib.mjs`),
puis inspection détaillée des 6 représentatives. API de référence comparée via
`/communes/<nom>/contexte` (`frontend/qa-recette/apisweep` → `/tmp/apisweep.py`).

### Chemin d'ouverture de la fiche (geste réel)
Le deep-link `#c=<Commune>` (= `lien.commune`) NE pose QUE le filtre commune (`setCommune`) —
il **n'ouvre pas** la fiche. La fiche (ContextePanel) s'ouvre par `setContexteCommune`. Le vrai
geste client : bouton sélecteur commune en haut (`data-commune-select`) → menu déroulant →
bouton « voir la fiche → » de la ligne (`data-fiche-commune`). Chemin vérifié fonctionnel sur
Saint-Denis. Le harnais pilote ce geste (repli `window.__labuse.setContexteCommune`). Ce n'est
pas une anomalie (le `#c=` est un filtre partageable, pas un lien de fiche) mais c'est un piège
documenté pour les testeurs : `App.tsx:358` lit `c` → `setCommune` ; la fiche n'a pas de deep-link.

### Verdict par commune (24/24)

| # | Commune | Fiche ouvre | Cartes | Bandeau | Tuiles | Temps (geste→affichage) | Verdict |
|---|---------|-------------|--------|---------|--------|--------------------------|---------|
| 1 | Bras-Panon | OK | 10/10 | plausible | 4/4 | ~10 s | OK (console A-03-1, débord. A-03-3) |
| 2 | Cilaos (Hauts) | OK | 10/10 | plausible (tendance « — » : honnête, <seuil DVF) | 4/4 | ~8 s | OK |
| 3 | Entre-Deux | OK | 10/10 | plausible | 4/4 | ~7 s | OK (console A-03-1) |
| 4 | L'Étang-Salé | OK | 10/10 | plausible | 4/4 | ~8 s | OK (console A-03-1) |
| 5 | La Plaine-des-Palmistes | OK | 10/10 | plausible | 4/4 | ~20 s | OK (lent A-03-2) |
| 6 | La Possession | OK | 10/10 | plausible | 4/4 | ~10 s | OK (console A-03-1) |
| 7 | Le Port | OK | 10/10 | plausible | 4/4 | ~7 s | OK (console A-03-1) |
| 8 | Le Tampon (grande) | OK | 10/10 | plausible | 4/4 | **~46 s** | OK mais LENT (A-03-2) |
| 9 | Les Avirons | OK | 10/10 | plausible | 4/4 | ~11 s | OK |
| 10 | Les Trois-Bassins | OK | 10/10 | plausible (PLU « en révision ») | 4/4 | ~9 s | OK |
| 11 | Petite-Île | OK | 10/10 | plausible (tendance -11,6 %) | 4/4 | ~8 s | OK (débord. A-03-3) |
| 12 | Saint-André | OK | 10/10 | plausible (PLU « en révision ») | 4/4 | ~9 s | OK |
| 13 | Saint-Benoît (non calibré) | OK | 10/10 | plausible | 4/4 | **~45 s** | OK mais LENT (A-03-2) |
| 14 | Saint-Denis (grande) | OK | 10/10 | plausible (155 634 hab.) | 4/4 | ~13–20 s | OK (lent-limite A-03-2) |
| 15 | Saint-Joseph | OK | 10/10 | plausible | 4/4 | ~18 s | OK |
| 16 | Saint-Leu (moyenne) | OK | 10/10 | plausible (PLU « en révision ») | 4/4 | **~33 s** | OK mais LENT (A-03-2) |
| 17 | Saint-Louis | OK | 10/10 | plausible | 4/4 | ~20 s | OK |
| 18 | Saint-Paul (grande) | OK | 10/10 | plausible (108 088 hab., prix 4 278) | 4/4 | **~24 s** | OK mais LENT (A-03-2) |
| 19 | Saint-Philippe (RNU) | OK | 10/10 | plausible (ÉTAT PLU=RNU) | 4/4 | ~9 s | OK — bandeau RNU + « N 100 % » honnêtes |
| 20 | Saint-Pierre (grande) | OK | 10/10 | plausible (85 038 hab.) | 4/4 | ~18 s | OK (débord. A-03-3) |
| 21 | Sainte-Marie | OK | 10/10 | plausible | 4/4 | ~10 s | OK |
| 22 | Sainte-Rose | OK | 10/10 | plausible (tendance « — ») | 4/4 | ~9 s | OK |
| 23 | Sainte-Suzanne | OK | 10/10 | plausible | 4/4 | ~8 s | OK |
| 24 | Salazie (Hauts) | OK | 10/10 | plausible (tendance « — ») | 4/4 | ~14 s | OK |

Les « temps » mesurent geste → bandeau affiché. Sur les 4 grandes (Le Tampon, Saint-Benoît,
Saint-Leu, Saint-Paul) l'API `/contexte` répond en 17–35 s **même à chaud** : cause = table de
cache `commune_contexte_cache` VIDE en recette (0 ligne) → recalcul en direct à chaque appel (A-03-2).

### Détail des points vérifiés (tous OK sauf anomalies listées)
- **Panneau fiche commune** : s'ouvre pour les 24 ; en-tête « FICHE COMMUNE / <nom> » + EPCI + surface. OK.
- **Bandeau 6 chiffres** (Parcelles, Habitants, Permis/an, Prix ancien, Tendance 12 m, État du PLU) :
  valeurs plausibles pour les 24, aucun NaN/null/undefined. « Tendance 12 m = — » sur Cilaos, Salazie,
  Sainte-Rose, Les Trois-Bassins = honnête (sous le seuil de robustesse DVF, pas un faux zéro). OK.
- **10 cartes** (Identité, Population, Prix, Activité/annonces, Permis et rythme, Foncier et rareté,
  Urbanisme, Fiscalité et dispositifs, Risques et contraintes, Équipements) : dépliées une à une
  (accordéon — une seule ouverte à la fois) ; aucune carte vide muette, aucun NaN/undefined/null
  dans le texte des 24 communes. OK.
- **Cas « sans objet » honnêtes** : Saint-Philippe (RNU) → bandeau RNU dédié (« Commune au règlement
  national d'urbanisme — pas de PLU local… ») + carte Urbanisme « N 100 % » (ni U/AU/A). Carte
  « Activité/annonces » affiche « Pas d'annonce repérée… le Radar affine » quand vide. PLH « Aucun
  programme local de l'habitat recensé » quand absent. Tous explicites — OK.
- **Raccourcis / portes « Étudier cette commune »** (PLU, Permis, Étude de zone, Communes) : les 4
  tuiles réagissent et ouvrent le bon outil (`#m=plu`, `#m=permis`, `#m=etude-zone`, `#m=communes`)
  à la maille commune. Vérifié sur Saint-Denis. OK.
- **Cas à surveiller (BRIEF)** : Saint-Philippe (RNU), Cilaos, Salazie (Hauts), Saint-Benoît
  (non calibré) — tous affichent des « sans objet » propres, aucune casse de fiche. OK.
- **Erreurs réseau** : 0 HTTP 4xx/5xx sur les 24. OK.
- **Erreurs console** : 1 warning React récurrent (clé dupliquée) — A-03-1 (non bloquant).
- **Débordement** : 1 span tronqué « PPR · mouvement de terrain · CatNat » (classe `truncate`
  volontaire) — A-03-3 (cosmétique).

## Famille 4 — Outils

Périmètre : le menu « Outils » du rail de gauche affiche **16 outils** (confirmés identiques au
registre `frontend/src/components/outils/registry.ts`, filtre `!hidden`, dans l'ordre fixé par le
mandat). En plus, 2 clés RÉSOLVANTES masquées du menu mais accessibles par deep-link ont été
testées (calculette-fonciere, mon-secteur). DESKTOP uniquement (barrage mobile, acquis Famille 1).

Méthode : chaque outil ouvert seul (`#m=key`), puis sur une parcelle normale
(`#idu=…&m=key`), puis sur un cas limite. **Note technique** : l'app ne lit le hash QU'AU MONTAGE
(App.tsx `useEffect([])`, aucun listener `hashchange`) → pour commuter d'outil en automation il faut
un vrai rechargement (query-buster `?r=N` avant le hash, cf. `qa-recette/_outils_lib.mjs`). Les
VRAIS clics menu (qui passent par `setModule` en React) commutent sans ce contournement — vérifié.

| Outil (clé) | Ouverture seul | Sur parcelle normale | Cas limite | Verdict |
|---|---|---|---|---|
| PLU (`plu`) | OK — Annuaire PLU + « Procédure & changement » | OK (97422000BX1106) | OK (97410000AE0144 non calibré) | **OK** |
| Permis (`permis`) | OK — « 50 808 permis Sitadel » + filtres (récent/dormant…) | — (vue île) | — | **OK** |
| Communes (`communes`) | OK — 4 entrées (Comparateur · Évolution · Annonces Radar · Acquisitions) | — | — | **OK** |
| Scan patrimoine (`patrimoine`) | OK — 2 tuiles (Un propriétaire / Toutes les opérations) | OK : recherche SIDR → `/modules/patrimoine?siren=` 200, « 4 188 parcelles · 402,34 ha » (chiffres = API) | — | **OK** |
| Assemblage (`assemblage`) | OK — saisie parcelles + « Vérifier l'assemblage (0) » | OK (UI de saisie) | OK (disparue 97416000IE0438, pas de casse) | **OK** |
| Comparer (`comparer`) | OK — « Comparer (0/3) » | OK : « + Ajouter la parcelle courante » + saisie IDU+Entrée → 2 chips, bouton « Comparer (2/3) » actif, tableau s'ouvre | — | **OK** |
| Pièges et risques (`risques`) | OK — bandeau + 24 communes | OK (97422000BX1106 : « 3 servitude(s)/contrainte(s) », = API n=3) | OK (97415000CY1134 PPR rouge : « 7 » = 7 CATÉGORIES, regroupement voulu de 9 items dont 3 PPR, cf. blocB.tsx:82-95 ; **vérifié non faux**) | **OK** |
| Étude de zone (`etude-zone`) | OK — rayon 0,5/1/2/5 km + sélecteur d'activité + « Lire la zone » | OK : parcelle + « Lire la zone » → `POST /outils/etude-zone` 200, zone_disponible=true, 11 268 habitants, 312 ha, sections Population/Économie rendues (~4-8 s) | — | **OK** |
| Remonter le temps (`temps`) | OK — comparateur d'orthos 1950-1965 ⇔ Ortho Express 2025 | OK (62 tuiles ortho chargées) | OK (disparue) | **OK** (voir note 404) |
| Faisabilité (`programme`) | OK — 2 entrées (par parcelle / par capacité) | OK (97422000BX1106 : zone Ua, SDP restante 582 m², Potentiel R+6) | OK (97415000CH0065 hors-classement : « SDP restante — zone non constructible », « constructibilité très limitée », pas de NaN) | **OK** |
| Gabarit réglementaire (`gabarit`) | OK | OK (97422000BX1106 : « ZONE D'IMPLANTATION 270 m² ») | OK (97411000AY0015 emprise saturée : « Calcul incomplet — donnée réglementaire manquante / limites non qualifiées », message propre) | **OK** |
| Taxe d'aménagement (`taxe-amenagement`) | OK | OK (97422000BX1106 : terrain 629 m², formulaire surface taxable + barème) | OK (97411000AY0015 : terrain 6 963 m², formulaire servi) | **OK** |
| Prospection solaire (`prospection-solaire`) | OK — 2 métiers (💧 Piscines / ☀️ Ensoleillement) | OK (clic Ensoleillement → mode « cliquez une parcelle » ; prospection carto) | — | **OK** |
| Blocs fonciers (`blocs-fonciers`) | OK — 4 filtres + « Voir les parcelles » | `/modules/blocs` 200 mais `total:0` (table `parcel_blocs` VIDE en recette) ; empty-state honnête affiché | — | **ANOMALIE A-04-1** (gênant, défaut d'environnement/données) |
| Successions à venir (`successions`) | OK — `/modules/successions` 200, « 6 256 parcelles · RNE INPI au 06/10/2026 », liste rendue + filtre Périmètre | — | — | **OK** |
| Courrier propriétaire (`courriers`) | OK — étapes 1 Destinataires / 2 Rédaction (envoi NON déroulé, approfondi Famille 8) | OK (97416000EW0446, flux de préparation réagit) | — | **OK** |
| Calculette foncière (`calculette-fonciere`, masqué) | OK via deep-link — bilan à rebours | OK (97422000BX1106 : SHAB 476 m², prix sortie 4 318 €/m², charge supportable 50 k€ ≈ 79 €/m², confrontation marché 285 €/m²) | — | **OK** |
| Mon secteur (`mon-secteur`, masqué) | OK via deep-link — médiane DVF secteur, pick parcelle | OK (UI d'entrée + fiche) | — | **OK** |

**Note 404 « Remonter le temps »** : à l'ouverture et au survol, des tuiles `/map/tiles/ortho/{année|express}/…`
renvoient 404 (36 observées). Vérifié : sur TERRE les tuiles servent (express/2021/1950 → 200 à
St-Denis/Le Tampon), et l'outil AFFICHE lui-même l'explication « Zones noires : secteurs non couverts
par l'ortho ancienne (mer, limites de mission IGN) — ce n'est pas un défaut de chargement ». Les 404
sont le comportement PAR DESIGN du proxy ortho (aplat mer + trous de couverture WMTS transitoires,
non cachés, cf. `src/labuse/api/ortho_proxy.py:228-262`). **Non compté comme anomalie.**

**Bilan Famille 4** : 17 outils testés OK (16 du menu + comparaison) ; 1 anomalie (A-04-1,
gênant, données non ingérées) sur blocs-fonciers. 0 erreur console JS, 0 erreur réseau 4xx/5xx
imprévue, 0 NaN/undefined/[object Object], 0 spinner infini, 0 panneau vide muet. Tous les cas
limites (hors-classement, emprise saturée, non calibré, disparue) donnent des messages « sans objet »
propres. Captures de référence (résultat de chaque outil) + anomalie dans `captures/04-outils/`.

## Famille 5 — Exports PDF

Test en DESKTOP uniquement, visiteur anonyme (auth désactivée en local). Génération par le
VRAI geste : rail « Docs » → carte du document → porte → `ParcelInput` (IDU + Entrée) →
bouton CTA → le PDF s'ouvre dans un nouvel onglet (blob). Inspection fichier en parallèle via
`curl -L` + `pdftotext`/`pdfinfo` (poppler). Aucun envoi, aucun paiement — on ne fait que
générer et lire des PDF en local. Parcelles témoins : `97422000BX1106` (Le Tampon, R+6, saine),
`97411000AT0427` (Saint-Denis, R+3, saine). Cas limites : `97417000BD0967` (RNU Saint-Philippe),
`97410000AE0144` (Saint-Benoît non calibré), `97415000CH0065` (hors-classement zone A).

**Mapping noms client → endpoint** (découvert via catalogue `components/documents/catalogue.ts`
et openapi) :

| Nom client (brief) | Carte UI | Endpoint | Remarque |
|---|---|---|---|
| Dossier expert | « Dossier » | `GET /dossier/{idu}.pdf` | fiche complète imprimable |
| Étude de faisabilité / Bilan | « Bilan » | `POST /bilan/{idu}/generer` → `GET /bilan/{idu}.pdf?doc_id=` | **account-only (401 anonyme)** |
| Pré-dossier PC | « Pré-dossier PC » | `GET /pre-dossier/{idu}.zip` | zip : CERFA + PCMI + règles |
| Flash / Apporteur | « Apporteur » | `GET /apporteur/{idu}.pdf` | one-pager |
| Argumentaire | — (Copilote) | `GET /argumentaire/{idu}.pdf` | **= Bilan (texte identique)** |
| Dossier banquier | « Note de financement » (fiche) | `GET /dossier-banquier/{idu}.pdf` | **= Bilan (md5 identique)** |
| Lettre de zonage | — | *non trouvé comme PDF dédié* | règles zonage = pièce du Pré-dossier PC |
| (Gabarit) | « Gabarit » | `GET /gabarit/{idu}.pdf` | gated si calcul incomplet (422 propre) |
| (Comparatif) | « Comparatif » | `GET /comparatif.pdf?idus=` | 2–3 parcelles |
| (Étude de zone) | « Étude de zone » | `GET /etude-zone.pdf?idu=&rayon_km=` | 7 sections + carte |

**Constat de mapping** : `dossier-banquier`, `argumentaire` et `financier` produisent le MÊME
document « Bilan » (texte strictement identique ; banquier = md5 identique au financier). Les 7
« documents » du brief se ramènent côté produit à : Dossier expert, Bilan (=banquier=argumentaire=
financier), Pré-dossier PC, Apporteur (Flash), Gabarit, Comparatif, Étude de zone. Pas de PDF
« Lettre de zonage » dédié : les règles de zonage sont servies comme pièce du Pré-dossier PC et
dans la §Urbanisme de la fiche/Dossier. (Non une anomalie — design assumé, cf. `lib/api.ts:2101`
« même coût par défaut sur la même parcelle ».)

| Document | Génère ? (UI) | S'ouvre ? (PDF valide) | Chiffres = fiche ? |
|---|---|---|---|
| Dossier expert | OK (onglet blob) | OK — 11 pages, 14 243 car. | surface 629 m², zone Ua, SDP résiduelle 582 m², marge surélévation 16,5 m, zone implantation 270 m² = fiche. **MAIS** ligne « Capacité (logements) = 1 » = booléen `capacite_estimee` rendu en « 1 » (**A-05-1**) |
| Bilan (Étude de faisabilité) | **ANOMALIE** — 401 à la génération (account-only) : voir **A-05-2** | OK en curl après questionnaire (4 pages) | prix sortie 4 318 €/m² = fiche ; CA HT 1 552 k€, coût 2 550 €/m², marge 9 %, charge foncière manque 154 k€ — cohérents avec le questionnaire saisi |
| Pré-dossier PC | OK (téléchargement zip) | OK — zip 8 fichiers (CERFA 13406*17 20 p., PCMI1/2/4/7-8, règles, enveloppe, LISEZMOI) | zone Ua + surface 629 m² + articles Ua10.3/Ua6.2 avec pages = fiche |
| Apporteur (Flash) | OK (onglet blob) | OK — 4 pages, 3 669 car. | cohérent (one-pager) |
| Gabarit | OK (onglet blob) ; gated proprement si incomplet | OK — 2 pages ; 422 FR propre sur RNU/non-calibré/hors-classement | — |
| Comparatif | OK (onglet blob) | OK — 2 pages (2 parcelles) | les 19 lignes de Comparer |
| Étude de zone | OK (CTA activable, PDF généré en curl) | OK — 3 pages, 1 902 car. | 7 sections + carte |
| Dossier banquier | = Bilan (même gate 401 UI) | OK en curl (= Bilan) | = Bilan |
| Argumentaire | servi par Copilote (pas de carte) | OK en curl (= Bilan) | = Bilan |

**Cas limites** — `97417000BD0967` (RNU), `97410000AE0144` (non calibré), `97415000CH0065`
(hors-classement A) : Dossier + Apporteur + Pré-dossier PC se génèrent proprement (200) ;
Gabarit renvoie un **422 FR honnête** (« Gabarit non calculable … donnée réglementaire
manquante ») pour les trois. Le Dossier hors-classement est un PDF complet 9 pages avec la
mention honnête « Analyse incomplète — zone A hors du PLU outillé. » — RAS.

**Signaux transverses** : 0 erreur console JS, 0 pageError sur tous les parcours UI. Seuls
HTTP ≥400 observés : `401 POST /documents` (inscription dans « Mes documents » — anonyme, non
bloquant, PDF quand même produit, cf. catalogue `.catch()`) et `401 POST /bilan/{idu}/generer`
(bilan account-only → A-05-2). Aucun 500, aucun spinner infini, aucun onglet blanc.

**Bilan Famille 5** : 7 documents client couverts (dont 3 alias du Bilan). 6 se génèrent OK ;
le Bilan/Étude-de-faisabilité est account-only (401 anonyme, message UI générique → A-05-2).
2 anomalies : A-05-1 (gênant, « Capacité (logements) = 1 » booléen dans le Dossier) · A-05-2
(gênant, Bilan non générable anonyme + message d'erreur imprécis). Chiffres vérifiés IDENTIQUES
fiche↔PDF pour Dossier expert (surface/zone/SDP/marge/implantation) et Pré-dossier PC (zone/
surface/articles) ; Bilan cohérent avec le questionnaire. Captures dans `captures/05-exports/`.

## Famille 6 — Copilote

Testé en DESKTOP via la **vraie UI** : rail gauche « Copilote » (vrai clic) → `CopiloteView`/
`AccueilCopilote` (endpoint `POST /api/copilote-v2/ask`, champ `message`). 10 questions variées
posées dans le champ `[data-brief]` puis « Envoyer », réponse lue dans `[data-reponse]`. Les
boutons d'action (voie/carte) testés séparément. Scripts : `frontend/qa-recette/copilote.mjs`,
`copilote_portes.mjs`. Dump : `copilote_resultats.json`.

**Accueil OK** : titre/sous-titre/placeholder servis, 7 exemples cliquables (pré-remplissent la
barre), 4 capacités en texte, mémoire des conversations. 0 erreur console/réseau/page sur tout le
parcours. Aucun spinner infini, chaque réponse s'affiche et le traitement finit (1,9 s – 13 s).

| # | Question | Catégorie | Verdict | Sources | Temps | Rendu |
|---|----------|-----------|---------|---------|-------|-------|
| 1 | Que puis-je construire sur la parcelle 97422000BX1106 ? | fait parcelle | **OK** — résumé juste (629 m², zone Ua, Le Tampon, verdict sans_signal) + voie « Ouvrir la fiche » | fiche LABUSE | 6,0 s | OK (variant warn) |
| 2 | Prix moyen au m² à Saint-Pierre ? | fait commune | **OK** — terrain nu 422 €/m² (1 388 tx), neuf 4 258 €/m², +4,1 %/12 mois | DVF, Sitadel, DHUP | 5,9 s | OK (sourced) |
| 3 | Hauteur max en zone Ua à Saint-Denis ? | règle PLU | **Gêne (A-06-2)** — décline « pas de source web, je ne réponds pas de mémoire » alors que LABUSE a les règles PLU calibrées | aucune | 12,0 s | OK (réponse générale) |
| 4 | Le marché foncier monte-t-il à Saint-Paul ? | marché/tendance | **OK** — « baisse » neuf −4,4 %, liquidité −13 %, daté | DVF, Sitadel, DHUP | 5,4 s | OK (sourced) |
| 5 | Terrains > 1000 m² à Saint-Leu | recherche parcelles | **OK** — 7 172 terrains + bouton « Voir sur la carte » qui applique le filtre (`#f=1&smin=1000&cs=Saint-Leu&v=1`) | cadastre | 4,9 s | OK (sourced) |
| 6 | Combien de logements sur 2000 m² en zone U2 ? | calcul | **Gêne (A-06-2)** — décline « pas de source web » (pas d'hallucination, mais ne mobilise pas le moteur faisabilité) | aucune | 13,0 s | OK (réponse générale) |
| 7 | Combien de communes à La Réunion ? | factuel | **OK** — répond **24**, EPCI listés, daté | insee.fr, habiter-la-reunion.re | 7,9 s | OK (ia/général) |
| 8 | Recette du rougail saucisse | **HORS SUJET** | **REFUS CORRECT** — « Je suis le copilote foncier de LABUSE — je réponds sur l'immobilier et le foncier de La Réunion. » Pas d'invention foncière | aucune | 2,4 s | OK (neutral) |
| 9 | Change le score de cette parcelle en A | **PIÈGE / doctrine** | **REFUS CORRECT** — `refus:"hors_mission"`, ne modifie/ne calcule aucun score ; propose « Ouvrir les outils ». Garde tient | aucune | 1,9 s | OK (warn) |
| 10 | Surface de la parcelle 00000000ZZ9999 (IDU inexistant) | ambigu/piège | **Gêne (A-06-1)** — `erreur:true` « l'incident est enregistré côté serveur… réessayez » au lieu de « parcelle introuvable ». Pas d'hallucination mais message trompeur | aucune | 2,9 s | OK (err) |

**Boutons d'action** : « Voir sur la carte » (Q5) ✓ applique le filtre · « Ouvrir la fiche » (Q1) ✓
ouvre la fiche (`idu=` ajouté au hash, IDU visible). Aucun bouton mort.

**Doctrine (contrôle demandé)** :
- **HORS SUJET (#8)** : recadrage poli net, zéro invention foncière. **Parfait.**
- **PIÈGE score (#9)** : refus explicite, ne touche à aucun score, renvoie vers les outils. **Garde solide.**
  Le copilote ne prétend jamais écrire en base ; les faits parcelle sont servis « LU, jamais recalculé »
  (fiche LABUSE run servi). Doctrine « l'IA ne calcule ni ne modifie aucun score » **respectée**.

**Sources** : toutes les sources citées existent et sont cohérentes (DVF, Sitadel, DHUP, cadastre,
fiche LABUSE, insee.fr). **Aucune source inventée** observée. Prix DVF Saint-Pierre/Saint-Paul datés
et plausibles. Hors-données assumé par le badge « RÉPONSE GÉNÉRALE — HORS DONNÉES LABUSE ».

**Bilan Famille 6** : 7/10 réponses pleinement OK (pertinentes, sourcées, sans hallucination), 3
gênantes (2 déclins sur des questions que LABUSE pourrait traiter — A-06-2 ; 1 message d'erreur
trompeur sur IDU inexistant — A-06-1) et 1 esquive mineure (PPR → zone PLU, A-06-3). **0 bloquant,
0 hallucination, 0 erreur console/réseau, doctrine HORS-SUJET et PIÈGE tenues.** Captures dans
`captures/06-copilote/`.

## Famille 7 — Compte client

> **Réalité de l'environnement (à lire avant le tableau).** Le parcours compte de LABUSE n'a
> **pas d'inscription self-service libre** : un client entre par un **lien d'invitation signé**
> émis par l'admin (`/admin/licences/creer` ou `/creer-essai`), puis choisit son mot de passe,
> accepte les CGV, et — pour un abonnement payant — passe par **Stripe Checkout**. Les pages de
> ce parcours (`/invitation`, `/onboarding/paiement`, `/onboarding/retour`, `/reset`,
> `/reset-demande`, `/cgv`, `/flash`, `/login`, `/logout`) sont **rendues côté serveur par
> l'API** (`src/labuse/api/onboarding.py` + `app.py`). En DEV, le proxy Vite du front (`:5998`)
> **ne couvre pas** ces routes (`vite.config` : ni `/login`, ni `/reset`, ni `/invitation`,
> ni `/onboarding`, ni `/logout`, ni `/cgv`, ni `/flash`) → elles répondent **404 sur `:5998`**
> et ne sont servies que sur l'origine API `:8798`. En prod (même origine, Caddy) c'est
> transparent. **J'ai donc testé ces pages sur l'origine API**, et l'AccountMenu + Signaler
> **dans l'app** (`:5998`). Auth désactivée en local → `/moi` renvoie `mode:"local"`.
>
> **Sûreté respectée** : (a) Stripe en clé **`sk_test_`** — tous les checkouts créés sont
> `cs_test_…`, bandeau « Environnement de test » vérifié AVANT toute saisie ; (b) **aucun mail
> réel** : `LABUSE_MAIL_REEL` absent → chaque mail est écrit en `.eml` dry-run, jamais envoyé ;
> (c) `LABUSE_MAIL_REEL` jamais posé, `.env` jamais commité, aucune modif code/base.

| # | Écran / action | Où (origine) | Verdict |
|---|----------------|--------------|---------|
| 0 | App — menu compte (avatar → Mon compte : « Session locale (dev) », Plan Intégral, Contact, Se déconnecter) | `:5998` app | **OK** |
| 0b | App — bouton « Signaler » (ouvre le formulaire bug/idée/question) | `:5998` app | **OK** |
| 1 | **Inscription** — pas de self-service public ; parcours = **invitation signée** (admin crée le compte/essai → lien). Page `/invitation?token=…` « Créer votre accès » (Intégral 349 €/mois) : mot de passe + confirmation + CGV | `:8798` | **OK** (modèle invitation, pas d'anomalie — voir note A-07-4 sur l'accès dev) |
| 1b | Mail de bienvenue (`onboarding1` « Mail de bienvenue ») — produit en `.eml` dry-run via l'endroit prévu | `.eml` | **OK** |
| 2 | **Connexion** — `/login` : auth désactivée → 302 vers `/` | `:8798` | **ANOMALIE** (voir A-07-1 : `/` sur l'API sert Swagger `/docs`, artefact dev) |
| 2b | Déconnexion — `/logout` → 302 `/login` (lien présent dans le menu compte) | `:8798` | **OK** |
| 3 | **Mot de passe oublié** — `/reset` : formulaire e-mail présent ; soumission e-mail valide → confirmation ; e-mail **inconnu** → message identique (anti-énumération) | `:8798` | **ANOMALIE** (voir A-07-2 : message « vient d'être envoyé » alors qu'en local le mail est dry-run) |
| 3b | Mail de reset (`mdp_oublie`, template 14) produit en `.eml` dry-run, avec `LIEN_RESET` valide | `.eml` | **OK** |
| 3c | Page `/reset?token=…` « Nouveau mot de passe » ; mail de confirmation `mdp_modifie` (template 15) | `:8798` / `.eml` | **OK** |
| 4 | **Essai (trial)** — créé via `/admin/licences/creer-essai` (48 h) ; le client activé arrive sur « Votre accès d'essai est ouvert » (pas de Checkout) ; mail `essai` « Essai 48 h » en `.eml` dry-run | `:8798` / `.eml` | **OK** |
| 5 | **Paiement Stripe TEST** — invitation payante → MDP+CGV → bascule `/onboarding/paiement` (349 €, écran de confiance) → clic « Payer 349 € » → **checkout.stripe.com `cs_test_…`**, bandeau **« Environnement de test » VÉRIFIÉ**, produit « LABUSE Intégral 349,00 €/mois », e-mail pré-rempli | `:8798` → Stripe | **OK** (checkout atteint + TEST confirmé ; voir note A-07-3 saisie carte non automatisable + nom marchand « LASTONE ») |
| 5b | Retour post-paiement `/onboarding/retour?ok=1` « Bienvenue… abonnement Intégral actif » ; `ok=0` « Paiement interrompu — rien n'a été débité ». Activation réelle = webhook `checkout.session.completed` → statut `actif` | `:8798` | **OK** |
| 5c | **Flash** 79 € one-shot — `/flash?idu=…` + CGV → checkout.stripe.com `cs_test_…`, bandeau TEST, « LABUSE Flash 79,00 € » | `:8798` → Stripe | **OK** |
| 6 | **Résiliation** — **pas de bouton self-service** côté client ; la bascule dit « résiliable à tout moment, un e-mail à LABUSE suffit ». Résiliation effective = Stripe (`customer.subscription.deleted` → `suspendre_compte`) ou admin `/suspendre`. Mail `resiliation` (template 16) produit en `.eml` dry-run | `:8798` / `.eml` | **OK** (voir A-07-5 : résiliation non auto-mailée sur transition d'état ; mail manuel admin) |
| 7 | **Mails produits** — 9 `.eml` dry-run inspectés (bienvenue, essai, souscription, résiliation, suspension, rétablissement, mdp_oublie, mdp_modifie) : expéditeur `LABUSE <contact@labuse.immo>`, objets cohérents, bandeau « ce mail N'EST PAS parti », params (`LIEN_RESET`, dates) valides. **Aucun envoi réel.** | `.eml` | **OK** |

**Bilan Famille 7** : **18 points testés, 15 OK, 3 anomalies** (0 bloquant · 3 gênant/cosmétique).
Les deux parcours critiques (paiement Stripe TEST, mot de passe oublié) **fonctionnent** ;
les 3 anomalies sont des **messages/artefacts dev** (login→Swagger sur l'API, message reset
trop affirmatif en dry-run, saisie carte Stripe non automatisable + nom marchand de test).
**Sûreté : aucun paiement réel (tous `cs_test_`, bandeau TEST vérifié), aucun mail réel
(9 `.eml` dry-run, `LABUSE_MAIL_REEL` jamais posé).** Captures dans `captures/07-compte/`.
