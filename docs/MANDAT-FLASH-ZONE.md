# MANDAT — RAPPORT FLASH : LA SECTION ZONE
Régime AUTONOME. Commits par lot (F1→F4). RÈGLES COMMUNES. Findings FZ-001→.
**Dépôt : labuse-pdf** (pas le dépôt principal). Vérifie-le à l'étape 0.
Le rapport Flash est le produit à 79 € en paiement unique : un client saisit une parcelle (ou désormais une adresse) sur /flash, paie, et reçoit un PDF. Ce mandat lui ajoute la section « Étude de zone » — ce qui ouvre le Flash aux commerçants et porteurs de projet, pas seulement aux investisseurs fonciers.

## LE CONTEXTE, PARCE QUE TU NE L'AS PAS
Le dépôt principal (labuse) vient de livrer le mandat ÉTUDE DE ZONE. Il expose un **endpoint qui rend l'étude complète d'une zone** (population, concurrents par activité, générateurs de flux, marché immobilier), et il possède déjà un rendu PDF autonome de cette étude (module pdf_zone, chaîne fpdf2, mise en page de docs/ZONE/maquette-zone-v1.html côté labuse).
Ta première tâche est donc une **enquête**, pas du code.

## F1 — ENQUÊTE : LES DEUX CHAÎNES
Établis et écris au rapport, en lisant le code des deux côtés :
- Comment le rapport Flash est produit aujourd'hui : quelle bibliothèque, quelle structure de sections, comment les données arrivent (appel HTTP au backend ? accès direct à la base ? paramètres passés au moment de la génération ?), comment une section existante est écrite.
- Comment l'étude de zone est produite côté labuse : la forme exacte des données rendues, et ce que fait pdf_zone.
- **La question qui décide de tout** : les deux chaînes utilisent-elles la même bibliothèque PDF ? Si oui, la mise en page se réutilise. Sinon, dis-le clairement et propose l'option la moins coûteuse — ne réécris pas un moteur de rendu.
- Comment le Flash obtiendra les données de zone : appel à l'endpoint du dépôt principal, ou calcul local ? Choisis, justifie, et prends garde à ne pas dupliquer la logique métier — le calcul de zone doit rester à un seul endroit.

## F2 — LA SECTION DANS LE RAPPORT
Ajoute la section « Autour de cette parcelle » au rapport Flash, mise en page fidèle à l'écran 3 de la maquette (docs/ZONE/maquette-zone-v1.html, côté labuse — va la lire) :
population de la zone · activité et concurrence · carte de la zone · marché immobilier de la zone · le pied de page des sources avec l'astérisque ESTIMÉ.
- **Les honnêtetés voyagent avec les chiffres** : ESTIMÉ sur les revenus issus de carreaux imputés, « hors trafic » sur les temps de trajet, sources et millésimes au pied, et AUCUNE prévision de chiffre d'affaires ni score d'attractivité. Un PDF part chez un client et lui survit — ces mentions y comptent plus qu'à l'écran.
- **Si l'étude de zone est indisponible** (API isochrone injoignable, zone inhabitée, données manquantes), le rapport se génère quand même, avec une section qui dit honnêtement ce qui manque. Un client qui a payé reçoit toujours son rapport. Jamais de page blanche, jamais de section muette, jamais un rapport qui échoue en entier à cause d'une section.
- La section s'insère à sa place dans le sommaire et la pagination existants.

## F3 — LE CAS DU COMMERÇANT
Le parcours /flash accepte désormais une adresse en plus de l'IDU (livré côté labuse). Vérifie que le rapport se génère correctement dans ce cas : le point d'entrée est une adresse, la parcelle est déduite, et le rapport doit rester cohérent — l'en-tête indique clairement ce qui a été analysé.
- L'activité étudiée (le code NAF de l'écran 2) : est-elle transmissible depuis le parcours Flash, ou le rapport sort-il sans activité ? Si le parcours ne la propose pas encore, **génère la section sans concurrence** (le reste garde tout son sens) et pose un finding décrivant ce qu'il faudrait ajouter au parcours côté labuse. Ne bricole pas une valeur par défaut.

## F4 — RECETTE
- Génère de VRAIS PDF et regarde-les : une parcelle de centre-ville, une parcelle des hauts (zone peu peuplée), une entrée par adresse, et le cas dégradé (étude indisponible).
- Vérifie la pagination, les débordements de texte, les tableaux coupés entre deux pages, la lisibilité à l'impression.
- Livre les PDF produits dans le dépôt (docs/ ou équivalent) — c'est la preuve du mandat, comme les captures ailleurs.

## FIN
Critères : enquête F1 écrite avant tout code · aucune duplication de la logique de calcul de zone · section fidèle à la maquette · ESTIMÉ, « hors trafic », sources et millésimes présents · aucune prévision de CA ni score · rapport toujours généré même en cas d'étude indisponible · PDF réels livrés et regardés · tests du dépôt verts (dis leur état avant/après).
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé. Tu ne merges pas.
