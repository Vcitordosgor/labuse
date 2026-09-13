| id | libellé court | libellé long | seuil |
|---|---|---|---|
| priorite | Priorité | À contacter en priorité | p ≥ 0.2 (sortie 0.18) |
| a_suivre | À suivre | À suivre de près | 0.1 ≤ p < 0.2 (sortie 0.09) |
| sans_signal | Sans signal | Sans signal de vente à court terme | p < 0.1 (ou déclassé/réserve) |
| ecartee | Écartée | Écartée — motif en fiche | étage 0 — éliminée par la cascade (motif en fiche) |

## Front (frontend/src/lib/status.ts — PALIER_META)

| id | label (court) | long |
|---|---|---|
| priorite | Priorité | À contacter en priorité |
| a_suivre | À suivre | À suivre de près |
| sans_signal | Sans signal | Sans signal de vente à court terme |
| ecartee | Écartée | Écartée — motif en fiche |

**Conclusion W6** : les libellés du front sont RIGOUREUSEMENT IDENTIQUES à ceux du registre
serveur (`scoring/tiers_client.py::PALIERS_CLIENT`). Aucune différence à corriger côté front.
Un test anti-dérive garde déjà l'égalité (voir W5 pour le verrou étendu). Les seuils (`p`) vivent
en config (`scoring_client.yaml → paliers`), jamais en dur ; ils ne sont pas affichés au client.
