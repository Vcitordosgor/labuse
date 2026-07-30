# GPU-PILOTE — RAPPORT PAQUET B (4 communes à jour)

> 97415 Saint-Paul · 97416 Saint-Pierre · 97419 Sainte-Rose · 97423 Les Trois-Bassins.
> Extraction : `config/calibrage/extraction_paquetB.yaml`. Rien écrit en base, aucun YAML modifié.
> Garde-fou sha : **4/4 concordant**.

## Saint-Paul (97415)
- **Enregistrements** : AU très granulaire (~24 codes indicés AU1b…AU6st), 0 conflit OAP chiffré en texte.
- **a_verifier** : OAP (413 p — extraction à approfondir) + ~24 sous-secteurs — motif : volume du document.
- **Faits nouveaux** : statut d'ouverture AU (**conditionnée à modification**, p.59) + granularité AU indicée non individualisée par le YAML.
- **sha** : concordant (20251217).

## Saint-Pierre (97416)
- **Enregistrements** : AU à `name`=description (garde-fou 21077) ; **conflits OAP nombreux** (densité/social par site).
- **a_verifier** : appariement zone↔polygone OAP (densité par site) — motif : la densité vient de l'OAP, pas du règlement.
- **Faits nouveaux** : **planchers de densité par OAP 50/60/80 log/ha + % social 20-40%** — absents du YAML. Même mécanique de prévalence OAP que L'Étang-Salé, mais **plus riche**.
- **sha** : concordant (20240625).

## Sainte-Rose (97419)
- **Enregistrements** : AU ouverture **`conditionnelle_etat_tiers`** ; 0 OAP chiffrée.
- **a_verifier** : liste des 1AU conditionnantes + statut de l'exception nommée **1AUc** — motif : chaîne de phasage.
- **Faits nouveaux** : dépendance de phasage — « qu'une fois l'aménagement de l'ensemble des zones 1AU indicée entrepris, **hors 1AUc** » (p.7). Le YAML ne porte pas de dépendance inter-zones.
- **sha** : concordant (20190504, PLU ancien mais en vigueur).

## Les Trois-Bassins (97423)
- **Enregistrements** : 1AUa/b/c/e/t + 2AUa/b/c + AUs/AUse ; ouverture à deux régimes (1AU vs 2AU).
- **a_verifier** : appariement AUa/b/c ↔ 1AU/2AU + AUse — motif : indices de phasage vs secteurs.
- **Faits nouveaux** : **plancher de densité 35/30/20 log/ha (AUa/AUb/AUc, p.66)** + **phasage 2AU→1AU** (p.65, ton cas-type). Les deux absents du YAML.
- **sha** : concordant (20220602).

## Le fait structurant du paquet
La variété se confirme et **le schéma tient sur les 4** :
- ouverture : `conditionnelle_operation` (Saint-Paul, Saint-Pierre) et `conditionnelle_etat_tiers`
  (Sainte-Rose, Les Trois-Bassins 2AU) — les deux via `dependance`.
- planchers de densité : **présents** ici (Les Trois-Bassins 35/30/20 au règlement ; Saint-Pierre
  50/60/80 via OAP), **absents** chez Saint-Paul. → confirme : les planchers existent mais varient,
  ni universels ni propres à L'Étang-Salé.
- `name`=description sur Saint-Pierre → lire l'ouverture dans le texte, jamais le préfixe.

**Aucun cas non descriptible → pas d'arrêt.** Reste du bloc « à jour » : 97424 Cilaos (paquet C
partiel, en attente des retéléchargements A/B/C pour compléter les paquets suivants).
