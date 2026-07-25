# M19 — PHASE 2 : maquettes cliquables de la fiche

3 maquettes HTML statiques, **une seule parcelle réelle** riche en données (run `q_v7_defisc`) :

> **`97418000AT2317`** — 204 Rue de l'égalité, 97438 Sainte-Marie · 274 m² · **Brûlante rang 11, ×22** ·
> propriétaire **CBO TERRITORIA** (personne morale, SIREN 452 038 805, gérant 81 ans) · 2 signaux vendeur
> (cession de fonds < 12 mois + détention longue) · zone UB, sous-densité 126 m² SDP · viabilisation confirmée
> (CISE / STEP Grand Prado / EDF SEI) · 9/11 couches risques sans aléa bloquant · ICD 90 %.

Palette = tokens **réels** du design system (`tailwind.config.js` / `tokens.ts`) : `bg #060A08`, surfaces,
`mint #5CE6A1`, `violet #B497F0`, brûlante `#E8695A`, amber `#E8B44C`. Aucune couleur inventée. Tiroirs =
`<details>` natifs cliquables. Rendus PNG : `shot_A_defaut.png`, `shot_B_densite.png`, `shot_C_groupes.png`.

## Les 3 variantes
| | Fichier | Parti pris | Fermé, ça informe |
|---|---|---|---|
| **A — défaut** | `A_defaut.html` | Fidèle à la direction validée : tiroirs empilés verticaux, verdict = en-tête de rapport, **une seule** carte accent violette (signal vendeur), respiration généreuse. | 1 valeur clé + micro-preuve par tiroir |
| **B — densité** | `B_densite.html` | Grille **2 colonnes**, typo resserrée, 2 valeurs par tiroir fermé, tout replié. Pour le pro qui scanne 100 fiches/jour. | 2 valeurs par tiroir |
| **C — groupes** | `C_groupes.html` | Tiroirs rangés sous **3 super-sections** thématiques (① Le terrain · ② Le vendeur & le marché · ③ Faisabilité & dossier). | valeur clé + résumé de groupe |

## Choix : **A est retenue** (R2)
A est la traduction fidèle de la direction validée (« fermé ça informe », drawers horizontaux empilés, carte
accent unique, verdict comme en-tête). Aucun problème concret ne force B ou C :
- **B** est excellente pour un usage expert mais rompt la respiration « calme » de la référence (densité =
  charge cognitive). On garde son idée en réserve (option « vue compacte » possible en PHASE 3, non requise).
- **C** ajoute un niveau de regroupement que la référence n'avait pas ; le gain de lisibilité ne compense pas
  la profondeur de nesting supplémentaire.

→ **PHASE 3 implémente A.** La hiérarchie 3 niveaux de P1.3 y est appliquée telle quelle.

## LOT C déjà mis en scène dans les maquettes
C1 motif « écartée » à côté du badge + « voir pourquoi → » (états dégradés) · C2 « Voir sur Pages Jaunes »
jaune · C3 adresse jamais tronquée (2 lignes possibles) · C4 cloche 🔔 (plus l'œil) · C5 exports **segmentés
qui passent à la ligne** (aucun débordement) · C6 « Banquier » → **« Note de financement »** · C7 « Cadastre ↗ »
(ouvre cadastre.gouv.fr) · C8 IA une ligne « Une question sur cette parcelle ? » en violet premium · C9 en-têtes
dégradés soignés (sans adresse / écartée / données partielles).

## Non-suppression (R1)
Toute l'info de l'inventaire P1.1 est présente : rien n'est retiré, seulement **réorganisé** en niveaux. Les
rétrogradations (badge événement legacy, flags SOFT, statut matrice historique, équipements cosmétiques) vont
en niveau 3 « voir le détail », toujours accessibles.
