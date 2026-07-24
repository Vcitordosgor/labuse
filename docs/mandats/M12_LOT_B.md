# M12 — LOT B : Vocabulaire & preuve

**Branche** : `feat/m12-b-preuve` · **Base** : `main` · **Dépend de** : LOT A (A1, A3, A5).
**Golden** : 116/116 PASS (frontend-only, API/DB intouchées). **Build** : `tsc -b && vite build` 0 erreur.

> Ce lot **ne retire pas la transparence, il la traduit**. Aucune ligne de scoring touchée
> (A3 : le lift est correct). Tout le texte client est **centralisé** dans
> `frontend/src/lib/strings.ts` (objet `CLIENT`, règle R3) — Vic réécrit là, sans toucher au JSX.

## Fait

| Point | Fichier | Ce qui a changé |
|---|---|---|
| **B1** Lexique | `docs/LEXIQUE_CLIENT.md` + `frontend/src/lib/strings.ts` | Table terme technique → formulation client ; libellés appliqués centralisés |
| **B2** Cartes résultat | `panel/ResultsSection.tsx` | Le **« 92 » (anneau de complétude) retiré de la liste** (non discriminant), conservé sur la fiche ouverte (`Fiche.tsx`). `×N` gagne son **unité de sens « plus probable »** sous le nombre + infobulle B1. **Calcul inchangé.** |
| **B3** Barre de tri | `panel/ResultsSection.tsx` | Libellés B1 (`rang P` → **« classement »**) ; espacement régulier (`gap-1`, `px-2.5`). A1 a montré que les 4 tris marchent → aucune réparation de logique. |
| **B4** Bloc modèle | `sources/SourcesPage.tsx` | **Scindé** : visible = le point de confiance (« niveaux récents provisoires **mais classement fiable** ») ; replié derrière **« détail technique »** = version/sha/gel/recalage. |
| **B5** Fraîcheur | `sources/SourcesPage.tsx` + `strings.ts` | 3 statuts reformulés. **`À VÉRIFIER` → « Cadence non sondable »** avec title « la donnée affichée est bien la dernière ingérée, ce n'est pas une donnée douteuse ». Faute **« à » → « a »** corrigée. |
| **B6** Fiches source | `sources/SourcesPage.tsx` | Le **« — » isolé** de « prochaine MAJ » supprimé (la ligne ne s'affiche que si une date existe). Italique **gris-sur-gris illisible** retiré (`opacity-70`/`italic` → `text-txt-mut`). « jamais vérifiée » → « pas encore contrôlée manuellement ». |
| **B7** Précision mesurée | `sources/SourcesPage.tsx` | Section autonome **fusionnée dans l'en-tête** (bloc « preuve »). Chaque ligne **cliquable** (`<details>`) → méthode + échantillon. **Piscines retiré** (spin-off). **ANC conservé** (A8 : utilisé par FLASH). |
| **B8** Comprendre l'algo | `panel/LeftPanel.tsx` + `strings.ts` | Bouton **« Comprendre le classement »** à côté de « Analyse LABUSE affichée » → overlay 4 sections écrites client (mesure / entraînement / ×N / ce qu'il ne dit pas). |
| **B9** « masquer » | `panel/LeftPanel.tsx` | Le texte gris devient un **vrai bouton** affirmé (bordure, « Masquer »). |

## Décisions CC (défaut réversible R1)

- **B8 libellé retenu** : « **Comprendre le classement** ». Alternatives consignées : « Comment LABUSE classe », « Sur quoi repose ce classement ? » (dans `CLIENT.algo.boutonAlt`). Réversible = 1 chaîne.
- **B4/B5/B7 texte** : proposé, centralisé, **à réécrire par Vic** (voir rapport final § texte client).
- **B7 ANC** : **gardé** — A8 prouve son usage hors Vues (Flash `flash/data.py`). Piscines retiré (part au spin-off C-bis).

## Laissé volontairement / notes

- **`×N` calcul** : intouché (A3). Le « ×64.0 » de tête reste — c'est la valeur réelle (plafond du modèle). B ne fait que l'entourer d'un sens.
- **B6 refonte forme complète** : les corrections de fond (vocabulaire, dash orphelin, lisibilité) sont faites ; une refonte visuelle plus poussée de la grille (colonnes) relève de la validation à l'œil de Vic — le squelette actuel est propre et lisible.
- Le `PRECISION_PAR_SOURCE` inline par carte (IGN) est conservé tel quel ; seule la section « proof » d'en-tête a retiré Piscines.

## À relire par Vic — texte client

Intégralité recopiée dans `M12_RAPPORT_FINAL.md` § 3. Source unique : `frontend/src/lib/strings.ts`.
