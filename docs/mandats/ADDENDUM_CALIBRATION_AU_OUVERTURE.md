# ADDENDUM au mandat de calibration PLU — extraire le STATUT D'OUVERTURE des zones AU

> Addendum RÉDIGÉ (30/07), **NON exécuté**. Étend `MANDAT_PLU_SERIE_NUIT.md`. Motif : dette #7
> (V8-VERIF) — les YAML gravent les articles DIMENSIONNELS des AU (Art. 9 emprise, 10 hauteur,
> 13 pleine terre) mais PAS le statut d'ouverture (Art. 1 occupations / Art. 2 caractère de zone).

## Le défaut, chiffré (run servi q_v7_defisc, 24 communes)
- 187 zones AU distinctes servies ; **81 à ouverture NON documentée**.
- **420 parcelles servies EN TÊTE DE LISTE** sur ces zones : **12 brûlantes, 172 chaudes,
  236 réserve** (dont 313 en zones génériques = statut pur inconnu, 107 en « dimensions seules »).
- Conséquence : toute AU dotée d'articles chiffrés est servie CONSTRUCTIBLE sans que son ouverture
  ait été lue → même faux positif que la brûlante 2AUd du 29/07, ×12.

## Ce que l'addendum EXIGE (en plus des articles dimensionnels)
Pour CHAQUE zone AU de chaque PLU calibré, extraire l'**Article 1** (occupations et utilisations
autorisées/interdites) et/ou l'**Article 2 / caractère de la zone AU** (conditions d'ouverture),
et graver dans le YAML :
- un champ **`ouverture: ouverte | fermée | conditionnelle`** (fermée = subordonnée à modification
  du PLU / OAP non adoptée ; conditionnelle = ouverte sous condition d'opération d'ensemble/OAP) ;
- **`ouverture_src`** : article + page (comme les autres `_src`).
Puis : `resolve_zone` pose `constructible_neuf=False` pour `ouverture: fermée` (comme les 2AU) ;
la garde O12 et le déclassement tête-de-liste les traitent alors correctement.

## Priorité d'exécution (par urgence servie)
1. **4 communes portant les 12 brûlantes** : Bras-Panon (AU), La Possession (AUBm, AUAv),
   Saint-Benoît (**AUb19 = 7 brûlantes**, AUa5), Saint-Denis (AUm). — lisibles en une matinée.
2. Les 18 communes portant les 420 têtes de liste (51 zones).
3. Le reste des 81 zones AU non documentées.

## Garde-fous
- Ne RIEN inventer : une zone dont l'Art. 1/2 est illisible/absent reste `ouverture: a_verifier`
  (documentée comme non tranchée), JAMAIS supposée ouverte par convention.
- Re-golden + re-mesure des tiers après application (une AU passée fermée bouge des brûlantes).
