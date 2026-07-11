# AMÉLIORATIONS UX — audit du 12/07/2026 (product designer senior)

**Statut : SUGGESTIONS. Rien n'est implémenté. Décision : Vic.**
Grille : DA (noir/mint/violet #B497F0) · feedback < 300 ms · états vides · wording FR ·
hiérarchie · contrastes · focus clavier · tooltips · cohérence badges · navigation · mobile 375.
Priorisation : **P = impact × effort** (P1 = fort impact/faible effort). Preuves : `audit_shots/ui2026/`.

## P1 — fort impact, faible effort

1. **[Mobile 375 · Cartes] La carte n'existe pas sur mobile.** Le panneau COUCHES occupe
   100 % de l'écran, la légende VERDICT recouvre le texte du hero, la carte est invisible
   (`375_boot.png`). Proposition : sous 640 px, panneau en tiroir escamotable (bouton
   « Couches ») et carte plein écran par défaut.
2. **[IA · confiance] Mode dégradé invisible.** Quand l'appel Anthropic échoue (crédits),
   chaque recherche part en « repli stub » mots-clés : la requête « DPE F ou G au Tampon »
   rend 2 080 parcelles (= tout Le Tampon) sans dire à l'utilisateur que le critère DPE a
   été ignoré — l'explication « (repli stub) » reste sur la vue IA qu'on vient de quitter.
   Proposition : reprendre l'`explanation` serveur DANS la restitution (« Filtres appliqués :
   commune Le Tampon — critère DPE non traduit »), badge « mode mots-clés » si `stub`.
3. **[Fiche · erreurs] Wording « Le serveur est peut-être périmé — relancer \`labuse api\` ».**
   Message développeur montré à un client (hors 429, désormais traité). Proposition :
   « Connexion au serveur impossible — vérifiez votre réseau ou réessayez » + le détail
   technique en ligne discrète.
4. **[Carte · état vide] Liste de résultats vide sans explication** (commune à 0 chaude,
   `1440_carte_cilaos_vide.png`) : zone blanche muette sous les compteurs. Proposition :
   état vide avec message (« Aucune parcelle chaude à Cilaos — élargissez à l'île ou
   ajustez les filtres ») + CTA reset, comme le fait déjà `#map-empty` de l'UI historique.
5. **[Builder segments · saisie] Ranges acceptent les négatifs en silence** (min = −50
   traité comme 0, `seg_valeurs_limites`). Proposition : `min="0"` + garde visuelle
   (bordure ambre) quand la valeur est hors domaine.

## P2 — fort impact, effort moyen

6. **[Segments · mobile] Le builder n'a pas de mode étroit** : colonne filtres fixe 320 px
   → sur 375 la table des résultats est inutilisable. Proposition : onglets « Filtres /
   Résultats » sous 640 px. (La galerie, elle, passe très bien — `375_vue_segments.png`.)
7. **[Fiche · tooltips scores] Q/A/V affichés sans définition au survol.** Le panneau
   « Pourquoi ce score » explique V, mais Q et A restent des sigles pour un nouvel
   utilisateur. Proposition : `title`/tooltip une phrase par score (« Q = qualité
   intrinsèque… », « A = accessibilité/dossier… »).
8. **[Offline] Pas d'état réseau global.** Carte coupée du serveur : toast « Chargement de
   la carte » persistant + erreurs silencieuses en console ; la fiche affiche son erreur
   après ~5 s de retries muets (loader). Proposition : détecteur d'échec réseau global
   (bandeau « Connexion perdue — reconnexion… ») + skeleton avec compte à rebours de retry.
9. **[Focus clavier] Les boutons du Rail, chips et toggles de couches n'ont pas de
   `focus-visible` distinct** (seuls les inputs ont `focus:border-mint`). Un parcours
   clavier complet est aujourd'hui « à l'aveugle ». Proposition : anneau mint 2 px
   `focus-visible` global.
10. **[NL stub · refus] « supprime toutes les parcelles de la base » → « Filtres appliqués :
    flag risques ».** Le repli mots-clés ne refuse pas les demandes hors périmètre ; il
    « trouve » toujours quelque chose. Proposition : liste de verbes interdits côté stub
    (supprimer/modifier/écrire) → réponse out_of_scope systématique.

## P3 — polish

11. **[375] Warning MapLibre « Map cannot fit within canvas »** au boot mobile — bornes de
    fitBounds à adapter au petit viewport.
12. **[Publipostage] Gabarit générique « Aménagement extérieur »** pour les presets
    piscines : un gabarit « bassin/entretien » par métier augmenterait le taux de réponse.
13. **[Typo] Beaucoup de labels 9,5–10 px** (mono tracking-widest) sur fond sombre —
    lisibilité limite sur écrans non-Retina ; passer les libellés porteurs de sens à 11 px.
14. **[Cohérence] Le compteur galerie segments est un cache 24 h** : après recalcul il
    peut différer du builder pendant une session (observé égal aujourd'hui, mais aucune
    mention « compteur du JJ/MM à HH:MM » — l'afficher éviterait la question).
15. **[Flash] Le rapport n'a pas de section Copropriété** alors que la fiche écran en a
    une (parcelle `97411000BH0670` : bloc copro à l'écran, absent du PDF). À trancher au
    moment des Lots 2-4.

## Ce qui est déjà à niveau (à préserver)

- DA rigoureuse (noir/mint, violet réservé au copilote/modules — aucune dérive relevée
  sur 150+ captures) ; nombres fr-FR (« 5 315 ») ; dates FR ; badges statut/brûlante
  cohérents carte/liste/fiche/export ; états vides de Projets avec CTA ; toasts d'export
  explicites ; mention RGPD des exports (« aucune donnée nominative ») ; fiche = loader
  puis erreur actionnable (Réessayer) ; navigation retour partout (Escape fiche, retour
  segments, fermeture modules).
