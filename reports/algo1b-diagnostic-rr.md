# ALGO-1b — Diagnostic du RR par commune · Rapport (lecture seule)

**Mandat** : rapport seul, aucun code, aucune branche — fichier NON commité, scripts
jetables /tmp. **Données** : fold 2025 out-of-sample (`scores-2025-fold-final.csv`),
label L2-F, hors copro, harnais `p_model.evaluate` (bootstrap n=1000, seed 974).
Contrôle : RR@1158 île = **6,73** (= gelé). Référence : `reports/algo1-rr-commune.md`.

---

## 1. Intervalles de confiance — qui est signal, qui est bruit

RR intra-commune (k_c ∝ part du 1158) avec IC95 bootstrap. « DISTINCT » = l'IC95
exclut la moyenne île 6,73.

| Verdict | Communes (RR [IC95]) |
|---|---|
| **DISTINCT au-dessus** | L'Étang-Salé **17,9** [7,2;29,8] · Le Port **16,1** [7,8;27,4] · Saint-Benoît **14,0** [7,5;22,0] |
| **DISTINCT en dessous** | Le Tampon **3,1** [1,0;5,6] · Saint-Joseph **2,5** [0;5,8] · Les Trois-Bassins **0** [0;4,7] · Cilaos **0** [0;0] |
| Bruit-compatible (bornes larges) | tout le reste — y compris la « tête » spectaculaire de l'ALGO-1 §1 : Sainte-Suzanne 19,5 [6,3;35,2], Sainte-Rose 14,5 [0;38,9], Saint-Philippe 12,0 [0;31,0] |
| Faibles mais NON distinguables | **Saint-Paul 4,6 [2,0;6,9]** · **Saint-Denis 3,8 [1,3;7,2]** · Saint-Louis 3,7 [0,9;8,5] · La Possession 3,8 [0;7,6] |

Réponse à la question « les <20 positifs sont-elles distinguables ? » : **non pour
presque toutes** (IC énormes — Sainte-Rose [0;38,9] ne prouve rien), **avec une
exception instructive : Cilaos [0;0]** — 114 positifs au total dans la commune et
JAMAIS un seul dans le top-k, même rééchantillonné 1 000 fois. Un zéro aussi têtu
n'est pas du bruit : c'est une cécité réelle. Trois-Bassins [0;4,7] est au bord du
même constat.

## 2. RR à budget proportionnel (top 0,3 % de chaque commune)

| Commune | RR (part du 1158) | RR (top 0,3 %) |
|---|---:|---:|
| Saint-Paul | 4,6 | **4,9** |
| Saint-Denis | 3,8 | **4,5** |
| Le Tampon | 3,1 | **2,7** |
| Saint-Joseph | 2,5 | **2,2** |
| L'Étang-Salé | 17,9 | 15,9 |
| Le Port | 16,1 | 18,1 |

**Le classement ne change pas** (les deux colonnes sont quasi identiques sur les
24 communes). Ce n'était de toute façon pas un artefact possible : le RR intra de
l'ALGO-1 §1 était DÉJÀ à budget proportionnel (k_c = part du 1158 ≈ 0,27 % de chaque
parc — la commande du mandat et la mesure existante coïncident à 0,03 point près).
**Conclusion nette : le modèle n'est pas « dilué » par la taille de Saint-Paul ou du
Tampon — à budget égal, il y discrimine réellement moins.**

## 3. Diagnostic des grandes — la couverture n'explique rien (mais elle explique AUTRE chose)

Couverture des features, fold 2025 hors copro (parts de valeurs absentes) :

| Commune | taux base | PLU inconnu | résiduel NULL | DVF bâti NULL | Filosofi NULL | win_cov |
|---|---:|---:|---:|---:|---:|---:|
| **Saint-Paul** | **1,74 %** | 0 % | 36,8 % | 3,8 % | 11,0 % | 1,0 |
| **Saint-Denis** | **1,60 %** | 0 % | 30,7 % | 0,9 % | 3,4 % | 1,0 |
| **Le Tampon** | **1,71 %** | 0 % | 37,5 % | 1,3 % | 5,2 % | 1,0 |
| (île, ordre de grandeur) | 1,51 % | ~0 % | ~35-45 % | ~2-5 % | ~10 % | 1,0 |
| Étang-Salé (forte) | 1,63 % | 0 % | 38,6 % | 2,1 % | 11,0 % | 1,0 |
| **Saint-Philippe** | 1,52 % | **100 %** | **100 %** | 13,8 % | 25,6 % | 1,0 |
| Cilaos (zéro) | 1,74 % | 0 % | 45,1 % | 3,2 % | 19,0 % | 1,0 |
| Salazie | 0,87 % | 0,1 % | 66,0 % | 10,9 % | 22,2 % | 1,0 |

Constats :
- **Les 3 grandes sont NORMALEMENT couvertes** — PLU rattaché partout, DVF quasi
  complet, fenêtres pleines (win_cov = 1), et leur taux de base de mutation est
  AU-DESSUS de l'île (1,60-1,74 % vs 1,51 %). Ni données manquantes, ni marché
  atone : la faiblesse du RR y mesure bien un **pouvoir discriminant moindre**.
- **Les zéros des Hauts ont une signature commune** : rotation bâtie de secteur
  ~moitié de l'île (Cilaos 0,0038, Salazie 0,0033, Trois-Bassins 0,0048 vs île
  ~0,008). Le moteur carbure au signal de marché (rot_nu/rot_bati = seules
  monotonies contraintes) : là où rien ne tourne, il n'a rien à lire — Cilaos mute
  pourtant (1,74 %!) mais pour des raisons que les features ne capturent pas.
- **Finding de couverture INATTENDU — Saint-Philippe (97417)** : la commune est
  **100 % non calibrée** (zone_plu « inconnu » partout, résiduel NULL partout).
  Conséquence produit vérifiée dans le run servi : **0 chaude, 0 brûlante,
  0 réserve foncière** — le plancher C (SDP > 0 OU surface ≥ 600 m² en U/AU) est
  mathématiquement infranchissable sans zone ni SDP. La commune est exclue DE FACTO
  des tiers actionnables par le trou de données, alors que son RR intra (12,0,
  fragile) suggère que le classement y serait plutôt bon. C'est le SEUL vrai
  problème de couverture trouvé — et il ne touche aucune des 3 grandes.
- Nuance sur Trois-Bassins/Cilaos : elles ont 31 et 7 chaudes SERVIES (2026) alors
  que le fold 2025 n'y valide aucun pouvoir de classement — ces chaudes-là sont
  sans support de validation locale (petits effectifs, prudence).

## 4. Le « ×N » de la fiche — calculé sur l'île, surestime modérément en mono-commune

Vérifié dans le code ET recalculé : `mult_base = p_raw / taux_base` où
`taux_base` = moyenne des p prédits **hors copro ÎLE** (0,015633 au run servi —
le recalcul colle au ×N stocké au centième). L'UI l'assume (« plus probable de
muter que la moyenne **de l'île** »).

Les 5 meilleures chaudes/brûlantes de Saint-Paul :

| Parcelle | rang | ×N affiché (île) | ×N intra-commune | écart |
|---|---:|---:|---:|---:|
| 97415000DK1044 | 10 | ×21,99 | ×20,4 | −7 % |
| 97415000CX1395 | 22 | ×18,02 | ×16,7 | −7 % |
| 97415000AY1622 | 25 | ×13,07 | ×12,1 | −7 % |
| 97415000CX0639 | 34 | ×13,07 | ×12,1 | −7 % |
| 97415000AY1587 | 39 | ×13,07 | ×12,1 | −7 % |

Saint-Paul a une moyenne prédite +7,7 % au-dessus de l'île (0,01684 vs 0,01564) ;
contre le taux OBSERVÉ 2025 (1,74 % vs 1,51 %), l'écart serait ~−13 %. **Verdict :
le chiffre servi surestime de 7 à 13 % pour un client mono-Saint-Paul — un biais
réel mais d'un ordre de grandeur INOFFENSIF** (×22 devient ×20, jamais ×22 devient
×5), et l'ancre « île » est affichée. À l'inverse, pour un client des Hauts le ×N
île SOUS-estimerait le lift local relatif — même ordre de petitesse.

---

## CONCLUSION — le diagnostic demandé

Les trois causes coexistent, mais **localisées et hiérarchisées** :

1. **FAIBLESSE RÉELLE (dominante, mais modérée)** — Le Tampon et Saint-Joseph sont
   significativement sous la moyenne île (IC95 exclut 6,73), à budget proportionnel,
   avec une couverture de données normale et un marché actif. Saint-Paul et
   Saint-Denis suivent la même tendance sans atteindre la significativité
   ([2,0;6,9] et [1,3;7,2]). Même faibles, ces RR restent ≥ 2-4× le hasard — le
   modèle y est MOINS BON, pas aveugle. Cas extrême : les Hauts à rotation quasi
   nulle (Cilaos [0;0], Trois-Bassins) où le moteur, assis sur le signal de marché,
   n'a structurellement rien à lire.
2. **BRUIT STATISTIQUE (la moitié du tableau)** — presque toute la « tête » et la
   « queue » spectaculaires de l'ALGO-1 §1 sont non significatives (IC géants sur
   petits parcs). Seuls Étang-Salé, Le Port et Saint-Benoît sont PROUVÉS meilleurs
   que l'île. Ne pas construire de discours commercial sur Sainte-Suzanne 19,5.
3. **COUVERTURE (un cas, mais sérieux)** — rien à voir avec les grandes :
   **Saint-Philippe est 100 % non calibrée (PLU + résiduel) et de ce fait exclue
   de facto des tiers actionnables (0 chaude/brûlante/réserve au run servi)** —
   un trou silencieux que ni le RR île ni le golden ne voyaient.

Le ×N (île) surestime de 7-13 % en mono-commune dense : réel, honnêtement ancré,
sans gravité à l'échelle des ×13-22 servis.

Conformément au mandat : **aucun correctif proposé** — les faits ci-dessus suffisent
à cadrer les décisions (elles relèvent de l'arène et d'un mandat data pour
Saint-Philippe).

---

## ANNEXE (26/07/2026) — Saint-Philippe : RNU confirmé, pas un PLU non ingéré

Question : RNU (aucun PLU approuvé) ou PLU existant jamais ingéré ? **Verdict : RNU,
avec un PLU EN ÉLABORATION jamais approuvé.** Le correctif relève donc de la branche
RNU (moteur de faisabilité + plancher C), PAS d'un mandat de données — il n'existe
RIEN à ingérer.

Faisceau (5 sources, dont 3 re-vérifiées EN DIRECT ce jour) :

| Source | Constat | Fraîcheur |
|---|---|---|
| GPU `document?partition=DU_97417` | **0 document** (et `CC_97417` = 0 : pas de carte communale non plus) | live 26/07 |
| GPU `zone-urba` au bourg (55,7667/-21,3578) | **0 zone** (témoin Sainte-Rose : 1 zone Ua) | live 26/07 |
| AGORAH Base permanente des PLU | **0 enregistrement** pour 97417 (témoin 97419 : 125 zones, datappro 2019-05-04) — l'agence d'urbanisme régionale ne référence AUCUN PLU approuvé | live 26/07 |
| DEAL « état d'avancement des documents d'urbanisme » | « **RNU + PLU en élaboration (non approuvé)** » — 1 seule commune de l'île dans ce cas | lue le 25/06/2026 (note repo) ; page 404 au re-fetch direct ce jour (géo-blocage/refonte probable), version indexée concordante |
| Notes repo (`docs/communes/saint_philippe_BLOCKED_PLU_GPU.md`, 22-25/06/2026) | pré-vol : zonage propre 97417 = 0 % ; les 3 « zones Saint-Philippe » en base sont des DÉBORDS des PLU voisins (idurba 97412 Saint-Joseph + 97419 Sainte-Rose), couverture parcellaire 0 % ; « Ne PAS improviser une cascade mode RNU sans logique réglementaire dédiée » | juin 2026 |

Deux pièges documentés au passage :
- le flag GPU `is_rnu = false` est **périmé/déclaratif** (aucune géométrie ni document
  derrière — la note repo du 25/06 le qualifiait déjà d'« ambigu ») ; c'est lui qui a
  induit la ligne ERRONÉE de `docs/communes/POST_16_STRATEGIC_INVENTORY.md` (« un PLU
  existe mais non numérisé → sourcing manuel ») — à corriger dans un futur mandat,
  rien touché ici (rapport seul) ;
- le calibrage `config/calibrage/zonage_saint_philippe.yaml` fige lui aussi ces zones
  de débord voisines (idurba 97412/97419) sous le nom de Saint-Philippe.

Conséquences pour le correctif (constat, pas une proposition détaillée) :
- **branche RNU** nécessaire : constructibilité limitée aux parties urbanisées de la
  commune (règle de constructibilité limitée, art. L.111-3 s. CU) — logique de
  continuité, PAS un zonage ; le plancher C actuel (SDP > 0 OU surface ≥ 600 en U/AU)
  est structurellement infranchissable au RNU ;
- vérification à 5 minutes qui clôt le sujet à 100 % : un appel au service urbanisme
  de Saint-Philippe (0262 37 38 80) — une approbation TRÈS récente ne serait visible
  ni au GPU ni à l'AGORAH ;
- pondération : gisement local faible de toute façon (secteur volcan, 4 162 parcelles,
  DVF 315, note repo « opportunités quasi-nulles attendues ») — la branche RNU vaut
  surtout par PRINCIPE (une commune entière silencieusement exclue) et pour la
  robustesse si d'autres communes retombaient au RNU (caducité, annulation).

*Scripts jetables : /tmp/algo1b_boot.py (+ /tmp/algo1b_boot.csv) ; requêtes SQL en
séance. Rien de commité, aucune branche créée, base intouchée.*
