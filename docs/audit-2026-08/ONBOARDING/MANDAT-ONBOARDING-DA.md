# MANDAT — ONBOARDING : MISE EN PAGE ET ÉTATS
Régime AUTONOME. Commits par lot (O1→O4). RÈGLES COMMUNES. Findings ON-001→.
Référence visuelle : docs/audit-2026-08/ONBOARDING/maquette-onboarding-v1.html (validée par Vic). Elle montre 5 vues en 390 px : invitation (case décochée ET cochée), paiement interrompu, mot de passe oublié, Flash. La section « Ce qui change, et pourquoi » en bas de la maquette énonce les règles — elles s'appliquent à TOUS les écrans du parcours, pas seulement aux 5 montrés.

## CONSTAT DE DÉPART (planche du mandat précédent, captures 390 px)
Le parcours applique bien la DA « Coffre » (fond sombre, vert menthe, Space Grotesk, oiseau) — la DA n'est PAS en cause. Ce qui cloche est la mise en page : contenu collé en haut avec parfois plus de 1 000 px de vide en dessous, blocs serrés, hiérarchie plate, et un bouton d'action peint en vert plein alors qu'il refuse d'agir.

## O1 — LE CONTENU SE CENTRE DANS LA HAUTEUR
Tous les écrans du parcours d'entrée : le bloc de contenu est centré verticalement dans la fenêtre, le pied de page (liens légaux) reste en bas. Plus aucun écran ne laisse un grand vide sous son contenu. Vaut pour les écrans courts (paiement interrompu, mot de passe oublié, nouveau mot de passe, activation admin, session expirée…) comme pour les longs, qui défilent normalement quand le contenu dépasse la hauteur.
Vérifier à 390, 768 et 1440 px, et sur une fenêtre courte (hauteur 600) : rien ne doit être coupé ni collé au bord.

## O2 — LES BOUTONS DISENT LEUR ÉTAT
Un bouton d'action qui ne peut pas agir n'est jamais peint comme un bouton actif. Deux états, comme dans la maquette : éteint (fond sombre, texte gris, bordure discrète) tant que la condition n'est pas remplie ; allumé (vert menthe, texte sombre, ombre portée) dès qu'elle l'est. La transition est immédiate au clic sur la case.
Conséquence : le message d'erreur permanent sous le bouton (« Cochez les conditions générales pour continuer ») disparaît — l'état visuel le remplace. Un message n'apparaît que si l'utilisateur force l'action.
Accessibilité : l'état désactivé doit être annoncé aux lecteurs d'écran (aria-disabled), le focus clavier reste visible, et le contraste du texte gris sur fond sombre reste lisible.
Appliquer partout où une condition garde un bouton dans le parcours.

## O3 — RESPIRATION, HIÉRARCHIE, USAGE DU VERT
- Espacement : marges latérales confortables sur mobile (le texte ne touche pas les bords), espace franc entre les groupes (titre / formulaire / conditions / action / mentions).
- Hiérarchie : titre en Space Grotesk espacé, sous-titre d'offre en une ligne, phrase d'accueil en corps de texte gris clair, mentions en petit et gris foncé. Trois niveaux lisibles, pas un aplat.
- Le vert est un ACCENT, jamais un porteur de texte long. Sur /flash, le paragraphe intégralement vert devient une liste sobre à puces vertes (5 lignes scannables, cf. maquette). Le mauve reste réservé à l'IA : absent de tout le parcours.
- Champs : 16 px minimum (pas de zoom iOS), hauteur de zone tactile ≥ 52 px.

## O4 — TEXTES ET ÉCRANS À RETRAVAILLER (contenu, pas seulement forme)
- **Invitation client** : sous-titre « Intégral · 349 €/mois · sans engagement », « sans engagement » mis en valeur en vert (c'est un argument commercial). Les valeurs viennent de offres.py, jamais en dur.
- **Paiement interrompu** : aujourd'hui trois lignes et un lien noyé. Devient : bouton d'action « Reprendre le paiement », puis un encadré « Un doute avant de payer ? Écrivez à victor@labuse.immo — je réponds moi-même, et je peux vous ouvrir un accès d'essai de 48 h. » (adresse exacte à confirmer dans la config, ne pas coder en dur si une variable existe).
- **/flash** : prix affiché en grand (79 € · paiement unique), les 5 lignes de contenu, et sous le bouton « Vous vérifiez la parcelle avant de payer. »
- **Mot de passe oublié** : ajouter sous le bouton « Le lien est valable une heure et ne sert qu'une fois. » (vérifier la durée réelle dans le code et écrire la vraie valeur).
- **Activation admin** : le titre tient sur une ligne si possible ; sinon équilibrer les deux lignes.
- Relire tous les textes du parcours : phrases courtes, vouvoiement, aucun jargon, aucune promesse fausse (pas de « depuis votre espace » pour la résiliation — elle se fait par e-mail).

## FIN
Critères : aucun écran du parcours ne laisse de grand vide (vérifié par captures 390 + 1440) · les boutons conditionnels ont deux états distincts et accessibles · le vert ne porte plus de paragraphe · les valeurs d'offre viennent toutes de offres.py · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree).
Livrable de vérification : planche PLANCHE-ECRANS-V2.html — TOUS les écrans du parcours, en **390 px ET 1440 px** (le mandat précédent n'a livré que 7 captures mobile alors qu'il en annonçait 32 : cette fois, la planche doit être complète, et le rapport doit dire combien d'écrans et combien de captures elle contient).
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff fix/onboarding-da). Tu ne merges pas.
