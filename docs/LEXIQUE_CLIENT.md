# LEXIQUE CLIENT — LABUSE (proposition M12-B1)

> **But** : traduire chaque terme d'ingénieur exposé à l'écran en une formulation qu'un
> promoteur qui n'a jamais fait de statistiques comprend **sans infobulle**. L'infobulle
> explique le détail, jamais le sens de base.
>
> **Statut** : PROPOSITION. Ces libellés sont centralisés dans
> `frontend/src/lib/strings.ts` (objet `CLIENT`). Vic les réécrit là, sans toucher aux
> composants. Ce fichier est le tableau de correspondance ; `strings.ts` est la source
> appliquée.
>
> **Ne touche à AUCUN calcul** (A3 : le lift est correct). On réhabille l'affichage.

| Terme technique à l'écran | Où | Formulation client retenue | Infobulle (détail) |
|---|---|---|---|
| `rang P` | barre de tri, fiche | **« Classement »** (bouton : « classement ») | « Classement de la parcelle sur les 428 239 parcelles analysées : n°1 = la plus prometteuse. » |
| `×N` / `×13.1` / lift | cartes résultat, fiche | **« ×N plus probable »** — jamais le nombre nu ; toujours suivi de l'unité de sens | « Cette parcelle est classée N fois plus haut que la moyenne du parc analysé. Plafond ×64 = certitude maximale du modèle. » |
| `Score Q` | filtres, fiche | **« Potentiel constructible »** (0-100) | « Qualité intrinsèque de la parcelle : règles PLU, risques, terrain. 100 = idéal. » |
| `SDP` | filtres, fiche | **« Surface constructible restante (m²) »** | « Surface de plancher encore mobilisable sur la parcelle, après le bâti existant. » |
| le `92` des cartes | (retiré de la liste) | **« Complétude des données »** — visible seulement sur la fiche ouverte | « Part des sources disponibles pour cette parcelle. N'est PAS une note de qualité du terrain. » |
| `À JOUR` | fiche source | **« À jour »** (vert) | « Donnée dans la cadence de publication du producteur. » |
| `MAJ ATTENDUE` | fiche source | **« Mise à jour disponible »** (ambre) | « Le producteur a probablement publié plus récent — rafraîchissement à lancer côté LABUSE. » |
| `À VÉRIFIER` | fiche source | **« Cadence non sondable »** (gris) — **PAS** « donnée douteuse » | « Ce producteur ne publie pas de calendrier vérifiable automatiquement. La donnée affichée est bien la dernière que nous ayons ingérée. » |
| « cadence du producteur » | fiche source | **« rythme de publication de la source »** | — |
| « prochaine publication dépassée » | fiche source | **« une version plus récente est probablement parue »** | — |
| `×64.0` en tête (5 parcelles) | cartes | affichage inchangé, mais l'unité de sens (« plus probable ») lève l'ambiguïté du « 64 » rond | « Plafond du modèle : ces parcelles sont jugées certaines de muter (probabilité maximale). » |

## Notes de traduction

1. **`rang P` → « Classement »** : « rang P » évoque une lettre de scoring interne. « Classement »
   est immédiat. La lettre P (le modèle) reste dans le détail technique replié.
2. **`×N` ne s'affiche JAMAIS seul** (règle B2). Sur la carte, le gros nombre `×13.1` reste,
   mais il gagne un micro-label « plus probable » dessous, et son infobulle donne le sens complet.
3. **`À VÉRIFIER` est le point le plus dangereux** (B5) : aujourd'hui il se lit « donnée douteuse ».
   Il veut dire « le producteur n'expose pas de calendrier sondable ». Le nouveau libellé
   **« Cadence non sondable »** + l'infobulle « la donnée affichée est bien la dernière ingérée »
   inversent l'effet.
4. Ces libellés sont **des propositions**. Vic tranche la voix. Le code lit `CLIENT.*` :
   changer le texte = éditer `strings.ts`, rien d'autre.
