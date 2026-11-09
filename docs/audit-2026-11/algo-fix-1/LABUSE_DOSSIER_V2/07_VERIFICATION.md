# Vérification du dossier — 9 novembre 2026

Version contrôlée : **ALGO-LABUSE-2 / proposition 1.0**.

## Résultats

| Contrôle | Résultat |
|---|---|
| Moteur de référence, données synthétiques | **36 invariants validés** |
| Parcours de la maquette HTML autonome | **33 contrôles validés** |
| Identifiants en liste et en analyse | **Les dix mêmes identifiants DEMO-A à DEMO-J** |
| Erreurs JavaScript observées pendant la recette | **0** |
| Requêtes réseau de la maquette autonome | **0** |
| Largeurs de navigateur testées | **1 064, 736, 360 et 320 px** |
| Débordement horizontal aux largeurs contrôlées | **Aucun détecté** |
| Captures de contrôle produites | **6** |
| Moteur et données embarqués dans le HTML | **Identiques aux fichiers de référence livrés** |

Les tests du moteur ont été exécutés avec Node 22.22.2. Les contrôles de la maquette ont été pilotés dans un navigateur Chrome isolé. Les requêtes HTTP/HTTPS ont été bloquées pour vérifier son autonomie ; aucune requête n’a été tentée dans la version finale livrée. Les bibliothèques de présentation externes inutilisées du wrapper d’export ont été retirées.

## Ce que vérifient les 36 invariants

- Disponibilité de l’API dans un navigateur et avec CommonJS.
- Conservation de l’univers d’identifiants dans les objectifs et scénarios.
- Maison sans marge additionnelle restant éligible à un Signal fourni dans son domaine fictif.
- Reconstruction continue entre 2 099 et 2 100 m² existants, sans changement de formule.
- Perte de SDP de −500 m² conservée et terrain nu sans démolition inventée.
- Absence, valeurs nulles, valeurs invalides et capacité nulle distinctes.
- Hauteur absente bloquant la SDP sans bloquer automatiquement le repérage division.
- Incompatibilité fondée sur une preuve et non sur le seul texte d’une zone.
- Grande et petite géométrie suspectes restant à vérifier.
- AU différée, capacité future facultative et absence de substitution de cette quantité à un gain net ou résiduel de tri.
- Pente observée ou inconnue visible sans coefficient inventé.
- Zonage mixte et données de la portion productive conservés.
- Seuils 0,10 et 0,20, p=0, p absent, NaN, infini et valeurs hors bornes.
- Domaine non validé, politique de démonstration et refus d’un faux mode de service de production.
- Distinction entre probabilité fournie comme servie et `p_raw`.
- Bornes documentées, enveloppe de conservation touchant zéro, reconstruction avec gain incertain, bornes incohérentes ou incomplètes.
- Tris explicites, absence de plafond à 2 000 m², groupes, nulls, égalités et identifiants stables.
- Quantités inférieures à 1 m² affichées sans être transformées en zéro.
- Pureté du moteur, ordre reproductible et refus de paramètres incompatibles.

Exécution reproductible depuis le dossier :

```sh
node 06_TESTS_REFERENCE.cjs
```

## Recette fonctionnelle de la maquette

Les contrôles couvrent notamment :

1. ouverture sur les filtres et choix liste ou analyse ;
2. liste descriptive sans badge ni verdict caché dans les faits ;
3. même univers de dix cas entre les deux sorties et sur l’ensemble des pages ;
4. tri de prospection selon les signaux fictifs et accès aux deux cas non évalués ;
5. tri de capacité, deux cas sans marge et deux cas à vérifier en conservation ;
6. AU différée avec hypothèse conditionnelle et capacité actuelle non servie ;
7. reconstruction avec différence nette négative visible et tri par gain net ;
8. repérage de division sans nombre de lots, y compris lorsque la hauteur de SDP manque ;
9. filtre N conservant à la fois un terrain N et une parcelle mixte U/N ;
10. synchronisation de la fiche sélectionnée après changement de statut ou de page ;
11. retour au panneau de résultats sur écran étroit ;
12. recherche vide restant vide, sans élargissement automatique ;
13. absence d’erreur JavaScript et de dépendance réseau ;
14. contrôle des dimensions et de la lisibilité sur les largeurs indiquées.

Les captures `captures/` montrent les états filtres, vente, conservation, reconstruction, liste étroite et détail étroit. Elles complètent le HTML interactif ; la spécification reste la référence métier.

## Vérifications documentaires

- Parcours final validé respecté : filtres actuels puis liste simple ou analyse ; pas de nouvelle catégorie ni nouvel onglet principal.
- Règles de tri différées cohérentes avec l’absence de quantités actuelles.
- Gain net signé distingué de la capacité totale.
- Programme logement explicitement limité, division seulement documentaire.
- Politique de démonstration séparée de toute activation du modèle réel.
- Date réelle de prédiction et fenêtre à préserver dans le produit, distinctes de la date de la requête.
- Fichiers autonomes, données fictives, versions rapportées et limites identifiés.

## Ce qui n’a pas été validé par ces tests

**Aucun de ces résultats ne constitue une validation de la production de LABUSE.**

Le dépôt réel, les géométries cadastrales, les règles de PLU, les données DVF, le modèle q_v15, les runs servis et les données de clients n’ont pas été utilisés pour exécuter cette recette.

Le moteur pédagogique consomme des hypothèses de géométrie, d’éligibilité et de Signal déjà déclarées dans les fixtures. Il ne démontre ni constructibilité, ni insertion d’un bâtiment, ni divisibilité, ni rentabilité, ni qualité statistique d’une prédiction.

Les métadonnées complètes, preuves géométriques, contrats de modèle et vérifications du domaine réel doivent être réalisés dans le dépôt selon `01_SPECIFICATION_ALGORITHME.md`. Les 36 invariants ne couvrent pas à eux seuls toutes les exigences de recette du produit réel.

Les anciennes tâches RESIDUEL-1/ALGO-FIX-1/DEPLOY-GROUPE-3 n’ont pas été déclarées livrées ou vérifiées ici.

## Intégrité du dossier

`MANIFEST.sha256` donne l’empreinte des fichiers livrés, hors manifest lui-même. L’archive a été relue et son intégrité ZIP vérifiée. Les notes intermédiaires de revue ne font pas partie du dossier normatif transmis.
