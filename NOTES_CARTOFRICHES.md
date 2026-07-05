# NOTES CARTOFRICHES — Vague C1 (friches Cerema)

## État : TEMPS 1 (reco) fait — STOP validation Vic avant persistance
Branche `ingestion/cartofriches` (jamais mergée). Base `openclaw@…/labuse`.

## API — vérifié live 05/07/2026 (INSEE 97415)
- **Host : `https://apidf-preprod.cerema.fr`** (⚠ `apidf.cerema.fr` NE résout PAS ; le host public
  réellement servi est `apidf-preprod`). Sans clé, sans auth. Licence ouverte 2.0.
- Endpoints Cartofriches :
  - `/cartofriches/friches/?code_insee=…` (ou `coddep=974`, ou bbox) → JSON `{count,next,previous,results[]}`,
    résumé par friche (pagination DRF : `page`, `next` = URL page suivante).
  - `/cartofriches/geofriches/?code_insee=…` → **GeoJSON FeatureCollection** (géométrie **MultiPolygon**
    + mêmes propriétés résumé, dont `unite_fonciere_refcad`). ← source géométrie.
  - `/cartofriches/friches/{site_id}/` → **détail 78 champs** (les « 30+ indicateurs »).
- Pas de header rate-limit exposé → throttle prudent (leçon INPI), pagination throttlée.
- **Couverture DOM : 974 = 373 friches** ; Saint-Paul = 9. Correct (pas exhaustif mais réel).

## Champs clés (vérifiés, pas devinés)
- `site_id` (ex. `97415_10812`), `site_nom`, `site_statut` (« friche avec projet » / « sans projet »),
  `site_surface`, `site_vocadomi` (mixte…), `nature`, `source_nom`.
- **`unite_fonciere_refcad`** = LISTE d'IDU 14 car. (ex. `['97415000BH0152', …]`) → **rattachement
  parcelle EXACT** (bien mieux qu'un `ST_Intersects`). Fallback polygone via la géométrie /geofriches.
- Pollution : `sol_pollution_existe`, `sol_pollution_origine`, `site_numero_basol/basias`.
- Urba : `urba_zone_type` (U…), `urba_zone_lib`, `urba_doc_type` (PLU).
- Propriétaire : `proprio_personne` (personne morale…), `proprio_type`.
- Potentiels de reconversion : `p_residentiel`, `p_industriel`, `p_tertiaire`, `p_equipement`,
  `p_culturel`, `p_renaturation`, `p_pv` + `taux_artif_ff`.
- ⚠ **Pas d'« indice de mutabilité » en un champ unique** dans cette API (le score mutabilité
  « Mutafriches » est un OUTIL séparé). Le signal mutabilité ici = `site_statut` + `site_vocadomi`
  + potentiels `p_*` + `site_reconv_*`. À expliciter, ne rien inventer.

## Échantillon Saint-Paul (calculé en mémoire, RIEN persisté)
- **9 friches**, 148 IDU refcad distincts → **147/148 parcelles rattachées EXACT** (idu ∈ refcad
  présentes en base). 1 seul IDU absent (parcelle disparue/fusionnée).
- 5 exemples : `97415_10812` FRICHE DE SAVANNA (avec projet, 2 022 796 m², 24 parcelles) ;
  `97415_20321` (avec projet, 477 321 m², 115 parcelles) ; `97415_20330` AGORAH (62 868 m², 3) ;
  `97415_36909` / `_36910` (sans projet, ~1-2 500 m², 1 parcelle).
- Sources : « Appel à projet Fonds Friches » + « AGORAH » (agence régionale).

## Proposition stockage (TEMPS 2 — Vic tranche)
- **Reco : `spatial_layers` kind='friche'** (géométrie /geofriches en MultiPolygon) + `attrs` jsonb
  portant les champs détail utiles (statut, surface, pollution, urba, proprio, potentiels, refcad,
  source). Cohérent avec le pattern Géorisques. Croisement EXACT via `refcad` (idu) + fallback polygone.
- Alternative : table dédiée si on veut requêter en colonnes les 78 champs (plus lourd ; l'étage 1/2
  n'en aura probablement besoin que d'une poignée → jsonb suffit).

## TEMPS 2 — passe 974 FAITE (05/07, 336 s, zéro erreur)
Commande `labuse ingest-cartofriches` (24 communes, résumable, throttle 0,15 s, détail 78 champs).
- **372 friches** en base, **22/24 communes** (Saint-Leu & Sainte-Marie = 0 friche).
- Top : Saint-Pierre 45, La Plaine-des-Palmistes 43, Saint-Louis 42, Cilaos 32. Majorité « sans
  projet » (inventaire) ; « avec projet » concentré Le Port 9 / Saint-Denis 6 / Saint-Louis 7.
- **Parcelles croisées île : exact refcad 1 057 · polygone 1 801.**
- Stockage `spatial_layers` kind='friche' + attrs jsonb (résumé + détail curé + refcad). Fraîcheur
  `data_sources` posée. # TODO étage 1/2 (data pure). Branche prête, NON mergée.

## Hors périmètre
- UrbanSIMUL, Mutafriches (outils de saisie/simulation) — on prend juste l'inventaire open data.
