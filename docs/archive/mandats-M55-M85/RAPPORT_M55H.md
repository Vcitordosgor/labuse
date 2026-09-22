# RAPPORT M55-H — Polish design, tri, libellés (11 points, 12/08/2026)

**Branche** : `feat/m55-h` (base : main `8a45a193` = M55-G + suite mergés — précondition vérifiée).
**11 commits, un par point** (`7155515b` → `de7f8715`) + ce rapport. CC ne merge jamais.
**Captures** : `reports/m55-h/captures/` (harnais `frontend/qa/m55h_captures.mjs`, rejouable).
Note : `/mnt/skills/public/frontend-design/SKILL.md` n'existe pas sur ce poste — l'esprit demandé
(hiérarchie, matières) a été appliqué dans les tokens LABUSE (mint/surfaces/display, DESIGN_SYSTEM).

## 1. Chevrons — centrage optique
Le glyphe texte « ⌄ » (ancré ligne de base, biais visible une fois pivoté) est remplacé par un
**chevron SVG symétrique** (trait arrondi, centré géométriquement = optiquement), rotation
fermé→gauche / ouvert→bas inchangée, hover inchangé. Captures `h1_chevron_*`.

## 2. Accueil — refonte visuelle, contenu exact
Bouton « Commencer → » en pièce maîtresse : proportions généreuses (py-4), texte centré avec
**flèche dessinée** (SVG aligné, glisse au hover ; le libellé figé garde son « → », rendu en
vectoriel), états hover (halo) / active (enfoncement). Hiérarchie typographique étagée : titre
display semi-gras → chiffres (les preuves) → ligne descriptive dim ; « i » centrés sur leur
chiffre (items-center — fini le flottement baseline) ; respiration verticale (mt-7/8/3, marges
latérales px-7). Contenu strictement identique (texte figé Vic 9 ter). Capture `h2_accueil`.

## 3. Zone des deux boutons + reset
Groupe d'action net : `gap-2` constant, même largeur ; « Voir les N parcelles » secondaire FRANC
(fond + bordure visibles) au-dessus ; « Demander à LABUSE → » primaire dominant (plus haut,
flèche dessinée, hover/active) ; « Réinitialiser les filtres » (danger discret) SÉPARÉ du groupe
par un filet + respiration. Capture `h3_zone_boutons`.

## 4. Tri Surface — les deux sens
Re-clic sur la pill active inverse le sens : « Surface ↓ » ↔ « Surface ↑ », dans les deux modes.
Servi par la clé `sort=surface_asc` (ajout minimal aux tables d'ORDER BY + pattern /filtre et
export CSV — les slivers < 2 m² restent masqués par le plancher d'affichage existant). Vérifié :
asc sert 2 m² d'abord ; sonde UI ↓→↑ OK.

## 5. Liste d'analyse groupée par tiers (décision Vic)
`groupes=1` (préfixe d'ORDER BY, serveur) + comparateur client (mode commune) : brûlantes →
chaudes → potentiel long terme → à creuser → **potentiel épuisé** (declasse_*) ; le tri choisi
s'applique DANS chaque groupe. Mode factuel : liste plate inchangée. Le chemin rapide « index
rang » est contourné quand le groupement est demandé (page groupée mesurée à ~1,3 s). Sonde :
page 1 = Brûlante → Chaude ✓.

## 6. MESURÉ — Opportunités vs Mutation
**Constat Vic confirmé, et ce n'est PAS un bug de branchement front** (les deux tris lisent bien
deux colonnes distinctes : `s2.rang` vs `s2.mult_base`). La mesure (SQL, run servi) :
- **aucune inversion stricte sur les 431 663 parcelles** (0 paire où un meilleur rang porte un
  ×N strictement plus petit) — le rang est MONOTONE dans le ×N ;
- le rang est construit sur **P seul** (pondéré AU), les ex æquo — nombreux, le ×N est arrondi à
  2 décimales : **15 valeurs distinctes de ×N dans le top 500** — départagés par la qualité du
  terrain (contribution D) → SDP → surface → IDU (pipeline.py, départage M28) ;
- corrélation des deux ordres : 0,9947 ; top-50 servi : 50/50 positions identiques.
Le libellé « probabilité de vente × qualité du terrain (l'opportunité globale) » était donc
FAUX : la qualité n'intervient qu'en DÉPARTAGE, pas en produit. **Fix (dans le périmètre)** :
les libellés du tri disent le réel (« la probabilité de vente d'abord, les ex æquo départagés
par la qualité du terrain » / « le ×N brut, sans départage ») ; « (P×C) » retiré des tooltips.
**Hors périmètre (à arbitrer)** : faire du rang un vrai produit P×C serait un changement moteur.

## 7. Menu périmètre — une ligne
Menu élargi à 320 px, nom en nowrap, lien shrink-0 : nom + code postal + « voir la fiche → »
sur UNE ligne pour les 24 communes (La Plaine-des-Palmistes comprise). Au passage : le menu
affichait le code INSEE (ressemble à un CP sans l'être) — il affiche désormais le VRAI code
postal, depuis la table mesurée du panneau (`CP_COMMUNES`, source unique). Capture `h7_*`.

## 8. Toujours une section ouverte (décision Vic)
L'état « aucune section » n'existe plus (type store `'couches' | 'filtres'`) : Couches par
défaut ; cliquer le titre de la section ouverte ne fait rien ; ouvrir l'autre la remplace ;
l'allumage de l'analyse et le retract post-Révélation rendent la main à Couches. Sondes : clic
sur section ouverte → reste ouverte ; jamais 0 section ✓.

## 9. IDU complet = LA référence
La référence courte disparaît des cartes de résultat — l'IDU complet (97422000AK1372) en mono
lisible. Appliqué aussi aux analogues : restitution IA, comparateur, CRM. Vérifié : la fiche
affichait déjà l'IDU complet ; les exports aussi (pdf_projet : IDU + courte entre parenthèses ;
CSV : idu en 1re colonne). Les outils (pickers, modules) gardent leur affichage contextuel.

## 10. Ventilation complète + « Potentiel épuisé »
- La ligne de résultats affiche les SIX familles : brûlantes · chaudes · potentiel long terme ·
  à creuser · potentiel épuisé · écartées — **mêmes nombres que la phrase de Révélation**
  (source unique getFiltre ; épuisé = retenues − 4 tiers ; écartées = trame − retenues ;
  vérifié : 118 + 1 038 + 2 964 + 29 978 + 43 210 = 77 308 retenues, + 354 355 écartées
  = 431 663). Garde ajoutée : la phrase d'intro n'affiche plus jamais « 0 parcelles » pendant
  le chargement de la trame.
- **« Déclassée » → « Potentiel épuisé »** dans les DEUX sources uniques (miroirs assumés) :
  `frontend/lib/status.ts` (TIER_DECLASSE_META — badges, ventilation, légende, fiche, carte) et
  `src/labuse/verdict_servi.py` (TIER_LABELS — fiche legacy, exports, assistant, résumé).
  Grep : aucune table recopiée ne subsiste (2 occurrences hors dictionnaires : une docstring
  (resume.py) et un repli assistant.py — raccordé). Codes techniques `declasse_*` INCHANGÉS.
  Tests backend renommés : 45 passent.
- « i » sur la ventilation : les trois familles en une phrase chacune (servables / potentiel
  épuisé / écartées — texte du mandat).

## 11. La date et le nom du run disparaissent du rendu client
Sweep par grep (date, q_v8_calibre, « classement du », « run », « servi », « versionné »,
champs API). Retirés :
- **Modale** : la ligne « Classement servi du 12/07/2026… » (posée en M55-G suite) — chaîne
  `algo.dateRun` et requête 0-caller supprimées.
- **Page Sources** : « — gelé le 12/07/2026 » du détail technique (le sha court reste :
  empreinte, ni date ni nom de run).
- **Fiche + outil Renouvellement** : « · run servi q_v8_calibre » retirés.
- **Tooltips/textes** : « du run servi » → formulations sans « run » (cartes de résultat, IA).
- **API cliente** : `/v2/modele` ne sert plus `gel` ni `dernier_run` (run_id + computed_at).
- **PDF** : seul `pdf_premium` imprimait le run (en-tête + pied « (run q_v8_calibre) ») —
  retiré ; mesuré : les 5 autres documents ne l'ont jamais porté. N° de rapport et date de
  génération conservés (dates de document).
**Validation** : 5 documents régénérés (harnais M54-AB) → grep `q_v8_calibre|12/07/2026` =
**0 occurrence** ; page Sources : dates de synchronisation des SOURCES toujours présentes ✓ ;
`/readyz`, santé, audit (admin/ops) inchangés et portent toujours le run ✓. Le nom du run reste
dans les URL d'API (`?source=…`, mécanique de serving, pas du rendu) et le garde-fou de boot.

## Non-régression
5 combinaisons /filtre STRICTEMENT identiques · rituel 3 317 ms (3,0 s + réseau) · un seul récit
de nombres (ventilation == Révélation, source unique) · **carte == liste préservé** (Salazie +
procédure : liste 1 / peintes 1) · harnais M54-AB rejoué : tous [OK], **zéro code technique dans
les documents** · tests backend ciblés 45/45 · tsc 0 · vitest 32/32 · build vert · mobile
vérifié · 0 erreur console sur les sondes.

## Périmètre
Front + libellés partagés (status.ts / verdict_servi.TIER_LABELS) + mesures. Écarts assumés et
minimaux, chacun exigé par son point : clé de tri `surface_asc` + param `groupes` (points 4-5,
ORDER BY seulement), purge `/v2/modele` + PDF premium (point 11, demandé explicitement).
Codes techniques et moteur INTACTS. CC ne merge jamais — `feat/m55-h` en attente de Vic.
