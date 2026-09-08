# MANDAT TAXE-AMÉNAGEMENT-1 — donner à LABUSE les 24 taux communaux

**Nature** : recherche de source, puis alimentation.
**Branche** : `feat/taxe-amenagement-1` depuis `main`. **Worktree** : `~/Desktop/labuse-ta1`.
**Modèle CC** : Fable.
**Constat de départ** (audit du 08/09/2026, `docs/audit-2026-09/TAXE-AMENAGEMENT.md`) : le barème national 2026 est juste et daté ; la table `taxe_amenagement_taux` est **vide, 0 commune sur 24** ; l'app dit honnêtement « taux communal non renseigné » sur six surfaces (outil dédié, fiche, Dossier, Flash, Financier, pré-dossier PC).
**Interdits** : aucun taux inventé, estimé, moyenné ou repris d'une commune voisine. Un taux sans sa délibération n'entre pas. Aucun merge, aucune bascule.

## Étape 0
`pwd`, branche, arbre propre. Copier le `.env` depuis `~/Desktop/labuse` si absent.

## Lot A — chercher la source automatique avant toute saisie manuelle
SOURCES-1 a ingéré les taux TFPB (fichier REI de la DGFiP). Vérifier si le **même jeu de données porte le taux de taxe d'aménagement**, ou s'il existe un fichier public équivalent (DGFiP, DEAL, observatoire). Regarder aussi ce que SOURCES-1 a déjà téléchargé et qui dormirait en base.
Rendre compte : source trouvée ou non, couverture 974, millésime, clé de jointure commune. **Si une source existe, elle prime sur la saisie manuelle** — l'ingérer comme les autres, avec sa fiche au registre CIRCUIT et son millésime affiché.

## Lot B — à défaut, la saisie documentée
Si aucune source automatique : préparer l'alimentation manuelle, sans inventer.
1. Un fichier de saisie (YAML ou CSV versionné) avec une ligne par commune : code INSEE, nom, taux communal, **date de délibération**, référence de la délibération, secteurs à taux majoré s'il y en a.
2. Le pré-remplir avec ce qui est **trouvable et vérifiable en ligne** (délibérations publiées, arrêtés) — chaque valeur accompagnée de son lien. Les communes introuvables restent vides, marquées « à obtenir ».
3. Le chargeur qui alimente `taxe_amenagement_taux` depuis ce fichier, avec la date de délibération conservée.
4. Rendre compte : combien de communes trouvées, lesquelles manquent, où les chercher (mairie, recueil des actes).

## Lot C — la fraîcheur
Les taux se votent avant le 1er juillet pour l'année suivante. Poser :
- le **millésime affiché** partout où le taux apparaît (« taux 2026, délibération du JJ/MM/AAAA ») ;
- une **alerte** quand un taux date de plus d'un an, sur le modèle des autres sources périmées ;
- une ligne dans la sonde des sources, pour que la couverture (X/24) soit visible au tableau de bord.

## Décision de Vic (08/09/2026)
Dans le **Financier**, le champ de saisie du taux **reste** : le client tape sa valeur, c'est plus sûr qu'un chiffre servi automatiquement sur un bilan qui part chez un banquier. Le taux connu peut être proposé à côté du champ, jamais imposé à sa place.

## Rapport
`docs/audit-2026-09/TAXE-AMENAGEMENT-1.md` : la source trouvée ou l'absence de source, le tableau des 24 communes (taux, date de délibération, lien, ou « à obtenir »), ce qui s'affiche maintenant sur chaque surface, et ce qu'il reste à faire côté Vic.
