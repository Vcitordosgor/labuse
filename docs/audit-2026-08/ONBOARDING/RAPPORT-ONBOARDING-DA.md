# RAPPORT — ONBOARDING : MISE EN PAGE ET ÉTATS

Branche `fix/onboarding-da`. Référence : `maquette-onboarding-v1.html` (validée Vic). Régime autonome,
commits par lot O1→O4. Le parcours est rendu côté serveur (`coffre_ui.page` + `onboarding.py` / `auth.py`).

## O1 — LE CONTENU SE CENTRE DANS LA HAUTEUR
`coffre_ui.page` restructuré : `<main class="bloc">` devient une **colonne flex pleine hauteur**
(`min-height:100vh`) — le contenu vit dans `.top` (`flex:1`, centré verticalement), le pied dans
`.foot` (collé en bas). Plus aucun grand vide sous le contenu ; les écrans longs défilent (min-height,
pas height). Le body n'est plus centré par flex (l'ancienne règle mobile `align-items:flex-start` qui
collait le contenu en haut sur téléphone est supprimée — c'était la cause du vide). Pied légal PARTAGÉ
(`FOOTER_LEGAL`) servi via `foot=` sur login, 2FA, invitation et tous les écrans client ; l'activation
admin reste sans (interne). Pages légales : lecture du haut (`.legalpage .top`). Vérifié à 390, 768,
1440 et fenêtre courte 600 (le `.top` remplit la hauteur, rien n'est coupé ni collé au bord).

## O2 — LES BOUTONS DISENT LEUR ÉTAT
Deux états, comme la maquette : **allumé** (vert menthe, texte sombre, ombre) par défaut ; **éteint**
(`.off`/`[aria-disabled=true]` : fond sombre #141A17, texte gris **lisible** #7A857E ~4:1, bordure
discrète, sans ombre). Le bouton d'invitation est **éteint** tant que la case CGV n'est pas cochée,
**allumé** à la coche (transition immédiate, la flèche apparaît). Le **message d'erreur permanent
disparaît** — l'état visuel le remplace ; il ne s'affiche QUE si l'utilisateur force le clic sur un
bouton éteint (`preventDefault`). Le bouton n'est **jamais** HTML-`disabled` (submit natif = filet,
la validation `required` + le serveur restent — pas de cul-de-sac si le JS échoue). Accessibilité :
`aria-disabled`, focus visible conservé. Vérifié Playwright : off=#141A17 → on=#4ADE80 à la coche.

## O3 — RESPIRATION, HIÉRARCHIE, USAGE DU VERT
Hiérarchie à trois niveaux : titre (Space Grotesk 17px espacé), sous-titre d'offre en une ligne (avec
`.free` **vert** pour « sans engagement »), phrase d'accueil `.lede` (corps gris clair), mentions en
petit gris foncé. Champs à **54px** (zone tactile ≥52px, 16px anti-zoom iOS), labels aérés, boîte CGV
élargie, marges latérales mobiles (le texte ne touche pas les bords). **Le vert redevient un accent** :
sur `/flash`, le paragraphe intégralement vert devient un **prix affiché en grand** (79 € · paiement
unique) + **5 lignes scannables à puces vertes**. **Mauve absent** de tout le parcours (réservé à l'IA).
Palette alignée sur la maquette validée (`--mint #4ADE80`, `--mint-dim #2E9E5B` pour liens & puces) —
elle harmonise aussi le CTA avec l'oiseau, déjà en #4ADE80.

## O4 — TEXTES ET ÉCRANS RETRAVAILLÉS
- **Invitation client** : sous-titre « Intégral · 349 €/mois · sans engagement » (valeurs d'`offres.py`),
  « sans engagement » en vert (argument commercial), phrase d'accueil raccourcie (maquette).
- **Paiement interrompu** : devient utile — bouton d'action « Reprendre le paiement » + encadré humain
  « Un doute avant de payer ? Écrivez à **victor@labuse.immo** — je réponds moi-même, et je peux vous
  ouvrir un accès d'essai de 48 h. » L'adresse vient de la config (`contact_email`, plus en dur).
- **/flash** : prix en grand, 5 lignes, et sous le bouton « Vous vérifiez la parcelle avant de payer. »
- **Mot de passe oublié** : sous le bouton « Le lien est valable une heure et ne sert qu'une fois. »
  (durée réelle vérifiée = `demander_reset(minutes=60)` → 1 heure).
- **Activation admin** : titre équilibré sur deux lignes (`text-wrap:balance`) — il ne tient pas sur une
  à cette taille (17px, .2em, majuscules) ; l'équilibre est propre.
- Écrans de succès (bienvenue / accès ouvert / essai) : bouton `.btn` (fin des boutons inline mint).
- Textes relus : phrases courtes, vouvoiement, aucune promesse « depuis votre espace » (résiliation par
  e-mail, cohérent avec le mandat sans-engagement).

## LIVRABLE — PLANCHE-ECRANS-V2.html
`docs/audit-2026-08/ONBOARDING/PLANCHE-ECRANS-V2.html` : **24 écrans**, **48 captures** (chaque écran
en **390 px ET 1440 px**), sommaire cliquable. Écrans couverts : connexion (normal + erreur), invitation
client (décochée + **cochée**), conditions requises, activation admin, invitation introuvable, récap
abonnement, bienvenue, paiement interrompu, Flash (accueil + confirmation + attente), mot de passe oublié
(demande + réinit + demande enregistrée), 2FA (enrôlement + code + codes de secours), CGV, mentions,
confidentialité, essai 48 h, régularisation. Captures dans `planche-v2/*.png`.

## FINDINGS
- **ON-001** — l'e-mail de contact humain (`config.contact_email`) prend par défaut la valeur de la
  maquette `victor@labuse.immo` : **à confirmer par Vic** (les CGV/mentions utilisent `kampusreunion@gmail.com`,
  l'expéditeur transactionnel est `contact@labuse.immo` — trois adresses distinctes à arbitrer).
- **ON-002** — le `<script>` inline de la page **login** (bascule d'état défaut/erreur/chargement) est
  bloqué par la CSP de prod (`script-src 'self'`) : la mécanique `data-state` (spinner de chargement)
  ne s'exécute pas en production. Non bloquant (le login fonctionne sans), mais à porter en fichier
  same-origin comme `/parcours.js` dans un prochain passage. Constaté, non corrigé (hors périmètre O1–O4).

## CRITÈRES DE FIN
Aucun écran ne laisse de grand vide (vérifié captures 390 + 1440) · boutons conditionnels à deux états
accessibles · le vert ne porte plus de paragraphe · les valeurs d'offre viennent d'`offres.py` ·
gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree).
