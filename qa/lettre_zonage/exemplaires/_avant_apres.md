# Lettre de zonage — avant / après M147 (données réelles)

« Après » = sortie du VRAI code M147 (`_zonage`/`_regles`/`_regles_zone` importés et exécutés sur la
base `labuse`), fichier joint `_contenu_reel_apres.txt`. « Avant » = comportement mesuré en M146
(`AUDIT_M146.md` + reproduction fidèle de l'ancienne logique). Rendu binaire indisponible en local
(WeasyPrint/pango + chaîne carte) ; le contenu montré EST celui du chemin de code.

| Cas | Parcelle | AVANT (M146) | APRÈS (M147) |
|-----|----------|--------------|--------------|
| **B5 Us gelé** | `97416000EP1044` | Tableau « Hauteur 6/11 » ; `hauteur_note` imprimée **2×** ; note de GEL **coupée** par `[:2]` → **le gel jamais dit** (faux positif cardinal) | `-- Zone Us — zone gelée --` + **bandeau ⚠ « construction neuve non autorisée » AVANT le tableau** ; colonne titrée « Règle si ouverture » ; **6/11 toujours servis** ; note de gel présente ; note hauteur **1×** |
| **B5bis 2AU** | `97422000AK0771` (Le Tampon 2AUc) | idem (gel silencieux) | gel dit ; **9/13 par renvoi servis** (AUindicée→Uc) ; caveat AU |
| **Ua (5 notes)** | `97422000BV2471` | 1 note imprimée **2×**, **4 notes matérielles perdues** (alignement RD3, limites, stationnement collectif, perméabilité) | **5 notes présentes, aucune en double** |
| **B3 RNU** | `97417000AC0003` | « Zonage non résolu dans les couches numérisées — vérification en mairie » (impute un statut légal à un défaut de numérisation) | **bandeau « Commune au règlement national d'urbanisme — pas de PLU local »** + statut vérifié le 2026-07-26 ; section 3 : « non applicable — RNU » |
| **B6 ZAC** | `97415000CW1073` (AU3a) | règles PLU affirmées, aucun caveat ZAC ; note « ZAC Savane des Tamarins » coupée | règles PLU + **caveat AU générique** (« ouverture conditionnée à une opération d'aménagement d'ensemble… ZAC éventuelle à vérifier auprès de la commune, non modélisée ») |
| Nominal Uc | `97422000AD0675` | note « Annexes 3,5 m » imprimée **2×** | note **1×** ; reste inchangé |

## Non-régression vérifiée (assertions automatiques, toutes vertes)

- **Multi-zones (parts)** : B1 sort toujours Nco 50 % / Ua 48 % / Uav 2 % ; B2 Nco 64 % / Uc 35 %.
- **Millésime du PLU** : « approuvé le 11/08/2023 » (Le Tampon), 25/06/2024 (Saint-Pierre), 27/09/2012
  (Saint-Paul) — inchangé.
- **Disclaimers** L.410-1 : `LIBELLE`/`LIMITES` intacts (non touchés).
- **Zéro score/rang/tier/verdict** dans le rendu (grep vert).
- **Séparation gel vs AU** : le caveat AU n'apparaît PAS sur Us (zone U gelée) ; le bandeau gel
  n'apparaît PAS sur une zone constructible.

## Ce qui reste en dette (hors périmètre M147, signalé)

- **B2 — conflit de source lettre/fiche** : la lettre (intersection, Nco dominant) diverge de la fiche
  (centroïde → Uc). Correctif de fond amont (dette §7 M133), pas dans cette lettre.
- **F4 — exposition** : `/lettre-zonage` hors `PREFIXES_PROTEGES` ET écrit une réf. `LZ-AAAA-NNNN` en
  base à chaque appel anonyme. Inchangé ici.
