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
