# GPU-PILOTE — RAPPORT PAQUET A (4 communes à jour)

> 97401 Les Avirons · 97402 Bras-Panon · 97403 Entre-Deux · 97406 La Plaine-des-Palmistes.
> Extraction : `config/calibrage/extraction_paquetA.yaml`. Rien écrit en base, aucun YAML modifié.
> Garde-fou sha : **4/4 concordant** (archive locale = version en vigueur GPU).

## Les Avirons (97401)
- **Enregistrements** : 6 zones AU (AUa, AUc, AUd, AUec, AUes, AUt), 0 en conflit règlement/OAP (pas d'OAP chiffrée).
- **a_verifier** : sous-secteurs AUec/AUes/AUt (vocations propres) + VRD — motif dominant : chapitre 3 (réseaux) non lu.
- **Faits nouveaux** : statut d'ouverture AU = **conditionnée à une modification du PLU** (p.5, p.42) — le YAML ne le portait pas. Pas de plancher de densité.
- **sha** : concordant (20241206).

## Bras-Panon (97402)
- **Enregistrements** : AU à `name` = DESCRIPTION (identité par subtype ; garde-fou 21077) ; 0 conflit OAP chiffré, mais OAP 50% social.
- **a_verifier** : chaîne exacte de phasage (quelles 1AU indicée) + densité OAP non chiffrée — motif : dépendance inter-zones à tracer.
- **Faits nouveaux** : ouverture **`conditionnelle_etat_tiers`** — « ne pourra intervenir qu'une fois les zones 1AU indicée aménagées ». **Une DÉPENDANCE de phasage** que le YAML ne porte pas (comme Saint-Joseph 2AU→1AU). + OAP 50% social.
- **sha** : concordant (20260428).

## Entre-Deux (97403)
- **Enregistrements** : AU = « Zone d'urbanisation future » (mixte + économique), `name`=description ; 0 conflit OAP.
- **a_verifier** : distinction AU mixte vs AU éco (règles propres) — motif : sous-secteurs non séparés.
- **Faits nouveaux** : ouverture **subordonnée à une modification OU révision** du PLU (p.6, p.29) — non porté par le YAML. Pas de plancher.
- **sha** : concordant (20240924).

## La Plaine-des-Palmistes (97406)
- **Enregistrements** : 6 zones AU (AUb, AUc, AUe, AUr, AUs1, AUs2 dont AUs1/2 = réserves) ; OAP graphique non chiffrée en texte.
- **a_verifier** : OAP (densité/social, PDF image) + secteurs AUr/AUs1/AUs2 — motif dominant : OAP à composante graphique.
- **Faits nouveaux** : ouverture conditionnée à modification (p.7, p.71) **+ plancher « 10 logements LOCATIFS SOCIAUX en opération d'ensemble »** (p.54) — variante du plancher L'Étang-Salé (en LLS, pas en densité). Non porté par le YAML.
- **sha** : concordant (20230527).

## Le fait structurant du paquet
Les **planchers de densité (log/ha)** de L'Étang-Salé **ne sont PAS universels**. Ici : 0 densité
log/ha ; La Plaine a un plancher en **LLS** ; les 3 autres n'ont aucun plancher. Le « fait nouveau »
commun aux 4 est le **statut d'ouverture AU** (absent des YAML) ; les planchers/dépendances varient.

**Le schéma décrit tout** : `conditionnelle_operation` (×3), `conditionnelle_etat_tiers` (Bras-Panon,
via `dependance`), plancher en LLS (La Plaine). Aucun cas non descriptible → **pas d'arrêt**, je
continue au paquet B (97415 Saint-Paul · 97416 Saint-Pierre · 97419 Sainte-Rose · 97423 Les Trois-Bassins).
