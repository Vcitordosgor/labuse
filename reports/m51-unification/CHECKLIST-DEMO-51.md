# CHECKLIST DÉMO M5.1 — 8 vérifications visuelles (Vic)

Lancer : `labuse api` (ou le serveur habituel) puis ouvrir `http://127.0.0.1:8010/socle/`.
Prérequis : `labuse build-mvt` déjà passé (tuiles tier_v2) — inchangé depuis M5.

1. **Panneau île — compteurs v2.** Ouvrir « Toute l'île », allumer le verdict. Les chips doivent lire : Tout · **Brûlantes v2 117** · Chaudes 960 · Réserve foncière 3 607 · À creuser 74 359 · Écartées 352 620. Plus aucun « À surveiller », plus de « 🔥 120 brûlantes ».
2. **Tri par rang.** L'en-tête liste dit « triés par **rang P** ×N surface commune » (rang P souligné). La première carte est `AB 1908` (Trois-Bassins, Brûlante v2 · 1) — c'est une « écartée matrice » : elle était INVISIBLE avant M5.1.
3. **Carte de résultat.** Sur chaque carte : le chip tier v2 est le PREMIER badge (couleur du verdict), avec « · rang » ; le gros chiffre à droite est « ×N » (plus de score V « V nn » nulle part — zoomer la carte à fond : les pastilles disent « #rang »).
4. **Opportunités détectées.** La ligne sous les compteurs : « 431 663 parcelles analysées → **1 077** opportunités détectées » ; le tooltip et « pourquoi ? » expliquent : brûlantes v2 + chaudes v2 ; le popover ventile par tier.
5. **Saint-Benoît.** Sélectionner la commune : tête de liste = `CD 0905` (Brûlante v2 · 8), `AS 1425` juste derrière (Brûlante v2 · 16). Ouvrir AS1425 : le verdict d'en-tête de la fiche = **Brûlante v2 rang 16** — liste et fiche racontent la même chose.
6. **Toggle copro + filtres.** Sous les chips : « masquer les copropriétés » (cocher → la liste se recharge sans copros). Dans « + Filtre » (header) : section « VERDICT · SCORING V2 », « Veille succession », « Masquer les copropriétés », « SIGNAUX PROPRIÉTAIRE » — plus de bandes V ni de 🔥.
7. **Recherche NL.** Taper dans le copilote « les brûlantes de Saint-Paul » : les filtres appliqués = tier Brûlantes v2 + commune Saint-Paul (plus jamais la matrice).
8. **Fiche — pourquoi ce score.** Ouvrir une brûlante → bloc « Probabilité de mutation (P v2) » : les 5 contributions sont en français client (« permis de construire récent (moins de 2 ans) », « parcelle peu boisée »…) — plus de « [≤ 0.4] » ; le bin exact reste au survol. Le bloc propriétaire s'appelle « Signaux vendeur ».

Bonus export : ⬇ CSV depuis le panneau — colonnes `tier_v2, rang_v2, mult_v2, copro, veille_succession` en tête, `statut_matrice` en secondaire, plus de colonne `brulante` v1.3.

Captures avant/après : `reports/m51-unification/captures/` (avant-* = main, apres-* = cette branche).
