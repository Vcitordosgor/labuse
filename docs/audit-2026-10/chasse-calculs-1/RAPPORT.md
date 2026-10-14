# CHASSE-CALCULS-1 — RAPPORT

Audit **lecture seule** des quatre endroits où LABUSE calcule et affirme un chiffre à la place du client : taxe d'aménagement, faisabilité, gabarit, exports. Branche `audit/chasse-calculs-1`, base `labuse` locale, run servi **q_v18** (résiduel run_seq 15). Aucun correctif, aucune écriture en base, rien sur le VPS. Modèle Opus, 2026-10-14.

> **MAJ passe 2 (14/10)** — B1/C1/D2/D3 exécutés en entier (12 faisabilités recalculées à la main, 8 gabarits mesurés au mètre, 5 témoins × exports extraits en texte, réactivité en transaction annulée). Verdict d'ensemble inchangé : **les chiffres servis sont justes et cohérents** ; les écarts neufs sont une **divergence inter-outils faible** (zone d'implantation Gabarit ≠ Faisabilité), **deux moteurs** dans le run (`gabarit` / `residuel_legacy` aux intermédiaires impossibles), une **couverture Gabarit à ~79 %**, et surtout la **non-réactivité prouvée** du couple SDP/run : un Dossier régénéré peut mêler une surface à jour et une SDP périmée. Détail : E-B1/B2/B3, E-C2 (ECARTS.md) et §Par lot ci-dessous.

## VERDICT (5 lignes)

1. **Les chiffres affirmés par LABUSE sur q_v18 sont justes et cohérents** : constantes TA 2026 vérifiées contre les textes officiels (892 €/m², piscine 251, stationnement 2 928, abattement 50 %/100 m², part dép 2,5 %, RAP 0,40 %), **9/10 cas TA recalculés à la main identiques au centime**, et le banc de recalcul indépendant (494 comparaisons : TA + géométrie + résiduel + score) ne sort **qu'un seul écart d'arrondi tolérable**.
2. **Un seul écart métier neuf (E-A1)** : l'outil TA n'exprime pas l'abattement « 100 premiers m² **par logement** » → un collectif de résidences principales est **sur-taxé ~×2** (66 231 € au lieu de 34 342 € sur le cas-type) sans le dire ; direction prudente mais faux vs la règle.
3. **Les manques connus de TAXE-AUDIT-1 sont corrigés** : exonérations de plein droit (agricole/PLAI/reconstruction), RAP 0,40 % de l'assiette **identique outil ↔ Dossier** (l'ancien forfait 0,68 €/m² a disparu), part départementale 2,5 % confirmée DELTA, 24/24 taux communaux sourcés+datés, secteurs à taux majoré servis (6 communes).
4. **Deux simplifications à déclarer au client** : le 3D du Gabarit est une **extrusion à terrain plat** (la pente n'entre pas dans le volume ; E-C1), et l'outil TA ne modélise ni les exonérations **communales facultatives** (abris de jardin) ni le **stationnement majoré sur délibération** (E-A2).
5. **Réactivité** : les valeurs **servies** (fiche/Dossier/Flash/Copilote) viennent d'un **run gelé** `parcel_residuel` — une règle PLU modifiée ne les change pas tant qu'un run n'a pas rebasculé, alors que l'**outil Faisabilité** recalcule en direct (fenêtre de divergence à surveiller ; E-B1). La surface servie est bien la **contenance cadastrale** partout (CONTENANCE-1 LIVE sur q_v18, fiche = Gabarit = base, vérifié sur 3 témoins).

## Par lot — passe 2 (enquêtes exhaustives)

- **B1 — 12 faisabilités à la main : JUSTE sur les constructibles.** Chaîne reconstituée depuis le règlement (article + page) : CES × contenance → reculs → niveaux (hé ÷ 3) → occupation 0,45 → SDP → logements ; chaque maillon tombe juste (ex. Ste-Rose AK0909 2 737 × 70 % × 0,45 × 3 = 2 586 m² = servi ; St-Joseph BV0419 chaîne exacte). Écarts : **E-B1** (SDP servie figée, prouvée en D3), **E-B2** (Gabarit ≠ Faisabilité sur la zone d'implantation, 0,6–2,7 %), **E-B3** (moteur `residuel_legacy` aux intermédiaires > 100 %), contenance NULL → outil calcule sur le dessin, RNU St-Philippe = outil muet (honnête).
- **C1 — 8 gabarits mesurés au mètre : GÉOMÉTRIE JUSTE.** Zone d'implantation toujours **dans** la parcelle (0 débordement), reculs exacts à ±0,05 m (alignement = 0 compris), **PPR rouge découpé** (Z∩rouge = 0). Écart : **E-C2** (status `incomplete` sur ~21 % des parcelles à potentiel → ni zone ni plafond) + rappel **E-C1** (3D terrain plat).
- **D2 — 5 témoins × exports : « même donnée » TENU.** Surface et SDP servies identiques fiche↔Dossier ; millésime = date du run (pas de génération) ; 0 None/null ; garde-fous légitimes (Bilan 422 sans achat/revente, Comparatif ≥ 2, Gabarit 422 si incomplete). Note D4 : sources **par nom sans millésime par source** (PAGE-SOURCES-1) → une seule date globale.
- **D3 — réactivité (transaction annulée, rollback) : le run gelé NE BOUGE PAS.** Après +10 000 m² de contenance, la surface réagit (fiche + Dossier) mais la **SDP reste figée** (3 095 → 3 095, `parcel_residuel`) et le **cache de fiche sert périmé**. **Risque** : un même Dossier mêle surface fraîche (12 983) et SDP périmée (sur 2 983) → ratio faux jusqu'au re-run.

## Méthode & périmètre honnête

**Passe 1** : quatre cartographies de code (TA, faisabilité, gabarit, exports) + lecture des audits antérieurs ; Lot A entier (règle reconstituée des textes, 24 taux, 10 cas manuels, A4), banc de recalcul indépendant, cohérence surface fiche=Gabarit=base. **Passe 2 (ce commit)** : les enquêtes exhaustives sont **faites sans appui sur les anciens audits** (la contenance et les règles PLU ont changé) — **B1** 12 faisabilités recalculées à la main depuis le règlement cité (harnais `_harness.py`), **C1** 8 gabarits mesurés au mètre en PostGIS (`_mesure_gabarit.py`), **D2** 5 témoins × exports extraits en texte et confrontés à la fiche (`_exports_d2.py`), **D3** réactivité en transaction annulée (`_reactivite_d3.py`). Résultats détaillés dans CALCULS-MANUELS.md (§ B1, C1, D2, D3). Tout est en lecture seule : aucune écriture durable (D3 fait un rollback vérifié).

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

# passe 2 (nécessitent LABUSE_DATABASE_URL + l'app en-process) :
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse PYTHONPATH=src python \
  docs/audit-2026-10/chasse-calculs-1/_harness.py B1          # B1 : règlement vs outil/fiche/Gabarit
  …/_mesure_gabarit.py      # C1 : reculs mesurés au mètre (Z⊂P, d(Z,bord), PPR rouge)
  …/_exports_d2.py          # D2 : exports PDF→texte confrontés à la fiche
  …/_reactivite_d3.py       # D3 : réactivité, transaction annulée (rollback vérifié)
```

La garde `banc_chasse_calculs.py` échoue le jour où l'un des 9 cas justes casse **ou** où E-A1 est corrigé sans mise à jour de l'audit. Les quatre harnais de passe 2 impriment chacun leur verdict (reproductibles sur q_v18).

## Recommandations (pour CHASSE-CALCULS-FIX-1)

1. **E-A1** — ajouter `nb_logements` à l'outil TA et appliquer l'abattement 100 m² par logement (ou, a minima, afficher « abattement RP appliqué une seule fois — saisir logement par logement pour un collectif »). Priorité haute (montant faux).
2. **E-A2 / A4** — compléter la note de l'outil : exonérations communales facultatives et stationnement majoré sur délibération non modélisés ; proposer la saisie du taux 5 857 €/place.
3. **E-C1** — mention « gabarit 3D : terrain supposé plat (pente {pente_pct} % non reprise dans le volume) » sur les parcelles en pente forte.
4. **E-B1 (relevé en priorité après D3)** — empêcher qu'un export mêle du vif et du gelé : soit recalculer la SDP à la volée dans l'export, soit figer **toutes** les données d'un export sur le run (surface comprise) pour qu'un Dossier reste cohérent ; ajouter une sonde « donnée plus récente que le run » et un TTL/clé-contenu au cache de fiche.
5. **E-B2 / E-B3** — réconcilier le « moteur gabarit » cité par la Faisabilité avec le Gabarit lui-même (une seule zone d'implantation) ; retirer `residuel_legacy` du service ou brider ses intermédiaires impossibles (taux > 100 %).
6. **E-C2** — chiffrer et réduire le taux de Gabarit `incomplete` (~21 % des parcelles à potentiel) : quelle donnée réglementaire manque, par commune.
7. **E-A3 / E-D1** — faibles : arrondir la TA à l'euro inférieur en affichage ; rattacher les cotes CERFA du pré-dossier au payload fiche.
