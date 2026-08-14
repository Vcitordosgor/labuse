# RAPPORT M83 — Le premier écran, la fiche commune, le nouveau logo

Branche `feat/m83-accueil-socle`. Un commit par partie. Run servi q_v9_m81. **NE PAS MERGER.**

---

## PARTIE A — Cadrage d'ouverture de la carte

**Constat** : la carte ouvrait DÉJÀ sur l'île entière, mais sur des **coordonnées figées en dur**
(`ILE_BOUNDS`). Le reste d'A1 était en place (mesuré au boot) : 24 communes nommées (marqueurs z<10),
**parcellaire filigrane visible** (couche `ile-limites`, contours fins = preuve de densité), limites
communes `#2E7D52` + trait de côte `#4ADE80` (M65), mode sombre.

**Fait** : `ileBounds()` calcule l'emprise = **union des bbox de communes** servies par `/communes`
(`ST_Extent` du parcellaire). Si la couverture évolue, le cadrage suit. `ILE_BOUNDS` n'est plus qu'un
repli de tout premier frame. Le cadrage affiché est identique (l'union ≈ l'ancienne constante) mais
désormais **dérivé des données**.

**A2 — panneau** : LeftPanel et MapView sont des **siblings flex** (App.tsx) — la carte est à droite du
panneau, l'île n'est jamais masquée. **A2 — bouton « retour à cette vue »** : **INEXISTANT**. Proposé
(non ajouté sans arbitrage) : un bouton discret « ⊡ Toute l'île » dans les contrôles carte qui appelle
`fitBounds(ileBounds())` — le recadrage dynamique est déjà prêt, il ne manque que le déclencheur.

**A3 — PERFORMANCE (mesurée)** : temps **boot → idle (rendu stable) = ~2,3 s** (viewport 1440×1000).
Acceptable. Simplification EN PLACE (cadrage NON dégradé) : **tuiles vectorielles MVT** (`/map/tiles`,
`tiles.py`) — source `parcels-ile` minzoom 9, **généralisation agressive à z≤11** (10-30 m, extent 1024)
puis géométrie brute à z≥12. Les 431 663 parcelles ne sont jamais servies brutes à ce niveau.

**A4** : ligne d'invite « Zoomez ou cliquez une commune pour voir ses parcelles » conservée (mode île,
z<10). Elle ne concurrence pas le panneau (bandeau bas de carte vs panneau gauche).

---

## PARTIE B — Panneau d'accueil (maquette DA-SOCLE-ACCUEIL.html, classes recopiées)

Refonte d'`AccueilPreuves` : **B1** promesse « Tout le foncier de La Réunion. / Au même endroit. » (2e
ligne mint) · **B2** chiffres compacts (parcelles/communes/sources, dynamiques `/accueil/chiffres`) ·
**B3** trois portes — Explorer la carte (mint, ferme l'accueil) · Demander au Copilote (**MAUVE, légitime
ICI ET SEULEMENT ICI**) · Ouvrir un outil (neutre, `N = MODULES.length` dynamique = 28, aligné tri M82) ·
**B4** « CETTE SEMAINE » · **B5** ligne de fraîcheur (point vert). Comparaison côte à côte maquette : OK.

**B4 — constat mesuré à rapporter (doctrine « un zéro n'est pas une absence »)** : l'ingestion est **en
retard** (mesuré) — **permis Sitadel arrêtés au 30/06/2026**, **DVF (ventes) jusqu'au T4 2025** (DVF n'a
PAS de date de publication en base — seul `date_mutation` ; la fraîcheur se lit sur le dernier trimestre
réel ≥ 50 ventes). Donc les compteurs « 7 jours » valent ~0 par retard, et le bloc le **DIT** honnêtement
(« permis Sitadel — dernière donnée 30/06 », « ventes DVF — dernier trimestre publié 2025T4ᵉ »,
« 3 communes en procédure PLU »). **Proposition** : ce bloc prouve la base par ses **dates de fraîcheur**
plus que par un flux hebdo. Si tu veux le rendre « vivant », il faut rafraîchir l'ingestion Sitadel/DVF
(chantier ingestion, hors M83). Le seul signal réellement hebdomadaire-compatible serait le **run de
scoring** (bascules) — à brancher si souhaité.

---

## PARTIE C — Fiche commune : le foncier d'abord

**C1 — bloc « LE FONCIER DE LA COMMUNE » EN TÊTE** (avant SRU). 7 lignes, points de calcul EXISTANTS :

| Ligne | Valeur (La Possession) | Source / point de calcul |
|---|---|---|
| Parcelles cadastrées | 13 338 | agrégat `parcels` |
| Surface cadastrée | 11 348 ha | agrégat `sum(surface_m2)` |
| Répartition zonage | U 77,9 % · AU 5,9 % · A 3,9 % · N 12,3 % | `parcel_zone_plu.zone_fam` |
| Évaluées au classement | 13 338 (Saint-Philippe : 4 162 dont **4 153 sans zonage GPU**) | `parcel_p_score_v2` (run servi) |
| Prix médian terrain nu | U 436 €/m² (444 v.) · AU 409 €/m² (96 v.) | **M79 `ligne2_terrain_zone`** (réutilisé) |
| Mutations 12 mois | 233 | agrégat `dvf_mutations` (fenêtre DONNÉES, pas now()) |
| Permis 12 mois | 82 (réserve « accordés seulement ») | **`ligne6_offre_engagee`** (réutilisé) |

**Aucun recalcul** : prix terrain + permis réutilisent les points de calcul M79 (`ligne2_terrain_zone`,
`ligne6_offre_engagee`) ; les comptes bruts sont des agrégats directs (pas la duplication d'une métrique
calculée). **« UNKNOWN » n'existe pas comme statut** : c'est l'absence de zonage publié au GPU →
écartée. Saint-Philippe : 4 153/4 162 sans zonage — c'est le « UNKNOWN » attendu, DIT.

**C3 — AUDIT DE VÉRACITÉ (SQL indépendant, La Possession) : TOUT EXACT, aucune divergence.**
SRU 33,04 % / 4 486 LLS ✓ · PLH 1 800 log/an / 47 % ✓ · INSEE 15 427 logements / 837 vacants ✓.
- « 8 quartiers NPNRU » : **en dur** dans le texte front, mais **mesuré exact** (`count(anru_quartiers)=8`,
  6 communes, tous nationaux, aucun régional). Conservé (risque de dérive si la table change — à brancher
  un jour ; pas fait pour ne pas sur-toucher).
- « écart consigné » (vocab interne) : **reformulé** → « pas de source spécifique à La Réunion identifiée
  à ce jour ».
- « proxy T1…T5+ » : **clarifié** → « Résidences principales par nombre de pièces (1 à 5+ pièces — approche
  la typologie) ».

**C4 — DA** : plus AUCUN mauve sur la fiche commune. En-tête « Contexte commune » (violet→neutre), chip
NPNRU (violet→neutre), barres locataires/5p+ (violet→cyan/neutre), zonage en verts sémantiques.

**Garde-fou** : `/communes/Saint-Philippe/contexte` → 200 sans erreur (RNU, 4 153 sans zonage).

**C2 — AUTRES INDICATEURS PROPOSÉS (au rapport, pas en code)** :
- **Rythme ENAF / horizon ZAN** (déjà dans l'outil Rareté, `commune_conso_enaf`) : à rapatrier en fiche
  commune — « il reste X ha constructibles, ~Y ans au rythme actuel ». Fort pour un promoteur.
- **Part de propriétaires personnes morales** (`parcelle_personne_morale`) : qui détient le foncier.
- **Tension du marché** (ligne4_tendance / ligne5_liquidité du point M79) : marché actif/atone.
- **Part de parcelles bâties** (cascade `bati`) : gisement nu vs déjà bâti.
- **Densité de risques** (cascade risques) : PPR/ABF/pente en part du parc.
Recommandation : les 2 premiers (ENAF + PM) apportent le plus ; à trancher.

---

## PARTIE D — Nouveau logo, PARTOUT

Le **tracé de la buse est identique** (ancien/nouveau) — le changement est la **couleur → `#4ADE80`** +
l'usage des **fichiers fournis comme SOURCE UNIQUE** (`frontend/public/marque/`, servis sous `/socle/`).

### Emplacements TRAITÉS (exhaustif)
| Emplacement | Fichier | Traitement |
|---|---|---|
| En-tête app | `Header.tsx` | `<img src="/socle/marque/labuseicone4ADE80.svg">` (fini le SVG inline dupliqué) |
| Filigrane états vides | `States.tsx` (`Oiseau`) | recoloré `#4ADE80` (inline JUSTIFIÉ : couleur dynamique dim/bright) |
| Favicons 16/32/180 | `frontend/public/favicon-{16,32}.png`, `apple-touch-icon.png` | **RÉGÉNÉRÉS** depuis `labuseiconeapp4ADE801024.png` (`sips`) ; `index.html` pointe déjà |
| Tunnel auth (login/reset/invitation/404) | `coffre_ui.py` `OISEAU` + favicon data-URI | recolorés `#4ADE80` (constante UNIQUE, couvre auth.py/onboarding.py/app.py) |
| E-mail digest hebdo | `events.py` | logo inline recoloré `#4ADE80` (JUSTIFIÉ : e-mail externe, pas de /socle) |
| Packs partenaires (×2 gabarits) | `partners.py` | logo inline recoloré `#4ADE80` (print-CSS conservée) |
| PDF fiche premium / projet | `pdf_premium.py` (`_LOGO_PTS`), `pdf_projet.py` | vert PRINT `#1E9E58` |
| PDF page de garde (dossier, banquier, pre-dossier, lettre-zonage, argumentaire) | `briques_pdf.py` `wordmark_html` | vert PRINT `#1E9E58` |
| Rapport Flash | `flash/report.py`, `flash/templates/rapport.html.j2` + `rapport.css` | vert PRINT `#1E9E58` |
| pre_dossier / argumentaire / division_review | idem | vert PRINT `#1E9E58` |
| DA de référence | `docs/DA-LABUSE.html` | **section MARQUE (logo) ajoutée** |
| Maquettes | `docs/mockups/*.html` | recolorés `#4ADE80` |

### Vérifications (D3)
- **Header** : `<img>` sur le fichier source, vérifié (buse verte + « LABUSE » sur fond sombre).
- **Favicon** : `/socle/favicon-32.png` → 200, nouvel icône vert.
- **3 PDF exportés → 200 avec le nouveau bandeau** : fiche premium (67 617 o), baromètre (38 450 o),
  dossier (281 243 o). Rendu de la fiche PDF vérifié : logo vert **lisible sur papier blanc** (`#1E9E58`,
  car `#4ADE80` échoue sur blanc — contraste ~1,5:1).
- **Grep de l'ancien logo écran/auth (`#2FE0A0`, `#C9A961`) en RUNTIME (`src/labuse`, `frontend/src`) : ZÉRO.**

### Emplacements NON traités (dits, avec raison)
- `coffre_ui.py:52` `--or:#C9A961` = **thème gold de l'auth (PAS le logo)** — le logo y est déjà vert.
- `RAPPORT_EXPERT_UX.md`, `frontend/DERIVATIONS.md`, `docs/mandats/*.md` : **documentation** (texte
  citant l'ancienne couleur), pas des logos.
- `qa/au_ouverture/*.{html,py}`, `qa/m18`, `qa/m20` : **artefacts QA figés** (HTML générés) — régénérés
  par les générateurs corrigés ci-dessus, pas édités à la main.

---

## Garde-fous (atteints)
tsc 0 · vitest vert · build vert · **golden 119/119 diff 0** · carte ouvre sur l'île (étiquettes lisibles) ·
panneau se ferme/rouvre · 3 portes ouvrent leur destination · fiche commune OK sur 24 communes (Saint-Philippe
compris) · **grep ancien logo runtime = zéro** · 3 exports PDF → 200 nouveau bandeau · le mauve ne subsiste
que sur la porte Copilote. Captures `qa/m83/captures/`. **NE PAS MERGER.**
