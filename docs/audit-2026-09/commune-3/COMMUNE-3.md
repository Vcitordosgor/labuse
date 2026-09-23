# COMMUNE-3 — Chemin « Marché des annonces (Radar) » (retraits front)

Chemin : Outils → **Communes** → porte « Marché des annonces (Radar) » → panneau plein écran (`RadarTablePanel`).
Branche `fix/commune-3`, base main `6684ba54`. Retraits front purs, aucune donnée Radar touchée.

## Les 4 retraits

| # | Retrait demandé | État | Où |
|---|---|---|---|
| 1 | Encart du bas « PRIX AFFICHÉS VS PRIX ACTÉS » | **FAIT** | `RadarMarche.tsx` — composant `SignauxCommune` (+ `EcartLigne`) supprimé, plus son rendu |
| 2 | Ligne « — = échantillon insuffisant (moins de 5 biens). Hors scoring. Données issues de la collecte manuelle. » | **FAIT** | `RadarMarche.tsx` — `<p>` de bas de tableau supprimé |
| 3 | Carrés de couleur en 1ʳᵉ colonne du tableau (texte de la ligne gardé) | **FAIT** | `RadarMarche.tsx` — composant `Chaleur` supprimé du `<td>` ; `{l.commune}` conservé |
| 4 | Mention du haut « — N biens collectés à ce jour » | **FAIT** | `Communes.tsx` — suffixe du `<h2>` retiré ; titre = « Marché des annonces (Radar) » |

Nettoyage induit (tsc `noUnusedLocals`) : imports `getRadarSignaux`/`RadarEcart`/`useState` retirés ; prop `max` et calcul `max` (heatmap) retirés ; binding `rm` inutilisé retiré (la requête de préchauffage du cache est conservée). `tsc --noEmit` = 0.

## Preuve DOM (panneau ouvert, données réelles 103 biens)

| Sonde | Avant | Après |
|---|---|---|
| `<h2>` | `Marché des annonces (Radar) — 103 biens collectés à ce jour` | `Marché des annonces (Radar)` |
| carrés couleur (`td span.inline-block`) | 24 | 0 |
| encart « Prix affichés vs prix actés » présent | oui | non |
| ligne « échantillon insuffisant (moins de… » présente | oui | non |
| lignes du tableau | 25 (24 communes + île) | 25 (inchangé) |

## Captures

- `avant.png` — haut du panneau : titre avec « — 103 biens collectés à ce jour », carrés de couleur en 1ʳᵉ colonne.
- `apres.png` — haut du panneau : titre nu, plus de carrés (texte communes conservé).
- `apres-bas.png` — bas du panneau : le tableau se termine sur la dernière ligne, plus d'encart « Prix affichés vs prix actés » ni de ligne de note.
