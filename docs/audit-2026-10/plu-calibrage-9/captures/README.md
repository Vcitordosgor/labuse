# Captures — PLU-CALIBRAGE-9 (témoin L'Étang-Salé, zone UA, PLU du 17/09/2025)

Témoin du mandat : **L'Étang-Salé AW 99 + 451 + 624 + 625**, zone **UA**.
Règle attendue : **> 1 000 m² de SDP → 20 % de logement aidé** (article UA 1.3 (1), p. 17).

## Fiche — tiroir « Mixité sociale (LLS) »

| Fichier | État | Ce que montre la fiche |
|---|---|---|
| `avant-mixite-etang-sale-UA.png` | **AVANT** (règlement non calibré pour la mixité) | Badge « non modélisée » · « Aucune clause de mixité sociale validée pour cette zone dans le règlement calibré. » |
| `apres-mixite-etang-sale-UA.png` | **APRÈS** (Lot B/C) | Badge **Sourcé** · Quota **20 %** · Seuil **1000 m² de surface de plancher** · *UA 1.3 (1) (p. 17) — « Tout projet visant à créer plus de 1 000 m²… au moins 20 %… »* |

Méthode : API `uvicorn labuse.api.app:app:8801` (base réelle) + front `vite:6001`
(`LABUSE_API_DEV=…:8801`), fiche ouverte via `#idu=97404000AW0099`. L'AVANT a été obtenu en
rétablissant temporairement le YAML pré-Lot-B (`git checkout 2c935049 -- …97404…`), puis restauré.

## Capacité — « N logements aidés imposés »

`capacite-assemblage-temoin.txt` : la 11ᵉ étape de la capacité sur l'**assemblage** des 4 parcelles
(1 746 m², zone UA) — SDP ~2 200 m² **> 1 000 m²** → la clause se déclenche :

```
STEP LLS valeur : ~4-5 logements aidés imposés
STEP LLS formule: 20 % du programme dès 1000 m² SDP — sur ~20-21 logts
STEP LLS source : UA 1.3 (1) (clause de mixité sociale) | prov sourcee
```

Sur **une seule** des 4 parcelles (501 m², SDP ~483 m² **< 1 000 m²**) la capacité affiche
honnêtement « **non imposé** » (seuil non atteint) — la clause est connue, elle ne se déclenche pas.

> Écart assumé avec l'archi : LABUSE modélise ~20-21 logements sur l'assemblage (modèle CES/niveaux/
> surface moyenne), l'archi en compte 29 (20 % × 29 = 5,8). La **règle** (« > 1 000 m² SDP → 20 % »)
> est identiquement appliquée et sourcée ; l'écart porte sur le **nombre de logements modélisé**, pas
> sur la clause de mixité.
