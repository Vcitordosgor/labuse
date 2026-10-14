# CHASSE-CALCULS-1 — RAPPORT

Audit **lecture seule** des quatre endroits où LABUSE calcule et affirme un chiffre à la place du client : taxe d'aménagement, faisabilité, gabarit, exports. Branche `audit/chasse-calculs-1`, base `labuse` locale, run servi **q_v18** (résiduel run_seq 15). Aucun correctif, aucune écriture en base, rien sur le VPS. Modèle Opus, 2026-10-14.

## VERDICT (5 lignes)

1. **Les chiffres affirmés par LABUSE sur q_v18 sont justes et cohérents** : constantes TA 2026 vérifiées contre les textes officiels (892 €/m², piscine 251, stationnement 2 928, abattement 50 %/100 m², part dép 2,5 %, RAP 0,40 %), **9/10 cas TA recalculés à la main identiques au centime**, et le banc de recalcul indépendant (494 comparaisons : TA + géométrie + résiduel + score) ne sort **qu'un seul écart d'arrondi tolérable**.
2. **Un seul écart métier neuf (E-A1)** : l'outil TA n'exprime pas l'abattement « 100 premiers m² **par logement** » → un collectif de résidences principales est **sur-taxé ~×2** (66 231 € au lieu de 34 342 € sur le cas-type) sans le dire ; direction prudente mais faux vs la règle.
3. **Les manques connus de TAXE-AUDIT-1 sont corrigés** : exonérations de plein droit (agricole/PLAI/reconstruction), RAP 0,40 % de l'assiette **identique outil ↔ Dossier** (l'ancien forfait 0,68 €/m² a disparu), part départementale 2,5 % confirmée DELTA, 24/24 taux communaux sourcés+datés, secteurs à taux majoré servis (6 communes).
4. **Deux simplifications à déclarer au client** : le 3D du Gabarit est une **extrusion à terrain plat** (la pente n'entre pas dans le volume ; E-C1), et l'outil TA ne modélise ni les exonérations **communales facultatives** (abris de jardin) ni le **stationnement majoré sur délibération** (E-A2).
5. **Réactivité** : les valeurs **servies** (fiche/Dossier/Flash/Copilote) viennent d'un **run gelé** `parcel_residuel` — une règle PLU modifiée ne les change pas tant qu'un run n'a pas rebasculé, alors que l'**outil Faisabilité** recalcule en direct (fenêtre de divergence à surveiller ; E-B1). La surface servie est bien la **contenance cadastrale** partout (CONTENANCE-1 LIVE sur q_v18, fiche = Gabarit = base, vérifié sur 3 témoins).

## Méthode & périmètre honnête

Quatre cartographies de code en parallèle (TA, faisabilité, gabarit, exports) + lecture des audits antérieurs (TAXE-AUDIT-1, SDP-VERIF-1, PPR-PARTIEL, CONTENANCE-1, GABARIT-AUDIT-1, EXPORTS-AUDIT-2, DOCS-FIX-1, CHASSE-DONNEES-1). **Couvert en profondeur** : tout le Lot A (règle officielle reconstituée des textes, 24 taux, 10 cas manuels, déclarations A4), le banc de recalcul indépendant rejoué sur q_v18, la cohérence surface fiche=Gabarit=base (C2) sur 3 témoins. **Non refait exhaustivement cette passe, appuyé sur les audits cités + le banc** : les 12 recalculs manuels de faisabilité (B1), les 8 mesures de reculs au mètre (C1 — GABARIT-AUDIT-1 : 10 parcelles, 0 faux positif), l'extraction texte 5 × 14 exports (D2 — EXPORTS-AUDIT-2 : 930/942 chiffres ralliés, 0 divergence écran/PDF). Ces trois enquêtes exhaustives sont la suite logique recommandée.

## Par lot

- **Lot A — taxe d'aménagement : JUSTE.** Constantes officielles 2026 (vérif. CGI 1635 quater H/I/J + arrêté 22/12/2025 + BOFiP), 9/10 cas exacts au centime, 24 taux sourcés, RAP corrigée, exonérations de plein droit implémentées. Écarts : **E-A1** (collectif par logement, sur-taxe), **E-A2** (exo facultatives / stationnement majoré non déclarés), **E-A3** (arrondi au centime vs euro inférieur).
- **Lot B — faisabilité : COHÉRENTE, servie d'un run gelé.** Calculateur unique, hypothèses principales affichées et éditables (coef_occupation 0,45 ; rendement 0,80 ; logement 65/80 m²) ; constantes moteur (étage 3 m, 25 m²/place) enfouies mais documentées ; SDP servie = source unique `parcel_residuel`. Écart : **E-B1** (péremption par conception + divergence transitoire outil-live ↔ fiche-gelée tant qu'un run n'a pas tourné).
- **Lot C — gabarit : SOURCE UNIQUE, surface = contenance.** Écran = PDF (`compute_gabarit`), zone d'implantation par reculs au grain arête (GABARIT-AUDIT-1), surface de base = contenance cadastrale (vérifié). Écart : **E-C1** (3D = extrusion à plat, terrain naturel non intégré au volume ; règle H/2 honnêtement marquée « non chiffrée »).
- **Lot D — exports : BUILDER PARTAGÉ, millésimes rendus.** `construire/collecte` lit le payload fiche (même donnée), « Données LABUSE au {promoted_at} » rendu en pied `@page` WeasyPrint, réserves par document, recette historiquement VERTE. Écart : **E-D1** (pré-dossier PC hybride — chiffres réglementaires via la fiche, cotes CERFA en SQL direct ; risque faible).

## Banc livré (rejouable)

```
# recalcul indépendant global (existant) — TA + géométrie + résiduel + score
PYTHONPATH=src python -m scripts.coherence.recalcul.banc_calcul           # 494 comp., 1 écart tolérable

# garde dédiée CHASSE-CALCULS-1 — 10 cas TA, épingle E-A1
PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/banc_chasse_calculs.py   # exit 0 = état conforme
```

La garde `banc_chasse_calculs.py` échoue le jour où l'un des 9 cas justes casse **ou** où E-A1 est corrigé sans mise à jour de l'audit (le cas collectif cesserait de diverger).

## Recommandations (pour CHASSE-CALCULS-FIX-1)

1. **E-A1** — ajouter `nb_logements` à l'outil TA et appliquer l'abattement 100 m² par logement (ou, a minima, afficher « abattement RP appliqué une seule fois — saisir logement par logement pour un collectif »). Priorité haute (montant faux).
2. **E-A2 / A4** — compléter la note de l'outil : exonérations communales facultatives et stationnement majoré sur délibération non modélisés ; proposer la saisie du taux 5 857 €/place.
3. **E-C1** — mention « gabarit 3D : terrain supposé plat (pente {pente_pct} % non reprise dans le volume) » sur les parcelles en pente forte.
4. **E-B1** — exposer, là où une valeur est servie d'un run, un repère « règle PLU plus récente que le dernier run » (sonde de péremption), et documenter la fenêtre run→bascule.
5. **E-A3 / E-D1** — faibles : arrondir la TA à l'euro inférieur en affichage ; rattacher les cotes CERFA du pré-dossier au payload fiche pour fermer le trou de provenance.
6. **Suite d'audit** — exécuter les trois enquêtes exhaustives laissées : 12 faisabilités recalculées à la main (B1), 8 gabarits mesurés au mètre (C1), 5 × 14 exports extraits en texte (D2).
