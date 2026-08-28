# MANDAT — RAPPORT FLASH : LA SECTION ZONE
Régime AUTONOME. Commits par lot (F1→F4). RÈGLES COMMUNES. Findings FZ-001→.
Le rapport Flash est le produit à 79 € en paiement unique : le client saisit une parcelle — ou désormais une adresse — sur /flash, paie, et reçoit un PDF. Ce mandat lui ajoute la section « Étude de zone », ce qui ouvre le Flash aux commerçants et porteurs de projet, pas seulement aux investisseurs fonciers.
Tout vit dans CE dépôt : la chaîne Flash est dans src/labuse/flash/ (report.py, data.py, carte.py) et le rendu de l'étude de zone dans pdf_zone (livré par le mandat ÉTUDE DE ZONE, voir docs/ZONE/).

## F1 — ENQUÊTE COURTE
Avant d'écrire une ligne, établis au rapport :
- Comment le rapport Flash est structuré (sections, sommaire, pagination, d'où viennent ses données via flash/data.py).
- Ce que produit pdf_zone et sous quelle forme l'étude de zone est calculée (l'endpoint /outils/etude-zone et le module zone).
- Les deux chaînes utilisent-elles la même bibliothèque ? Si oui, la mise en page se réutilise directement. Sinon, dis-le et propose le moins coûteux — tu ne réécris aucun moteur de rendu.
- **Point de vigilance** : le calcul de zone doit rester à UN SEUL endroit. Le Flash consomme le module existant, il ne recopie pas sa logique.

## F2 — LA SECTION DANS LE RAPPORT
Ajoute la section « Autour de cette parcelle » au rapport Flash, fidèle à l'écran 3 de docs/ZONE/maquette-zone-v1.html : population de la zone · activité et concurrence · carte de la zone · marché immobilier de la zone · pied de page des sources avec l'astérisque ESTIMÉ.
- **Les honnêtetés voyagent avec les chiffres** : ESTIMÉ sur les revenus issus de carreaux imputés, « hors trafic » sur les temps de trajet, sources et millésimes au pied, et AUCUNE prévision de chiffre d'affaires ni score d'attractivité. Un PDF part chez un client et lui survit — ces mentions y comptent plus qu'à l'écran.
- **Si l'étude de zone est indisponible** (API isochrone injoignable, zone inhabitée, données manquantes), le rapport se génère QUAND MÊME, avec une section qui dit honnêtement ce qui manque. Un client qui a payé reçoit toujours son rapport : jamais de page blanche, jamais de section muette, jamais un rapport qui échoue en entier à cause d'une section.
- La section s'insère à sa place dans le sommaire et la pagination existants.

## F3 — LE CAS DU COMMERÇANT
Le parcours /flash accepte désormais une adresse en plus de l'IDU. Vérifie que le rapport se génère correctement dans ce cas : la parcelle est déduite du point BAN, et l'en-tête indique clairement ce qui a été analysé.
- L'activité étudiée (le code NAF) : est-elle transmissible depuis le parcours Flash ? Si le parcours ne la propose pas encore, **génère la section sans le volet concurrence** (le reste garde tout son sens) et pose un finding décrivant ce qu'il faudrait ajouter au parcours. Ne bricole pas une valeur par défaut.

## F4 — RECETTE
- Génère de VRAIS PDF et REGARDE-LES : parcelle de centre-ville, parcelle des hauts (zone peu peuplée), entrée par adresse, et le cas dégradé (étude indisponible).
- Vérifie la pagination, les débordements de texte, les tableaux coupés entre deux pages, la lisibilité à l'impression.
- Livre les PDF produits dans docs/FLASH/ — c'est la preuve du mandat, comme les captures ailleurs.

## FIN
Critères : enquête F1 écrite avant tout code · aucune duplication de la logique de calcul de zone · section fidèle à la maquette · ESTIMÉ, « hors trafic », sources et millésimes présents · aucune prévision de CA ni score · rapport toujours généré même en cas d'étude indisponible · PDF réels livrés et regardés · gardées vertes · suite au niveau de la base (prouvé par worktree).
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/flash-zone). Tu ne merges pas.
