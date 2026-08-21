# Outil « Communes » (M137-Z) — fusion des 4 outils échelle-commune

Un seul outil `communes` (registre `frontend/src/components/outils/registry.ts`) remplace quatre entrées :
**Marché** (MU1) · **Comparateur de communes** (O6) · **Vélocité admin** (M05) · **Rareté du foncier** (O9).

- **Entrée** = la table des 24 communes (le Comparateur, `O6Comparateur`), lignes désormais **cliquables**.
- **Clic sur une commune → sa fiche** (`Communes.tsx` › `CommuneFiche`) : tous ses indicateurs sur un écran
  (rareté & horizon ZAN · vélocité · marché) + **« Voir ses parcelles → »** (filtre commune + ferme l'outil).
- Restent séparés (autre échelle) : **Baromètre** (île) et **Suivi de secteur** (secteur).

Composants réutilisés inchangés dans leur calcul : `O6Comparateur` (table), `MarcheCommune` (bloc marché
via prop `communeProp`), `M05`/`O9Rarete` conservés au dépôt (dormants, exportés). Endpoints inchangés.

## Dis lequel fait foi — source unique par indicateur

Chaque indicateur affiché dans la **fiche commune** vient d'**un seul endpoint** (« fait foi »). La **table
d'entrée** (comparateur) est explicitement une **vue de CLASSEMENT** — commodité réglable, *pas* un score
calibré (`comparateur.py:11-14`) : elle recalcule des proxys de rang depuis les **mêmes tables de base**, donc
ils ne peuvent pas diverger de source, seulement de fenêtre d'agrégation. En cas d'écart apparent, **la valeur
de la fiche fait foi**, pas la colonne de classement.

| Indicateur (fiche)                     | Fait foi (endpoint / calcul)                                   | Source de base            | Proxy de rang (table d'entrée)                    |
|----------------------------------------|----------------------------------------------------------------|---------------------------|---------------------------------------------------|
| **Foncier repéré (stock, ha)**         | `/pipeline-rarete` → `stock_opportunites_ha` (`rarete.py`)     | `parcel_p_score_v2` (run servi `Q_A_RUN_LABEL`, brûlante+chaude) | `comparateur.py:42-45` `stock` (compte, +1)       |
| **Droit à artificialiser restant / horizon ZAN** | `/pipeline-rarete` → `reste_zan_ha`, `horizon_epuisement_ans` (`rarete.py:34-62`) | `commune_conso_enaf` (Cerema) | `comparateur.py:53` `pression_zan` (conso ha, −1) |
| **Vélocité (tranche p25–p75, mois)**   | `/modules/velocite` → `delai_p25_mois`/`delai_p75_mois` (`modules.py:463-542`) | `m10_permit_delais` (SITADEL) | `comparateur.py:46-48` `velocite` (médiane, −1)   |
| **Prix ancien (bâti €/m²)**            | `/moteurs/marche/{commune}` bloc `PRIX` (`moteurs.py` `MarcheCommune`) | DVF                       | — (marché = source unique du prix affiché)        |
| **Prix de sortie neuf (€/m²)**         | `/moteurs/marche/{commune}` bloc `PRIX` (`moteurs.py`)         | `dvf_prix_sortie_neuf`    | `comparateur.py:54` `prix_neuf` (même table, +1)  |
| **Permis / dynamisme (SITADEL)**       | `/moteurs/marche/{commune}` bloc `OFFRE` (`moteurs.py`)        | `sitadel_permits`         | `comparateur.py:49-51` `permis` (24 mois, +1)     |

> Le **Simulateur ZAN** (M17, outil séparé) reste un *what-if* de trajectoire — il ne « fait foi » pour aucun
> chiffre d'état de la fiche ; la fiche sert l'horizon **mesuré** par la rareté.

## Les 3 corrections de véracité (M137-Z)

1. **Rareté** — le mot **foncier** ne porte que sur le **stock repéré** (`stock_opportunites_ha`). `reste_zan_ha`
   est dit pour ce qu'il est : **« droit à artificialiser restant (ZAN, estimé) »**, pas du foncier ni du
   constructible. Le **caveat interne monte à l'écran** (`rarete.py` `CAVEAT`, rendu dans `CommuneFiche`).
2. **Vélocité** — on sert la **TRANCHE p25–p75** (« 6 à 12 mois »), plus la médiane classée : avec des médianes
   de 8–9 mois **partout** et un IQR ~6, le classement inter-communes était du bruit. Le backend **mesure
   l'homogénéité et la DIT** (`modules.py:488-493`, `note_homogeneite`) ; le `rang_delai` a disparu.
3. **Baromètre** — la limite d'affichage du classement prix passe **en config** (`config/moteurs.yaml`
   `barometre_top_communes: 8`) et **se dit** : « les 8 premières sur 24 » (`moteurs.py`, `top_communes_cap`
   / `top_communes_total` / `top_communes_tronquee`) — plus de `LIMIT` muet. Les 24 ont la donnée (≥ 100 ventes).

## Trou de garde comblé

Aucun de ces endpoints n'avait de test « ne lève pas ». Ajouté `test_outils_commune_ne_crashent_pas`
(`tests/test_api.py`, patron `test_m136_exports_ne_crashent_pas`) : les 6 surfaces commune renvoient **200**
sur données vides (contrat data-gap, tables matérialisées vides dans `conftest.py`), et vérifie les 3
corrections (caveat présent · tranche & `communes_homogenes` · `top_communes_cap`, plus de `rang_delai`).
