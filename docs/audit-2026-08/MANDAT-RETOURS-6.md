# MANDAT RETOURS-6 — recette du 01/09 (matin)

**Branche : `fix/retours-6`** (neuve, depuis `main` **après** merge de `fix/retours-5`). Bloc commun habituel.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter sans écrire.
**Fin de session** : `tsc`, build, tests, puis **CC commite sur sa branche** avant le compte-rendu. Merge = Vic.

**Référence** : `docs/audit-2026-08/maquette-v7-scan-patrimoine.html`.

---

## U1 — Scan patrimoine : refondre le parcours (deux temps, un seul champ)

Constat Vic : l'écran affiche une barre de recherche **et** les deux onglets alors qu'aucun propriétaire n'est encore choisi, puis renvoie vers « la barre du haut » — soit deux champs de recherche pour une seule intention. Les onglets portent sur un propriétaire : tant qu'il n'y en a pas, ils n'ont rien à montrer.

**État 1 — à l'ouverture, aucun propriétaire :**
1. **Un seul champ**, celui de l'outil : « Nom, SIREN, IDU ou adresse » + bouton « Chercher ». Aucun autre champ à l'écran, aucun renvoi vers une autre barre.
2. **Pas d'onglets du tout** — ils n'apparaissent qu'à l'état 2.
3. Sous le champ, une ligne d'aide : « Une société, une parcelle, une adresse — LABUSE remonte au propriétaire. »
4. Un bloc **EXEMPLES** de 4 lignes cliquables (nom / SIREN / IDU / adresse) qui lancent la recherche : c'est ce qui remplace le message d'attente actuel et montre ce que le champ accepte.

**État 2 — propriétaire trouvé :**
5. Le champ de recherche **disparaît**, remplacé par un **encart propriétaire** en tête : raison sociale, SIREN et qualité, plus un lien **« changer »** qui ramène à l'état 1.
6. **Les onglets apparaissent alors** — « Ce qu'ils possèdent » (par défaut) · « Ce qu'ils construisent » — en onglets soulignés (pas en gros boutons pleins : ce sont des onglets, pas des actions). Voir la maquette.
7. Le contenu de chaque onglet est celui livré en RETOURS-5 (3 KPI + « Détail et méthode » replié + liste + compteur sous la liste), inchangé.
8. La bascule d'onglet **ne relance aucune recherche** : le propriétaire est partagé.

Vérifier au passage que la recherche par **nom d'entreprise** fonctionne réellement (pas seulement SIREN et IDU) — c'est le cas d'usage principal. Le signaler au compte-rendu si ce n'est pas branché.

## U2 — Fiche commune : survol plein

Les cartes de la fiche commune (Terrain nu, Annonces en cours — Radar, Loyers, Foncier repéré, Zonage, Risques, Population & logement, Quartiers prioritaires, et toutes les autres sections) n'ont pas le survol. Leur appliquer **l'aplat plein dégradé vert avec encre sombre** (`.hover-fill`), comme partout ailleurs : titre, sous-ligne, valeur de droite et chevron inversés. Les chips de droite (ex. « 34,4 % en PPR » en ambre) restent lisibles sur l'aplat — vérifier le contraste et ajuster leur encre au survol si besoin.

## U3 — Dépôt agence : retirer l'en-tête de l'encart

Retirer la ligne d'en-tête de l'encart de dépôt : **le libellé « DÉPÔT AGENCE · BÊTA » et la pastille ambre « drapeau fermé — invisible des clients » disparaissent tous les deux**. Le bouton de fermeture (✕) reste, aligné en haut à droite. L'état du drapeau reste piloté côté admin, il n'a pas à être répété dans l'écran.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : U1 la recherche par nom d'entreprise est-elle réellement branchée · U2 liste des cartes de fiche commune traitées. Commit fait par CC. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/retours-6
```
