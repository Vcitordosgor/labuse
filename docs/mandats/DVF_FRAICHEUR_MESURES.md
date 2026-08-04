# DVF — MESURES DE FRAÎCHEUR (priorité haute Vic 04/08 — mesuré, RIEN corrigé)

## 1 · Millésime ingéré vs dernier publié : NOUS SOMMES À JOUR
- Dernier géo-DVF publié (files.data.gouv.fr) : **années 2021-2025** — le fichier 2026
  **n'existe pas** (HTTP 404). Publication d'avril 2026 = année 2025 complète ; la suivante
  (oct. 2026) apportera S1-2026.
- Base : max(date_mutation) = **31/12/2025** = l'horizon du dernier publié.
- **Complétude vérifiée au fichier** : 974/2025 publié = 7 184 mutations uniques ; base =
  **7 184**. Exact.

**Le « 7 mois d'angle mort » est donc le CYCLE DE PUBLICATION de la source, pas un retard
d'ingestion.** Rien à ré-ingérer aujourd'hui ; tout à afficher (c'est la doctrine). La sync
DVF absente de data_sources reste un défaut de traçabilité (couvert par la SPEC millésime).

## 2 · Mutations manquantes (estimation)
S1-2026 non publié ≈ volume S1-2025 : **~3 273 mutations** en attente de la publication
d'octobre. C'est l'angle mort structurel entre deux millésimes.

## 3 · Les prix serviraient-ils différents ? (proxy mesurable)
Aucun millésime plus frais n'existe → mesure du COÛT D'UN CYCLE : médiane €/m² bâti par
commune, fenêtre 36 mois finissant 06/2025 vs 12/2025 (l'apport du dernier semestre publié) :

| commune | avant | après | Δ |
|---|---:|---:|---:|
| Sainte-Marie (97418) | 10 000 | 3 423 | −65,8 % ⚠ n faible, à lire comme instabilité |
| La Possession (97408) | 4 739 | 3 797 | **−19,9 %** |
| Saint-Benoît (97410) | 3 315 | 2 716 | **−18,1 %** |
| Sainte-Rose (97419) | 1 976 | 1 721 | −12,9 % |
| Salazie (97421) | 1 500 | 1 649 | +10,0 % |

**Un cycle de publication déplace les médianes de ±10-20 % dans plusieurs communes** (au-delà
du bruit sur les petites). Servir un prix sans étiquette de fraîcheur, c'est servir un chiffre
qui peut être à 20 % du marché courant sans que le client le sache.

## 4 · La fiche affiche-t-elle une date de comparables ?
**À moitié.** Le bandeau P14 existe (`dvf_couverture` : « ventes jusqu'à déc. 2025 ») mais
n'apparaît QUE dans le tiroir Faisabilité/Bilan. **La tuile Marché d'en-tête (médiane €/m² +
« N ventes secteur ») est SANS étiquette de fraîcheur** — c'est un chiffre servi sans date.
Correctif spécifié (pas implémenté) : SPEC_MILLESIME_AMONT §4 — le même libellé sur la tuile.

## Verdict
Donnée JUSTE et À JOUR au sens du publiable — mais servie SANS étiquette là où le client la
lit. Le correctif est d'affichage + traçabilité (spec), pas de ré-ingestion. À re-mesurer à
chaque publication (avril/octobre) — la garde de fraîcheur (spec §5) l'automatisera.
