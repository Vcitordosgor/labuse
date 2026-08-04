# A1.3 — IDU / adresses manquants par commune

> Généré 2026-08-04 (train-tech). Lecture seule sur la base servie.
> Métrique « adresse » = présence d'au moins une adresse BAN (`parcel_adresse.ban_voie`
> non nul) rattachée à l'IDU. Métrique « IDU » = IDU absent/vide sur `parcels`.
> `numero` (parcels) est le numéro cadastral, toujours renseigné → non pertinent ici.

## Totaux île
- Parcelles : **431 663**
- Sans adresse BAN : **174 518 (40,4 %)**
- Sans IDU : **0**

## Par commune (tri : sans adresse BAN décroissant)

| Commune | Parcelles | Sans adresse BAN | % sans adr. | Sans numéro |
|---|---:|---:|---:|---:|
| Saint-Paul | 51129 | 21446 | 41,9 | 0 |
| Saint-Pierre | 42425 | 16603 | 39,1 | 0 |
| Le Tampon | 42756 | 15446 | 36,1 | 0 |
| Saint-Joseph | 28959 | 14408 | 49,8 | 0 |
| Saint-Louis | 29241 | 12618 | 43,2 | 0 |
| Saint-Leu | 22959 | 11508 | 50,1 | 0 |
| Saint-Denis | 38138 | 10787 | 28,3 | 0 |
| Saint-Benoît | 21671 | 8286 | 38,2 | 0 |
| Petite-Île | 13137 | 7284 | 55,4 | 0 |
| Sainte-Marie | 16746 | 6253 | 37,3 | 0 |
| Saint-André | 22600 | 6135 | 27,1 | 0 |
| Les Avirons | 8611 | 4597 | 53,4 | 0 |
| Sainte-Suzanne | 12527 | 4546 | 36,3 | 0 |
| Salazie | 7035 | 4291 | 61,0 | 0 |
| La Possession | 13338 | 4196 | 31,5 | 0 |
| L'Étang-Salé | 9070 | 3930 | 43,3 | 0 |
| Sainte-Rose | 6287 | 3787 | 60,2 | 0 |
| Cilaos | 6560 | 3465 | 52,8 | 0 |
| Entre-Deux | 6312 | 3239 | 51,3 | 0 |
| La Plaine-des-Palmistes | 6450 | 2749 | 42,6 | 0 |
| Le Port | 10195 | 2415 | 23,7 | 0 |
| Les Trois-Bassins | 5314 | 2389 | 45,0 | 0 |
| Bras-Panon | 6041 | 2108 | 34,9 | 0 |
| Saint-Philippe | 4162 | 2032 | 48,8 | 0 |

## Lecture
- **Aucun IDU manquant** : l'IDU est l'identifiant, toujours présent.
- Le déficit est **adresse BAN**, structurel : ~40 % des parcelles n'ont pas de rattachement
  BAN. Plus marqué dans les Hauts / communes rurales (Salazie 61 %, Sainte-Rose 60 %,
  Petite-Île 55 %), plus faible en zones denses (Le Port 24 %, Saint-André 27 %).
- Requête (verbatim) : `LEFT JOIN (SELECT DISTINCT idu FROM parcel_adresse WHERE ban_voie
  IS NOT NULL)` sur `parcels`, `GROUP BY commune`.

## Complément (demande Vic) — adresse BAN sur les TÊTES servies (q_v8_calibre)

La question qui tranche « bruit rural » vs « trou produit » : le déficit touche-t-il les
parcelles réellement servies en tête ? Rang = `parcel_p_score_v2.rang` sur le run servi.

| Segment servi | n | sans adresse BAN | % |
|---|---:|---:|---:|
| Top 120 têtes (rang ≤ 120) | 120 | 55 | 45,8 |
| Brûlantes (tier, 117) | 117 | 46 | 39,3 |
| Brûlantes + chaudes (1159) | 1159 | 456 | 39,3 |
| Top 1000 têtes (rang ≤ 1000) | 1000 | 410 | 41,0 |

**Réparti sur toutes les communes, y compris urbaines** (têtes brûlantes+chaudes sans BAN) :
Saint-Pierre 63 %, Saint-Louis 67 %, Saint-Joseph 63 %, Saint-Leu 58 %, Le Tampon 44 %,
Saint-Paul 35 %, Sainte-Marie 38 %, **Saint-Denis 22 %**, La Possession 21 %.

## Réconciliation (définitions Vic, 2026-08-04) — chiffre unique

- « têtes servies » = les **1 000 premiers rangs** du run servi q_v8_calibre.
- « adresse présente » = **ce que la FICHE rend réellement au champ adresse** — pas la table de
  lien, pas un géocodage. En code : `_ban_adresse` (app.py) = `adresse_parcelles` JOIN
  `adresses`, `null` si aucun lien ou voie vide → le client voit « Adresse non disponible ».

Mesuré sur l'API servie (`source=q_v8_calibre`), 0 erreur :

| Segment | n | fiche : champ adresse VIDE | % |
|---|---:|---:|---:|
| **Brûlantes (tier)** | 117 | **46** | **39,3** |
| 1000 premiers rangs | 1000 | 410 | 41,0 |

**Verdict corrigé : ce n'est PAS un non-sujet en tête.** 46 des 117 brûlantes affichent
« Adresse non disponible » au client (≈ 2 têtes sur 5). Les chiffres provisoires 5,3 % / 0 %
**ne se reproduisent sous aucune définition** : la fiche lit exactement `adresse_parcelles`,
donc le champ-vide-en-fiche = le déficit de lien BAN (mêmes ~40 %). Le « 53 » de Vic est du
bon ordre (46 brûlantes / 47 sur le top-120).

**Conséquence (train 4)** : la tâche change d'ampleur. Le libellé « Adresse : Absente (BAN) »
(jamais un champ vide) reste nécessaire, mais 46 brûlantes / 410 des 1 000 rangs sans adresse
appellent un **enrichissement adresse sur les têtes**, pas seulement un habillage.
