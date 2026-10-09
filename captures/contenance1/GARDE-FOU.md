# CONTENANCE-1 — garde-fou « surface incertaine » (capture live, base labuse)

**750 parcelles** concernées (contenance < moitié du dessin, écart dessin > 100 %).

5 exemples (DV0285 = port de Saint-Pierre). Faisabilité LIVE + champs servis à la fiche :

| réf | commune | dessin | contenance | incertaine | faisabilité.cause | SDP servie | prix/m² | verdict fiche |
|---|---|---|---|---|---|---|---|---|
| 97416 DV 0285 | Saint-Pierre (le port) | 117505 | 1 | oui | surface_incertaine | ∅ (aucune) | ∅ (aucun) | Analyse incomplète — surface incertaine : le plan et le cadastre ne concordent pas. |
| 97419 BH 0010 | Sainte-Rose | 966633 | 9657 | oui | surface_incertaine | ∅ (aucune) | ∅ (aucun) | Analyse incomplète — surface incertaine : le plan et le cadastre ne concordent pas. |
| 97415 AO 0009 | Saint-Paul | 660230 | 4937 | oui | surface_incertaine | ∅ (aucune) | ∅ (aucun) | Analyse incomplète — surface incertaine : le plan et le cadastre ne concordent pas. |
| 97419 BD 0015 | Sainte-Rose | 418730 | 119250 | oui | surface_incertaine | ∅ (aucune) | ∅ (aucun) | Analyse incomplète — surface incertaine : le plan et le cadastre ne concordent pas. |
| 97421 AW 0079 | Salazie | 144657 | 20646 | oui | surface_incertaine | ∅ (aucune) | ∅ (aucun) | Analyse incomplète — surface incertaine : le plan et le cadastre ne concordent pas. |

## Ce que la fiche affiche (payload `/parcels/{idu}`)

```
DV0285 (port de Saint-Pierre) :
  "surface_dessin_m2": 117505,      // le plan
  "contenance_m2": 1,             // le cadastre (acte)
  "surface_incertaine": true,
  "surface_incertaine_libelle": "surface incertaine : le plan et le cadastre ne concordent pas",
  "valeur_terrain_secteur_eur": null    // aucun prix au m² (surface indéterminée)

Tuile « Surface » (Fiche.tsx) : « Plan 117 505 m² · Cadastre 1 m² »
  sous-titre (badge) : « surface incertaine : le plan et le cadastre ne concordent pas »
Tuile « SDP restante » : « — » (sous : « surface incertaine »)
```
