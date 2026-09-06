# MANDAT FICHE-1 — Les trous de la fiche parcelle

Branche : `feat/fiche-1`, worktree `~/Desktop/labuse-audit`, depuis `main` à jour (CIRCUIT-0→5b mergés).
Compte-rendu : `docs/RECETTE/COMPTE-RENDU-FICHE-1.md`. Captures avant/après dans `docs/RECETTE/FICHE-1/`.
Autonomie : aucune question à Vic, doutes tranchés par l'option la plus sûre et écrits, lots sautés plutôt qu'attendus, branche jamais rouge, un commit et un push par lot, rien mergé.

Constat : `docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md` (généré du registre le 06/09) montre que la fiche sert 40 données réparties en 12 tiroirs — et que sept choses que Vic attend n'y sont pas, alors que la donnée existe en base ou dans un autre écran. Ce mandat les ajoute, chacune déclarée au registre comme toutes les autres.

**Règles CIRCUIT qui s'appliquent ici sans exception** : toute donnée ajoutée est déclarée dans `registre/donnees.py` (id, libellé, définition, moteur, réservoirs, portée, états) · aucune SQL de calcul dans un endpoint ou un composant · trois états distincts à l'écran, jamais confondus : servie · « non déterminée » (la source ne dit pas) · « non calculée » (la chaîne a échoué) · `labuse circuit verrous` passe en fin de chaque lot · `labuse registre fiche parcelle` régénéré et commité à la fin.

## Lot 1 — Le bâti (nouveau tiroir « Le bien »)

Aujourd'hui la fiche ne dit rien du bâtiment existant, alors que `emprise_batie_m2`, `hauteur_bati_m` et le nombre de bâtiments sont calculés pour les exports.
- Nouveau tiroir « Le bien », placé après « Constructibilité » : emprise bâtie au sol, hauteur du bâti, nombre de bâtiments (BD TOPO + CoSIA), surface au sol libre restante.
- Nature et pente du toit (LiDAR HD), aujourd'hui réservées à la fiche soleil : mêmes ids, servis ici aussi, avec les trois états de RETOURS-15 (servie · « non déterminée — pans non nets » · « non calculée — LiDAR indisponible »).
- Le tiroir est omis si rien n'est évaluable — jamais un bloc creux.

## Lot 2 — Le DPE, rétabli

`dpe_ademe` est construit côté serveur mais n'est plus affiché (commentaire `Fiche.tsx:1492`) : c'est pour ça qu'il était un « réservoir muet » avant CIRCUIT-5b. Rétablir l'affichage dans « Le bien » : classe énergétique du bâtiment principal, date du diagnostic, et le fait qu'il s'agisse du dernier DPE connu du bâtiment, pas de la parcelle. Si plusieurs DPE existent, servir le plus récent et dire combien il y en a. « Non déterminée » si aucun DPE ne se rattache.

## Lot 3 — Les aléas en détail

La fiche ne sert qu'un compte (`n_vigilances`). L'outil Pièges et risques, lui, sait dire quel aléa et à quel niveau.
- Dans « Risques et protections », la liste des aléas touchant la parcelle : nature (inondation, mouvement de terrain, …), niveau, document et date d'approbation du PPR, part de la parcelle concernée.
- Le compte `n_vigilances` reste, au-dessus de la liste.
- Même moteur que Pièges et risques : la sonde doit trouver les deux écrans d'accord (contrôle ajouté).

## Lot 4 — Le stationnement allégé (TCSP)

Règle L151-36 (loi 2025-1129) : dans un rayon de 800 m d'une station de transport en site propre, le PLU ne peut imposer plus d'une place par logement (0,5 pour le logement social). C'est un vrai levier de bilan, aujourd'hui visible seulement sur la carte.
- Dans « Réseaux et accès » : la parcelle est-elle dans le rayon, distance à la station, station nommée, et le plafond applicable — avec la référence de l'article.
- Même moteur que la couche « Stationnement allégé — TCSP », rayon depuis la station, à vol d'oiseau.

## Lot 5 — La taxe d'aménagement estimée

L'outil existe et se préremplit depuis une fiche ouverte (RETOURS-14 R26). Servir l'estimation dans « Constructibilité », pour le scénario table rase du bloc potentiel : montant, assiette, taux communal et départemental avec leur source, et le lien vers l'outil pour changer les hypothèses. Si le taux communal n'est pas connu (chantier SOURCES-1), dire « taux communal non renseigné », jamais un taux inventé — doctrine CIRCUIT-3 lot 6.2.

## Lot 6 — Les annonces Radar

La fiche ne montre pas les annonces rattachées à la parcelle alors que le rattachement BAN existe et que la fiche annonce vit ailleurs.
- Dans « Marché et secteur » : les annonces Radar rattachées à cette parcelle, datées, avec prix demandé, statut (en cours, retirée, vendue) et lien vers la fiche annonce.
- Et, s'il y a une annonce en cours et une mutation DVF : l'écart entre prix demandé et prix acté, id existant `ecart_demande_acte_pct`.

## Lot 7 — Ce qui attend une source

Ces données sont demandées par Vic mais leur source n'est pas ingérée (chantier SOURCES-1, CIRCUIT-3 lot 6.3) : emplacement réservé, EBC, DPU, PEB, zonage A/B/C. Ne rien inventer. Les déclarer au registre avec l'état « non calculée — source absente » et la source attendue nommée, pour qu'elles apparaissent dès l'ingestion et que Vic voie le trou. Une ligne au compte-rendu par donnée.

## Lot 8 — Recette

- Ordre des tiroirs revu une fois l'ensemble en place : identité, urbanisme, dispositifs, score, constructibilité, le bien, risques, marché, réseaux, autour, propriétaire, division, solaire, confiance. Un tiroir vide ne s'affiche pas.
- Captures avant/après sur trois parcelles : une bâtie avec DPE et PPR, une nue, une dans le rayon TCSP.
- `labuse circuit verrous` vert, `labuse registre fiche parcelle` régénéré, suites backend et vitest vertes, rien mergé.
