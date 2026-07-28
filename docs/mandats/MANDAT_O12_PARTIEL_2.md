# MANDAT O12-PARTIEL-2 — CORRECTIFS POST-REVUE VISUELLE

**Contexte** : la revue visuelle du dossier `O12_PARTIEL_REVUE.pdf` (20 cartes) et `O12_PARTIEL_EXEMPLES.pdf` (5 cartes) a été conduite en session neuve. **Verdict : NO-GO en l'état.** La méthode de la bande de façade est validée sur le fond (12 cartes sur 20 propres, compacité 0,718 vs 0,505 au pool résiduel = la méthode produit bien des lots exploitables), mais **6 correctifs sont exigés avant EXPOSE=True**.

**Branche** : continuer sur `feat/o12-partiel` (nouveaux commits) · clone `labuse-o12` · **EXPOSE reste False** · Fable ne merge jamais.
**Attendu final** : re-run île + nouveau dossier de 20 cartes + les 5 exemples régénérés → nouvelle revue en session neuve.

**Le vivier va baisser sous 139. C'est attendu et c'est sain. Ne compenser AUCUNE perte par un assouplissement de seuil.**

---

## Correctif 1 — Supprimer la colonne « Gain estimé » 🔴 BLOQUANT

La colonne affiche des valeurs négatives massives sur des fiches intitulées « Division en or » : −821 267 €, −785 696 €, −1 465 619 €, −2 179 890 €, −1 381 950 €, −1 116 462 €, −447 745 €, −414 899 €. Un « gain » de −2,1 M€ est indéfendable et détruit la crédibilité du dossier entier.

**Action** :
- Retirer la ligne « Gain estimé (Score É, Estimé) » du gabarit des fiches de revue ET de toute sortie produit liée à O12.
- Ne PAS tenter de corriger le signe ou la formule dans ce mandat.
- **Rapport attendu** : expliquer d'où vient ce chiffre (quelle fonction, quelle définition, pourquoi négatif) dans `O12_PARTIEL_RAPPORT.md`, section « Gain estimé — piste gelée ». Décision de refonte ou d'abandon sera prise par Vic séparément.

Rappel boussole : mieux vaut « non estimable » qu'un chiffre faux.

## Correctif 2 — Connexité du lot restant 🔴 BLOQUANT

Le correctif anti-enclavement garantit ≥ 12 m de façade contiguë au reste, mais **pas que le reste soit d'un seul tenant**. Sur plusieurs cartes le lot est prélevé au milieu d'une parcelle allongée, ce qui scinde potentiellement le résiduel en deux morceaux disjoints — dont un sans accès. C'est le même angle mort que le correctif F, déplacé.

Cas suspects identifiés en revue (à examiner en priorité) :
- `97410000AB0189` — Saint-Benoît (parcelle en lanière est-ouest, lot au centre, bâti à l'est)
- `97408000AC1115` — La Possession (triangle très allongé, lot au centre-nord)
- `97418000AI0768` — Sainte-Marie (même configuration)

**Action** : ajouter un critère de rejet — **la géométrie restante (parcelle − lot) doit être une seule composante connexe**. Toute parcelle produisant un résiduel multi-polygones est écartée.
- Attention aux artefacts de topologie : appliquer une tolérance géométrique raisonnable (buffer/snap) pour ne pas rejeter sur un slice de quelques cm² dû à la précision du cadastre. Documenter la tolérance retenue.
- **Rapport attendu** : combien de parcelles ce critère retire sur les 139, et la liste.

## Correctif 3 — Tolérance zéro sur `lot ∩ bâti` 🟠

La famille `decoupe` doit produire un **lot nu**. Sur plusieurs cartes l'emprise du lot semble recouvrir du bâti.

Cas suspects (par ordre de gravité visuelle) :
- `97416000CX0214` — Saint-Pierre (le plus net : structures visibles dans le polygone, emprise bâtie 20 %)
- `97423000AH1514` — Trois-Bassins (angle sud-ouest sur une toiture, emprise 21 %)
- `97409000AZ0485` — Saint-André (petite structure au nord du lot)
- `97413000AC0262` — Saint-Leu (emprise bâtie 25 %)
- `97403000AS1883` — Entre-Deux (bord sud au contact du bâti)

**Action** :
1. Calculer et **rendre dans le CSV** l'aire d'intersection `lot ∩ ensemble_bati` en m² pour les 139 candidats (colonne `aire_bati_dans_lot_m2`).
2. Critère de rejet : pour la famille `decoupe`, `aire_bati_dans_lot_m2` doit être **strictement nulle** (tolérance ≤ 1 m² pour absorber le bruit de numérisation, à documenter).
3. Vérifier également l'absence de contact tangent problématique : le lot ne doit pas passer à moins de 1 m d'un bâti conservé (un lot collé au mur est ininstruisible). Proposer ce garde-fou et le chiffrer avant de l'appliquer — **point d'arrêt, attendre le GO de Vic sur ce sous-point uniquement**.

## Correctif 4 — Exclure les zonages d'activité 🟠

`97405000AW1275` — Petite-Île, zonage **UEa** : l'aérienne montre une zone d'activité (hangars, panneaux photovoltaïques, camions, parkings). Le critère « bâti d'activité exclu » n'a pas mordu parce qu'il porte sur le bâti, pas sur le zonage.

La division en or vise un particulier qui détache un lot à bâtir — pas du foncier d'activité.

**Action** : exclure du gisement les zonages d'activité / économiques (familles `UE*`, et tout équivalent identifié dans les 23 PLU calibrés : zones d'activité, industrielles, commerciales, logistiques). Établir la liste exacte des libellés concernés commune par commune à partir des manifestes existants — **ne pas deviner** : si un libellé est ambigu, le lister dans le rapport et demander l'arbitrage plutôt que de trancher seul.

## Correctif 5 — Qualification des voiries en RNU 🟠

`97417000AO0329` — Saint-Philippe (RNU, PAU estimée) : le linéaire de voirie tracé en bleu traverse de la végétation alors que la route apparente est au nord-ouest.

**Action** : vérifier que le linéaire retenu pour le calcul de façade est bien une **voie ouverte à la circulation publique** et non une piste, un chemin d'exploitation ou une servitude de passage. Si la source de voirie ne permet pas de trancher, **écarter les candidats RNU dont la façade repose sur un linéaire non qualifié** — en RNU la prudence est doublée.
- **Rapport attendu** : quelle source de voirie est utilisée, quels attributs permettent (ou non) de qualifier l'ouverture à la circulation publique, combien de candidats sont concernés.

## Correctif 6 — Documenter la sensibilité au seuil de 600 m² ⚪ Documentation seule

Observation de revue : `lot = 625 m²` sur 8 cartes sur 20, et `largeur ≈ 25 m` presque partout. L'algorithme colle au plancher. Ce n'est pas un défaut, mais ça signifie que le vivier est très sensible au seuil de 600 m².

**Action** : documenter dans le rapport la distribution des lots par rapport au plancher (combien à moins de 650 m², combien à moins de 700 m²) et l'élasticité du vivier si le seuil bougeait. **Ne toucher à aucun seuil.**

---

## Livrables

1. Code + tests (nouveaux tests pour connexité, intersection bâti, exclusion zonage activité).
2. **Golden 116/116 PASS** (`LABUSE_DEV_MODE=1`, `PYTHONPATH=src`) — obligatoire à chaque commit.
3. Tiers servis intouchés au bit près : 120 / 1031 / 3587 / 72980 / 353945.
4. Re-run île complet → nouveau `pool_decoupe.csv` avec les colonnes ajoutées.
5. Nouveau `O12_PARTIEL_REVUE.pdf` (20 cartes, tourniquet sur les communes représentées) **sans la colonne Gain estimé**.
6. Nouveau `O12_PARTIEL_EXEMPLES.pdf` (5 exemples régénérés).
7. `O12_PARTIEL_RAPPORT.md` mis à jour : entonnoir avant/après chaque correctif (139 → ? → ? → ?), liste des parcelles retirées par critère, sections demandées ci-dessus.
8. **EXPOSE reste False.**

## Points d'arrêt

- **Arrêt A** : après les correctifs 1, 2 et 4 (les plus structurants), rendre les chiffres d'entonnoir intermédiaires AVANT de lancer le re-run île complet. Attendre le GO.
- **Arrêt B** : sous-point du correctif 3 (distance minimale lot ↔ bâti conservé) — chiffrer avant d'appliquer.
- **Arrêt C** : dossier complet livré → revue visuelle en session neuve.

## Interdits

- Merger.
- Assouplir un seuil validé pour compenser la baisse du vivier.
- Corriger la formule du Gain estimé (piste gelée, rapport seulement).
- Trancher seul sur un libellé de zonage ambigu.
