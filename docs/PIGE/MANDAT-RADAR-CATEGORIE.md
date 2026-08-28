# MANDAT — RADAR : LA CATÉGORIE
Régime AUTONOME. Commits par lot (T1→T6). RÈGLES COMMUNES. Findings RC-001→.
**La référence de ce mandat est la maquette validée par Vic : docs/PIGE/maquette-radar-v2.html.** Ouvre-la et suis-la — structure, hiérarchie, wording. Fidèle à la maquette, pas approximativement inspiré. Les doctrines du §2 de docs/PIGE/MANDAT-RADAR-V0.md restent la loi. Ce mandat REFOND l'interface client du Radar ; le back (pige/*, client.py) est bon — réutilise-le, ne le réécris pas.

## POURQUOI
Le Radar a été livré comme un petit outil du panneau Outils. C'est un pilier de l'app, au niveau du CRM. Il devient une catégorie de premier niveau, plein écran. Vic a validé la maquette écran par écran.

## T1 — LA PROMOTION EN CATÉGORIE
- Radar entre dans le rail de navigation principal, entre Recherche et Veille, avec sa propre icône (radar, cf. maquette).
- Il SORT du registre des outils : plus d'entrée « Radar » dans le menu Outils.
- Route propre, plein écran, layout de la maquette : rail · panneau listing (~434px) · carte.
- Le wording de la maquette remplace l'ancien partout : « Les biens en vente — Repérés sur les portails, rattachés à leur parcelle. Des faits et un lien — jamais le contenu de l'annonce. » Plus aucun « vus par Victor ».
- Le bug « deux catégories ouvertes en même temps » corrigé par RETOURS-1 doit valoir aussi pour la nouvelle catégorie — vérifie.

## T2 — L'ÉCRAN (maquette, écran 1)
- **Filtres** : Commune · Type · Prix min/max · Surface min · segmenté Tous/Rattachés · segmenté Tous/Particulier/Pro. C'est tout.
- **BUG à corriger** : le filtre commune ne proposait que « toute l'île ». Il liste les 24 communes (+ « Toute l'île » en tête) et filtre réellement.
- « Non rattaché » disparaît du filtre de rattachement — deux positions : Tous / Rattachés.
- **L'encart « Être alerté sur ces critères (veille) » disparaît** — la veille a sa catégorie (T4).
- Compteur « N biens · N sur la carte », tri (Plus récentes / Prix croissant / Prix décroissant / Ancienneté / Baisses).
- Cartes du listing : la structure de la maquette — titre mono TYPE · Commune, prix à droite, specs, pied avec pastille (« Sur la carte » / « Non localisé — voir l'annonce »), badges (baisse, vente longue), méta portail·date. Sélection = liseré vert.
- Carte : pins rattachés SEULS, couleur par statut, légende, le hint de la maquette. Comportements de clic inchangés (rattaché → carte+fiche ; non localisé → portail, logué).
- État vide « Le Radar démarre » conforme à l'écran 3 de la maquette.

## T3 — LA FICHE D'UN BIEN (maquette, écran 2)
Dans l'ordre exact de la maquette :
1. En-tête : RADAR › BIEN, titre, badge statut.
2. Prix + mention de baisse + sparkline.
3. **« Voir l'annonce sur [portail] ↗ » juste sous le prix** — visible sans scroller, jamais en bas de fiche.
4. LES FAITS, étiquetés Sourcé/Estimé/Absent.
5. PARCELLE RATTACHÉE → ouvre la fiche parcelle.
6. **« ÉTUDIER CE BIEN »** — six tuiles qui ouvrent chacune l'outil réel, pré-rempli avec la parcelle rattachée : Étudier le bien · Remonter le temps · Calculette foncière · Taxe d'aménagement (commune pré-remplie, cf. R5) · Pièges & risques · Solaire. Mappe chaque tuile vers l'outil existant correspondant ; si un outil n'a pas d'entrée directe par parcelle, ouvre la fiche parcelle positionnée sur le bon module — et si même ça n'existe pas, finding, pas de bricolage.
7. Signaler (inchangé au back) + la micro-note de doctrine.
**Un bien NON rattaché n'a pas la section outils ni le bloc parcelle** — sa fiche s'arrête aux faits, avec le bouton portail.

## T4 — LA VEILLE À DEUX PORTES
La catégorie Veille s'ouvre désormais sur un écran d'entrée à DEUX chemins (deux gros boutons, patron de l'outil Communes restructuré par RETOURS-1) :
- **Veille interne** — le foncier : l'écran de veille existant, tel quel, rien ne change derrière ce bouton.
- **Veille externe** — les annonces : créer et gérer ses veilles Radar (critères commune/type/prix/surface/particulier-pro, événements nouvelle annonce · baisse · retour). Le back existe (type radar dans veilles, pige/veille.py) — c'est son interface propre.
Les veilles existantes des clients ne bougent pas, rien n'est perdu. Les digests et alertes (P4) continuent de fonctionner à l'identique — vérifie par les tests.

## T5 — LE MARCHÉ DÉMÉNAGE
- L'onglet « Marché » disparaît du Radar.
- Ses statistiques (pige/marche.py — réutilise, ne réécris pas) s'installent dans l'outil Communes → **Évolution du marché**, en section « Marché des annonces (Radar) » sous les stats existantes : les agrégats par commune, le n partout, « échantillon insuffisant » sous 5, l'état de démarrage digne. La correction d'endpoint faite par RETOURS-1 (R9) est le socle — pars d'elle.

## T6 — MOBILE ET RECETTE
- Mobile (390) : la catégorie reste utilisable — listing plein écran, carte accessible (le patron tiroir de P3 peut servir), fiche plein écran. Dis ton choix.
- Recette [RADAR-TEST] purgée SQL : jeu représentatif, tous les cas de T2/T3 exercés (filtre commune réel, tri baisses, fiche rattachée avec les 6 tuiles, fiche non rattachée sans outils, état vide, veille externe créée qui matche, veille interne intacte).
- Captures 390 + 1440 : l'écran, la fiche, la veille à deux portes, Évolution du marché avec la section Radar — nombre annoncé.

## FIN
Critères : conforme à la maquette (structure, ordre, wording) · plus aucune trace du Radar dans le menu Outils · filtre commune fonctionnel · aucun contenu d'annonce nulle part · carte = rattachés seuls · clics logués · le test anti-requêtes-portails de P0 reste vert · zéro mauve côté client · couleurs source unique · veilles existantes intactes (tests) · digests P4 intacts (tests) · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · [RADAR-TEST] purgés (vérifié SQL).
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/radar-categorie). Tu ne merges pas.
