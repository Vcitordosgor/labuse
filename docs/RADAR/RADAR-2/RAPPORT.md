# RADAR-2 — Radar et Veille, sans carte

Branche `feat/radar-2` (worktree `~/Desktop/labuse-radar2b`), base `origin/main` (VEILLE-FIX-2 mergé). Pas de merge.
Maquette de référence : `docs/RADAR/RADAR-2/captures/` (avant/après des 5 écrans, 1440 px).

## Lot 1 — Navigation
- Le rail perd **Veille** : Carte · Outils · Copilote · Radar · Projets · CRM · Sources (`Rail.tsx`).
- Un clic sur **Radar** ouvre le **hub à deux portes** (`components/radar/RadarHub.tsx`, `view:'radar'` +
  `store.radarEcran`) : porte **Radar** (« N biens en vente · dernière capture … ») et porte **Veille**
  (« N parcelles suivies · N alertes »), chiffres RÉELS via `GET /radar/apercu`.
- Chaque écran intérieur porte le `Retour` de la charte (« ← Radar » / « ← Veille »).
- La Veille n'a plus d'entrée de rail ni de carte : on l'atteint par la porte « Veille » du hub. Les
  deep-links de notif (`openSurveillance`) atterrissent directement sur le bon écran Veille du hub.

## Lot 2 — Radar : la carte disparaît
- Plus de carte, plus de légende ●/○, plus de marqueurs Radar. L'écran = **liste (560 px) + marché**
  (`RadarEcran.tsx`).
- **Rattachement automatique RETIRÉ** à l'ingestion (`html_ingest._rattacher` renvoie toujours
  `non_rattachee`). Le module `rattachement_html.rattacher` reste pour les PISTES de l'instruction admin.
- **Purge des rattachements auto existants** (SQL une fois) : `idu=NULL, etat=non_rattachee` où
  `rattachement_humain=false`. **14 effacés, 0 manuel** (aucun manuel en base). Le bouton admin
  « C'est cette parcelle » (`/admin/radar/rattacher-humain`) est intact.
- Un rattachement **manuel** vers une parcelle **suivie** déclenche le **mail immédiat** « parcelle
  suivie mise en vente » (`digests.mise_en_vente_immediate`, même chemin/dédup que le digest).
- Liste : filtres commune · prix max · surface min · type · vendeur · « Plus de filtres » ; tri.
  Pastilles **Nouveau** (<48 h) · **Baisse −X %** (ancien prix barré) · **En vente depuis N j** (>90 j)
  · **De retour** (annonce ré-activée après un retrait). Lien jaune « Voir l'annonce ↗ ». Appartements
  non listés (comptés dans les chiffres). Champs servis à plat par `client.lister` (`ancien_prix`,
  `baisse_pct`, `de_retour`).
- **« M'alerter sur ces critères »** crée une alerte des filtres du moment ; **« Mes alertes · N »** en
  bas de la liste (résumé + « N nouveaux » / « rien de neuf ») avec « Gérer dans Veille ».

## Lot 3 — Radar : le marché (colonne de droite)
`RadarMarcheColonne.tsx` ← `GET /radar/marche-tableau?commune=` (`marche.tableau`) :
- **4 chiffres** (maisons) : demandé médian (Radar) · acté médian DVF 12 mois · écart · biens en vente
  (dont > 90 j). Le prix **acté** vient du moteur DVF de la **fiche commune** (`comparateur.raw_rows` →
  `prix_ancien`), **jamais recalculé à part**.
- **Table par type** (terrain/maison/appartement « statistiques seules ») : en vente, demandé €/m²,
  acté €/m² (DVF), écart, > 90 j, baisses 30 j.
- **Ce qui a bougé · 30 j** : nouvelles / baisses / retirées / de retour.
- **Écart demandé/acté par commune** (maisons), barres, communes ≥ seuil uniquement.
- **Seuil** : sous **30** annonces l'écart s'écrit « sous le seuil » (même règle/`SEUIL_REF_TYPE` que la
  fiche commune). Pied : dernière capture, millésime DVF, phrase sur les appartements.

## Lot 4 — Veille (trois écrans) — `VeilleEcrans.tsx`
- **Veille** : deux portes (Le foncier / Les annonces) + réglage **« Recevoir le résumé par mail »**
  (Chaque matin / Chaque lundi / Seulement dans la cloche) — **même source que Mon compte**
  (`/events/prefs`, VEILLE-FIX-2).
- **Veille · le foncier** : `ParcelInput` + suivre ; tableau des parcelles suivies (IDU cliquable →
  `focusParcelle(idu,{fiche})`, commune, **secteur** = lieu-dit, dernier événement typé + pastille
  « Nouveau » si < 7 j, date, « Ne plus suivre »). `GET /suivis` enrichi (secteur/dernier_evenement/nouveau).
- **Veille · les annonces** : « + Nouvelle alerte (depuis Radar) » ; chaque alerte = critères en
  pastilles, résultat (« N nouveaux depuis hier » / « rien de neuf » / « en pause »), date, « Voir dans
  Radar » (applique ses critères à la liste via `store.radarPrefill`), « Mettre en pause » / « Reprendre »
  (`POST /radar/veille/{id}/pause`), supprimer (`Bouton` ton `danger`). `GET /radar/alertes`.

## Ce qu'on n'a PAS fait
Pas de nouvelle source, pas de changement de la capture ni de la grille de veille (VEILLE-FIX-2 fait
loi), pas de nouvelle DA (composants `components/ui/`).

## Vérifs
tsc 0 · vite build OK · vitest 218 · pytest (suites radar/veille/depot/onglets/commune) verts.
