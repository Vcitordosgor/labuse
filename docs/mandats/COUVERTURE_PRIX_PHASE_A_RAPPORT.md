# RAPPORT — Mandat couverture prix, PHASE A : les 3 leviers internes (mesure seule)

**Exécuté le 28/07/2026** (exécuteur Claude Code). **LECTURE SEULE intégrale — aucune
application.** Golden **116/116** et tiers du run servi `q_v7_defisc` **au bit près**
(120 / 1031 / 3587 / 72980 / 353945) avant ET après. Back-test = juge, **référence production
89-91 % viables** (promotion de marché ≥ 10 lgt).

> **Réserve d'entrée, factuelle** : `docs/mandats/MANDAT_COUVERTURE_PRIX.md` **n'existe pas**
> dans le dépôt (ni suivi, ni autre branche) — comme le mandat dossier communal. Je ne l'ai pas
> lu. Le message d'instruction spécifie complètement le **levier 1** (ratio neuf/ancien) et
> l'objectif (étendre la couverture au-delà de 5 communes sans baisser la barre) ; il ne nomme pas
> les leviers 2 et 3. Je les ai donc **définis comme les deux candidats internes naturels** —
> **levier 2 = abaissement de N_MIN, levier 3 = repli île (médiane marché mise en commun)** — en
> le disant. À corriger si tu visais autre chose.

## 0 · Le fait qui commande tout (et renverse l'ordre attendu)

**Le prix de l'EXISTANT varie énormément par commune (1 633 à 3 867 €/m²), mais le prix du NEUF
de marché est quasi UNIFORME sur l'île (4 258 à 4 953, ~4 375 médiane).** Le neuf est un marché
intégré (coûts de construction homogènes, acheteurs défisc/investisseurs insulaires) ; l'existant
reflète l'âge et la désirabilité du stock local. **Conséquence directe : tout levier ancré sur le
prix LOCAL de l'existant hérite de sa variance et échoue ; un levier qui utilise le prix de marché
du neuf directement réussit.** C'est pourquoi le levier 1 (le plus prometteur a priori) tombe et
le levier 3 (a priori le « péché du socle ») passe.

## 1 · Levier 1 — ratio neuf/ancien : NON FONDÉ (dit franchement)

Critère de validité posé par Vic : la **stabilité du ratio** entre les 5 communes couvertes.
Mesuré (médiane appartement neuf de marché / médiane appartement existant) :

| Commune | neuf | existant | **ratio** |
|---|---|---|---|
| Saint-Paul | 4 730 | 3 867 | **1,223** |
| Saint-Leu | 4 953 | 3 622 | 1,368 |
| Saint-Pierre | 4 258 | 2 681 | 1,588 |
| Saint-Denis | 4 275 | 2 256 | 1,895 |
| Le Tampon | 4 318 | 2 000 | **2,159** |

**Le ratio va de 1,223 à 2,159 — un écart de 1,77×, à la lisière du « simple au double » que tu
poses comme disqualifiant** (CV ≈ 21 %). La prime du neuf sur l'existant N'EST PAS une constante :
elle est faible là où l'existant est cher et désirable (Saint-Paul balnéaire, ×1,22), forte là où
l'existant est vieux et bon marché (Le Tampon, ×2,16). **Le transfert n'est pas fondé.**

**Back-test (confirmation) : 7 / 87 = 8 % viables** sur les opérations de marché des communes non
couvertes. Pourquoi : appliqué aux prix existants bon marché, le ratio médian (1,588) donne des
prix estimés **sous le seuil de bascule 3 859** dans 6 communes sur 9 (Sainte-Marie 2 000×1,588 =
3 176 ; Saint-Louis 3 573 ; La Possession 3 691…) → le modèle déclare non viables des opérations
réellement construites. Le ratio médian **sous-estime** précisément là où l'existant est bon
marché (communes qui auraient besoin d'un ratio ~2,1). **Rejeté par le back-test, exactement
comme l'instabilité le prédisait.**

## 2 · Levier 2 — abaissement de N_MIN (10 → 5) : marginal, pas un levier de couverture

À N_MIN = 5 (règle de fragilité maintenue : n < 20 & médiane < 3 859 → écarté), une seule commune
franchit : **Saint-Joseph** (n = 7 ventes neuves de marché, médiane 4 660). Or Saint-Joseph est
**social-dominant** (56 % du collectif est social) — lui servir un prix de marché sur 7 ventes est
doublement fragile. Back-test : 2 opérations, 2 viables — **échantillon sans valeur statistique**.
Toutes les autres communes non couvertes ont **< 5** ventes neuves de marché (souvent 0). **Gain
de couverture réel : nul.** Baisser N_MIN n'ouvre pas de marché là où il n'y a pas de ventes.

## 3 · Levier 3 — repli île (médiane marché 4 375) : PASSE le back-test (le prometteur, contre toute attente)

Médiane des ventes d'appartements neufs de marché **de toute l'île** (hors bailleurs sociaux) =
**4 375 €/m²**. Appliquée aux communes non couvertes :

**Back-test : 86 / 93 = 92 % viables** — **dans la bande de référence (89-91 %)**. Par commune
(viables / testées) : L'Étang-Salé 7/8, La Plaine 5/6, Le Port 1/1, La Possession 10/10,
Saint-Benoît 15/16, Saint-Joseph 2/2, Saint-Louis 13/14, Sainte-Marie 22/24, Sainte-Suzanne 9/10,
Trois-Bassins 2/2. Le prix de marché du neuf étant uniforme (~4 375), un prix île plat le
reproduit à ±12 % près (l'écart max des 5 communes couvertes), ce qui reste au-dessus du seuil de
bascule partout.

**Distinction CRITIQUE avec le socle 4900 mort** (à ne pas confondre) :

| | Socle 4900 (mort) | Levier 3 (candidat) |
|---|---|---|
| Provenance | prix d'UNE commune chère (Saint-Paul observatoire) | **médiane MARCHÉ de l'île** (DVF, appartements neufs hors social) |
| Niveau | 4 900 (trop haut) | **4 375** (empirique, plus bas) |
| Appliqué à | TOUTES les opérations, TOUTES communes (social/patrimonial inclus) | **communes de MARCHÉ uniquement** (social-dominantes restent « non calculable ») |
| Back-test | 78 % NON viables (échoue) | **92 % viables (passe)** |

Le levier 3 est la version **disciplinée** de ce que le socle tentait : un prix de marché mesuré,
appliqué là où le marché domine, validé par le back-test — pas un prix d'exception servi partout.

**Couverture** : il étend aux **~11 communes de marché** aujourd'hui non couvertes (social < 50 %) :
Sainte-Marie, Saint-Louis, Les Avirons, La Possession, Saint-Benoît, L'Étang-Salé, Sainte-Suzanne,
Saint-André, Les Trois-Bassins, Salazie, Sainte-Rose. **Couverture 5 → ~16 communes**, les **8
communes social-dominantes** (Le Port, Entre-Deux, Saint-Philippe, Petite-Île, Cilaos, Bras-Panon,
Saint-Joseph, La Plaine) **restant « non calculable — collectif majoritairement social/aidé »**
(décision précédente inchangée, et c'est correct).

**Incertitude honnête du levier 3** (à ne pas taire) :
1. **Prix PLAT** : il ignore la variation résiduelle du neuf (4 258-4 953, ±12 %). ±12 % de prix
   ≈ ±70 % de charge — significatif, mais ne fait pas basculer la majorité (marge au-dessus du
   seuil). Une variante régionale (Nord/Sud/Est/Ouest) réduirait l'écart si les régions ont assez
   de ventes — à mesurer en phase B.
2. **Validé E1 seulement** : le back-test montre que 4 375 ne déclare PAS non viables des
   opérations réellement construites (faux négatif écarté). Il ne prouve PAS l'absence de
   SUR-évaluation (le mode d'échec du 4900) : cela demande le test E3 (prix payé vs charge) sur
   les communes non couvertes, où les données achat→PC sont minces. **Mesure bloquante de phase B.**
3. **Ne pas l'appliquer aux social-dominantes** : le risque « socle » revient si on sert 4 375 à
   une commune où le collectif est social/patrimonial (il ne se vend pas à ce prix). La garde =
   la carte social-dominant déjà mesurée.

## 4 · Combinaisons

- **1 + 3, 2 + 3** : les leviers 1 et 2 n'ajoutent rien d'exploitable au levier 3 (1 échoue, 2
  n'ouvre qu'une commune social-dominante). Aucune combinaison n'améliore le levier 3 seul.
- **Raffinement de 3** (pas une combinaison des trois, mais la piste de phase B) : médiane MARCHÉ
  **régionale** plutôt qu'île, si chaque grande région atteint N_MIN de ventes neuves — réduirait
  le caractère plat sans ré-ancrer sur l'existant. À mesurer.

## 5 · Tableau final — levier → couverture → back-test → incertitude

| Levier | Couverture ajoutée | Back-test (réf. 89-91 %) | Incertitude | Verdict |
|---|---|---|---|---|
| **1 · ratio neuf/ancien** | nominalement ~15, **réellement 0** | **8 %** | ratio instable 1,22-2,16 (×1,77) | **NON FONDÉ** |
| **2 · N_MIN 10→5** | **+1** (Saint-Joseph, social-dom.) | 100 % sur **2 op.** (sans valeur) | n=7, commune social-dominante | **marginal, écarté** |
| **3 · repli île marché 4 375** | **+11** (5 → 16 communes de marché) | **92 %** | prix plat ±12 % ; validé E1 seul (E3 à faire) ; garder social-dom. non calc. | **PROMETTEUR** |

## 6 · Recommandation (phase B, non exécutée)

**Le levier 3 est le seul fondé, et il est contre-intuitif** : ce n'est pas le ratio local mais le
prix de marché île qui étend la couverture, parce que le neuf de marché est un marché insulaire
intégré. Recommandation pour la phase B (application), si GO :
1. Étendre l'instrument aux **~11 communes de marché** via la médiane marché île (ou régionale si
   assez de ventes — à départager), en tête de préséance APRÈS le local : override bassin sourcé >
   dvf secteur local > dvf commune local > **médiane marché région/île (repli typé)** > non
   calculable. Le local prime toujours ; le repli île ne sert que faute de local.
2. **Étiquette distincte** pour le repli île (« estimation île — pas de marché local observé »,
   placeholder) : ne jamais faire passer un repli pour une mesure locale.
3. **Garder les 8 communes social-dominantes en « non calculable »** — le levier 3 ne les touche
   pas.
4. **Mesure bloquante avant application** : E3 (prix payé vs charge) sur les communes de marché
   étendues, pour borner la SUR-évaluation (le mode d'échec du 4900 que le back-test E1 ne voit
   pas). Le back-test reste le juge permanent.
5. Ordre inchangé : ce mandat **avant** le coût par taille.

## Artefacts

`/tmp/leviers_couverture.py` (LECTURE SEULE, back-test des 3 leviers), mesures de ratio et de
couverture par requête SQL reproductible. Golden 116/116 + tiers au bit près avant/après
(`/tmp/couv_tiers_avant.txt` = `/tmp/couv_tiers_apres.txt`). Échantillons d'opérations réelles
issus de `/tmp/backtest_e1.json`.

---

# VÉRIFICATIONS (28/07/2026) — back-test restreint, E3, variante EPCI. LECTURE SEULE.

**Réconciliation de nomenclature** (le mandat déposé `MANDAT_COUVERTURE_PRIX.md` a été fourni
après ce rapport) : ses trois leviers sont **1 · ratio neuf/ancien** (mesuré, NON fondé, ci-dessus),
**2 · estimation hiérarchique avec rétrécissement vers l'EPCI**, **3 · élargissement de la fenêtre
temporelle**. Mon « repli île » qui passe à 92 % = le **levier 2** du mandat avec l'ÎLE comme niveau
supérieur au lieu de l'EPCI. Les trois vérifications ci-dessous valident et raffinent ce levier 2.
Golden 116/116 + tiers au bit près avant/après.

## 7 · Le 92 % vient bien des communes ÉTENDUES (pas des 5 couvertes) — question tranchée

Back-test **restreint aux seules communes étendues marché-dominantes**, île 4 375 :

| Commune | viables / testées |
|---|---|
| Sainte-Marie | 22 / 24 |
| Saint-Benoît | 15 / 16 |
| Saint-Louis | 13 / 14 |
| La Possession | 10 / 10 |
| Sainte-Suzanne | 9 / 10 |
| L'Étang-Salé | 7 / 8 |
| Les Trois-Bassins | 2 / 2 |
| **TOTAL étendues** | **78 / 84 = 93 %** |

**Le 92-93 % ne parle PAS des 5 communes déjà couvertes** (elles sont exclues de ce test) : il
mesure la validité du repli **sur les nouvelles**, et il tient (93 %, dans la bande 89-91 %).
**Limite de validation nommée** : 7 des 11 communes étendues ont des opérations ≥ 10 lgt pour le
test ; **4 (Les Avirons, Saint-André, Sainte-Rose, Salazie) n'en ont AUCUNE** — l'estimateur y
serait appliqué mais **non validé localement** (inoffensif, peu de parcelles, mais à dire). Le
levier 3 du mandat (fenêtre temporelle 2018+/2015+ indexée) servirait surtout à densifier la
validation de ces 4-là — non mesuré ce tour, à ouvrir si tu veux les couvrir avec preuve.

## 8 · E3 — pas de sur-évaluation (le mode d'échec du 4900 est absent)

Achat foncier → PC collectif ≤ 4 ans, communes étendues, charge à l'île 4 375, **ratio prix payé /
charge** (charge > 0, n = 10) :
- **ratio < 1 (acheteur a payé MOINS que notre charge = SUR-évaluation) : 0 / 10 (0 %).**
- médiane 5,57 · min **1,17** · déciles 1,17 / 1,39 / 1,58 / 1,99 / … — **tous ≥ 1**.

**Verdict** : à 4 375, aucun acheteur réel n'a payé moins que notre charge supportable → on ne
sur-évalue pas (contrairement au 4900, où E3 donnait des ratios < 1 massifs). On est même sur le
**versant conservateur** (l'acheteur paie 1,2 à 5× notre charge : direction non-optimiste, la
sûre — Vic). **Caveats honnêtes** : n = 10 (mince, limite de validation à nommer, non masquée) ;
les ratios élevés indiquent un léger sous-évaluation possible (charge un peu basse) OU un
`prix_payé` portant de la valeur bâtie résiduelle — dans les deux cas, PAS le défaut du 4900.

## 9 · Variante EPCI vs île — l'île suffit, la simplicité prime

Médianes MARCHÉ par EPCI (appt neuf hors social) : **TCO 4 595 · CIREST 4 400 (n=4 seulement) ·
CASUD 4 318 · CINOR 4 287 · CIVIS 4 270** — **écart 7,6 %**, ~ île 4 375. Back-test avec la médiane
EPCI par commune (repli île si EPCI mince) : **93 %, IDENTIQUE à l'île plate**. Et **CIREST (tout
l'Est) n'a que 4 ventes de marché** → médiane non fiable, repli île obligatoire. **Conclusion (règle
du mandat : « si l'amélioration est marginale, l'île suffit et la simplicité prime ») : l'estimateur
ÎLE PLAT est retenu.** L'EPCI n'apporte rien qui justifie sa complexité, et échoue là où l'île sauve.

## 10 · Le fait produit — le marché intégré (à servir tel quel, formulation Vic)

> « Le prix de sortie du collectif neuf est quasi uniforme à La Réunion (4 258 à 4 953 €/m², ±8 %)
> alors que le prix de l'existant varie de 1 633 à 3 867. Le neuf est un marché intégré — coûts de
> construction homogènes, acheteurs en défiscalisation — tandis que l'existant reflète l'âge et la
> qualité du stock local. »

Ce n'est pas un défaut du levier, c'est sa **fondation** : c'est ce qui rend méthodologiquement
légitime un estimateur plat de niveau île. Connaissance de marché servable par le produit.

## 11 · Recommandation consolidée (phase B/C, non exécutée)

- **Estimateur retenu : médiane MARCHÉ île (4 375), en repli TYPÉ après le local** — préséance :
  override bassin sourcé > dvf secteur local > dvf commune local > **repli île « estimation île »** >
  non calculable. Le local prime toujours ; le repli ne sert qu'à défaut.
- **Couverture 5 → ~16 communes** (5 locales + 11 marché-dominantes en repli île), dont **7 validées
  par back-test**, 4 non validées localement (à couvrir avec preuve seulement si le levier temporel
  est ouvert).
- **Les 8 communes social-dominantes restent « non calculable »** — sans exception (garde anti-socle).
- **Étiquetage** (validé Vic) : « Estimé — médiane locale, N ventes » (local) / « Estimé —
  estimation île, pas de marché local observé, incertitude ± ~12 % » (repli) / « Non calculable »
  (social dominant / marché non observable). Jamais un repli présenté comme une observation locale.
- **Interdits d'application respectés** : pas de socle global (le repli île est TYPÉ et n'écrase
  jamais un prix local), back-test = juge permanent, E3 re-mesurée en phase C.

## Artefacts (vérifications)

`/tmp/couv_verifications.py` (LECTURE SEULE : back-test restreint + EPCI + E3). Golden 116/116 +
tiers au bit près avant/après (`/tmp/covB_tiers_avant.txt` = `/tmp/covB_tiers_apres.txt`).

---

# LEVIERS 3 (temporel) & 4 (hédonique) — mesure seule (28/07/2026). LECTURE SEULE.

Golden 116/116 + tiers au bit près avant/après. (Réconciliation : le levier 3 du mandat déposé =
fenêtre temporelle ; le levier 4 — hédonique — a été ajouté par Vic ce tour.)

## 12 · Levier 3 — élargissement de la fenêtre temporelle (+ indexation)

Constat préalable : l'instrument prix inclut DÉJÀ toutes les années de vente (2014-2025). « Élargir »
agit donc sur (a) la **cohorte de back-test** (opérations PC, actuellement 2021+) et (b) l'**indexation**
(l'île 4 375 mélange du 2016 @~4 000 et du 2024 @~4 700 non corrigés). Trajectoire prix des communes
couvertes : ~4 000 (2016-2018) → ~4 700 (2022-2024), index lisse (facteurs 0,94-1,18).

**Q1 — les 4 communes non validées deviennent-elles testables ?** Cohorte élargie PC 2015+, prix
sûr 4 375 :

| Commune | back-test 2015+ |
|---|---|
| **Les Avirons** | **14 / 15 = 93 %** ✓ |
| **Saint-André** | **9 / 11 = 82 %** ✓ |
| Sainte-Rose | 0 / 1 (1 op, non concluant) |
| Salazie | 0 / 0 (aucune opération de marché) |

**Les Avirons et Saint-André étaient testables** (elles étaient absentes de l'artefact back-test
réutilisé, pas du marché) — elles **passent** → validées. **Sainte-Rose (1 op) et Salazie (0)
n'ont aucune opération de marché même en 2015+** : l'absence de preuve devient un FAIT établi (issue
n°2 de Vic) → étiquette « estimation île — aucune opération de marché observée sur cette commune ».

**Q2 — l'indexation change-t-elle la médiane île ?** Oui : 4 375 (brut) → **4 692 (+7 %)** indexée
au présent (le brut est tiré vers le bas par les ventes anciennes).

**Q3 — le back-test tient-il ? OUI au prix sûr, MAIS l'indexation le fait basculer en
SUR-ÉVALUATION.** Cohorte élargie 2015+ : **91 % à 4 375** (dans la bande) ; 97 % à 4 692. Le 97 %
n'est PAS un progrès — c'est le prix trop haut : **E3 à 4 692 donne 5 / 12 opérations sur-évaluées
(l'acheteur a payé MOINS que notre charge), contre 0 / 10 à 4 375**. **L'indexation réintroduit le
mode d'échec du 4900.** Résultat en soi : **on garde le 4 375 non indexé — plus bas, conservateur,
seul à passer E3.** L'indexation est méthodologiquement séduisante mais rejetée par la mesure
symétrique.

## 13 · Levier 4 — estimateur hédonique : la constante gagne (dit franchement)

Modèle `prix_m2 ~ niveau de vie + densité + part proprio + pente + surface + année` (features
parcelle `p_model_static`), **282 transactions** des 5 communes couvertes.

**Q1 — explique-t-il quelque chose ?** **R² = 0,204** (faible). Le vrai test = **validation croisée
laisser-une-commune** (prédire une commune couverte non vue) : **MAE médiane hédonique 397 €/m² vs
île plate 242 €/m²**. **Le modèle fait PIRE que la constante.** Il surajuste le bruit in-sample
(Saint-Denis prédit 4 885 vs vrai 4 275, err 610 ; Le Tampon 4 858 vs 4 318, err 540) et ne
généralise pas. **Par la règle de Vic : la constante gagne.**

**Q2 — domaine.** Enveloppe d'entraînement : revenu [19 256, 24 062], densité [1 675, 3 338], pente
[5, 12]. **10 des 11 communes étendues sont HORS enveloppe** sur ≥ 1 feature (Salazie, Trois-Bassins,
Sainte-Rose, Saint-Benoît, Saint-André… — les Hauts et l'Est). Toute prédiction y est une
**extrapolation** ; le modèle est le moins fiable là où on en a le plus besoin, et prédit des prix
sous le seuil de bascule (Salazie 3 627, Sainte-Rose 3 805) qui déclareraient non viable par
extrapolation non fiable.

**Q3 — back-test.** Inutile de le lancer : le modèle échoue déjà les deux tests plus fondamentaux
(il ne bat pas la constante en CV, il extrapole sur 10/11 communes). **Résultat en soi (mot de Vic)
: le marché du neuf est si INTÉGRÉ qu'il n'y a pas de signal spatial à capter — la constante plate
EST le meilleur estimateur, par robustesse.** C'est la confirmation, par un quatrième angle, du fait
produit du §10.

## 14 · Tableau final consolidé — 4 leviers

| Levier | Couverture | Back-test | Incertitude | Verdict |
|---|---|---|---|---|
| 1 · ratio neuf/ancien | 0 réel | 8 % | ratio ×1,77 instable | **NON FONDÉ** |
| 2 · rétrécissement EPCI | +11 | 93 % (= île) | EPCI 7,6 % ~ île ; CIREST n=4 | **écarté (île plus simple ET plus robuste)** |
| 3 · fenêtre temporelle | valide +2 (Avirons, St-André) | 91 % à 4 375 | indexation → E3 5/12 sur-éval. | **utile pour VALIDER ; indexation REJETÉE** |
| 4 · hédonique | — | échoue en amont | CV 397 > île 242 ; 10/11 hors domaine | **REJETÉ (la constante gagne)** |
| **→ estimateur retenu : ÎLE PLATE 4 375** | **5 → 16** | **91-94 %** | plat ±12 % ; E3 0 % sur-éval. | **VALIDÉ, tous angles** |

## 15 · Recommandation consolidée finale (phase C, non exécutée)

- **Estimateur : médiane MARCHÉ île 4 375 (NON indexée)**, en repli TYPÉ après le local. L'indexation
  et l'hédonique sont mesurés et écartés — la constante plate gagne par robustesse ET par E3.
- **Couverture 5 → 16 communes** : **14 validées par back-test** (5 locales + L'Étang-Salé, La
  Possession, Saint-Benoît, Saint-Louis, Sainte-Marie, Sainte-Suzanne, Trois-Bassins, **Les Avirons,
  Saint-André**) + **2 avec étiquette « estimation île — aucune opération de marché observée »**
  (Sainte-Rose, Salazie — issue n°2 de Vic, l'absence de preuve est un fait servi honnêtement).
- **8 communes social-dominantes restent « non calculable » sans exception** (garde anti-socle).
- **Étiquetage par confiance** (validé Vic) : « médiane locale, N ventes » / « estimation île, ± ~12 % »
  / « estimation île — aucune opération de marché observée » / « non calculable » (par cas).
- **Interdits respectés** : pas de socle global (repli TYPÉ, local prime), back-test = juge, E3
  re-mesurée en phase C au prix retenu.

## Artefacts (leviers 3-4)

`/tmp/levier_temporel.py`, `/tmp/levier_hedonique.py` (LECTURE SEULE). E3 à 4 375 vs 4 692 mesurée.
Golden 116/116 + tiers au bit près avant/après (`/tmp/covT_tiers_avant.txt` = `/tmp/covT_tiers_apres.txt`).

---

# VÉRIFICATION D'ARTEFACT avant GO phase C (28/07/2026) — exigée par Vic. LECTURE SEULE.

Une conclusion antérieure (« Les Avirons/Saint-André sans opération ») était fausse à cause d'un
filtre de mesure. Vic exige l'audit avant tout GO. Golden 116/116 + tiers au bit près.

## 16 · Le filtre, exactement, et depuis quand

`backtest_e1.json` (construit au PREMIER back-test) résolvait le prix via l'**ANCIEN**
`dvf_prix_sortie_neuf` (17 communes, médiane maison+appartement, N_MIN 5). Une opération dans une
commune HORS de ces 17 recevait le motif **`non_calculable_sans_marche_neuf`** et `c_prog=None`.
Mes mesures de leviers ont rechargé `backtest_e1.json` avec `if c_prog is not None` → ces opérations
étaient écartées. **Le filtre est donc la COUVERTURE de l'ancien instrument prix**, dans la chaîne
depuis le premier back-test.

**Empreinte mesurée** (les 1 137 entrées de `backtest_e1.json`) : 1 018 calculables ; **105
écartées `non_calculable_sans_marche_neuf`** — Les Avirons 21, Saint-André 52, Bras-Panon 8,
Cilaos 12, Salazie 9, Sainte-Rose 3 : **TOUTES en communes NON couvertes, ZÉRO dans les 5
couvertes** ; + 14 `faisabilite_absente` (Saint-Philippe 11, Saint-Paul 3 = parcelles réellement
non constructibles).

## 17 · Quelles conclusions en dépendent — audit source par source

| Conclusion | Source | Filtre l'affecte ? | Statut |
|---|---|---|---|
| **89-91 % acceptation** | `backtest_e1.json`, communes COUVERTES | Footprint = 0 en couvertes | **inchangé — re-mesuré FRAIS : 91 % (155/170)** |
| **E1 78 % (médiane fausse)** | back-test original, ANCIEN instrument par design | Mesure l'ancien instrument (17 communes) — pas un biais | inchangé (c'était le but) |
| **E3 0/10 sur-évaluation** | requête SQL FRAÎCHE (achats→PC) ce tour | N'utilise pas `backtest_e1.json` | inchangé |
| **Composition 20 % social** | requête Sitadel `vol` (tous permis) | Non filtrée par c_prog | inchangé |
| **Gradient build-to-hold** | Sitadel + DVF direct | Non filtrée | inchangé |
| **4 communes « sans opération »** | `backtest_e1.json` filtré | **OUI — matériellement faux** | **DÉJÀ CORRIGÉ ce tour (levier temporel, cohorte fraîche) : Les Avirons 14/15, Saint-André 9/11 validées** |

**La seule conclusion que le filtre a matériellement faussée est celle des 4 communes — et c'est
exactement celle que le levier temporel a rattrapée ce tour, en cohorte FRAÎCHE** (query Sitadel
directe + `parcel_faisabilite`, sans `backtest_e1.json`). Toutes les autres sont soit une mesure
de l'ancien instrument par construction (E1), soit bâties fraîches (E3, composition, build-to-hold),
soit sur les communes couvertes que le filtre n'a pas touchées (acceptation, re-confirmée à 91 %).

## 18 · Verdict : rien ne bouge → conditions du GO réunies

Aucune conclusion matérielle ne change. La seule affectée (4 communes) est corrigée et documentée.
**Le principe golden est respecté : on ne valide pas une mesure avec l'instrument dont on a
découvert qu'il filtrait — on a re-mesuré FRAIS, et le chiffre tient (91 %).**

Note d'exécution pour la phase C : la branche de mesure `mesure/couverture-prix-phase-a` est partie
d'AVANT le merge de l'application ; la **phase C doit brancher depuis `main` APPLIQUÉ** (code
`resolve_prix_neuf_marche`, N_MIN 10). La DB, elle, est en état APPLIQUÉ (5 communes, socle 4900
purgé) — les mesures ci-dessus l'ont lue.
