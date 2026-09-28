# RADAR-AUDIT-3 — chaque chiffre de la page Radar (lecture seule)

**Branche** `audit/radar-3` · worktree `~/Desktop/labuse-radaraudit` · base `52f97272`.
**Rien n'a été écrit** dans `src/` ni en base. API démarrée sur `127.0.0.1:5795` pour lire les valeurs
réellement servies ; recalcul par requêtes SQL **indépendantes** (que j'ai écrites, sans réutiliser les
constructeurs de requête de l'app). Le front dev (8595) n'a **pas** pu démarrer dans ce worktree
(`node_modules` en lien symbolique incomplet : `vite`/`@vitejs/plugin-react` absents) — la vérification a
donc été faite sur l'**API vivante** (source de vérité de ce qu'affiche la page) et non sur une capture.

**État du corpus** (au 28/09/2026, `pige_faits.valide_at IS NOT NULL`) : **241 biens** validés —
`active` 138 · `retiree` 103 · **`en_vente_longue` 0** · `vendue` 0. Dont `est_copro` (appartements) 69,
`a_qualifier` 13. Dépôts agence : 0. **`pige_prix_historique` : 1 seule ligne** dans toute la base.
Les 103 `retiree` ont tous leur `retiree_le` daté dans une fenêtre de **2 h 30 le 26/09** (import en masse).
Dernière capture `pige_passes` : **27/09 23 h 42**.

Ces trois faits (0 `en_vente_longue`, 1 ligne d'historique de prix, retraits en bloc) expliquent à eux
seuls la plupart des colonnes vides — voir §5.

---

## 1 & 2 · D'où vient chaque chiffre, et est-ce vrai

Légende verdict : **OK** = affiché = recalculé ; **OK/⚠** = exact mais trompeur (périmètre) ; **VIDE** =
structurellement 0 ; **KO** = incohérent avec un autre chiffre de la page.

### Bloc « Ce qui est demandé / ce qui se vend » — 4 chiffres du haut (MAISONS)

| Chiffre | Source (fichier:ligne) | Calcul & périmètre | Affiché | Recalculé SQL | Verdict |
|---|---|---|---|---|---|
| Prix demandé maisons — Île | `marche.py:197`→`radar_stats` `marche.py:98` ; front `RadarMarcheColonne.tsx:100` | médiane `prix/surface_hab`, `type_bien=maison`, `a_qualifier=false`, **tous statuts**, seuil masquage n<5 (`SEUIL_N`, `marche.py:15`) | **2 907 €/m²** · « 132 annonces » | 2907 / n=132 | **OK/⚠** (n compte 52 maisons `retiree` : actives seules = 80) |
| Prix demandé maisons — St-Denis | idem | idem, commune | 2 939 · 35 | 2939 / 35 | OK |
| Prix demandé maisons — St-Benoît | idem | idem, n=4 < 5 → masqué | **« sous le seuil »** · « 4 annonces » | brut 1873 / n=4 | **KO** (voir §3-b) |
| Prix acté maisons DVF — Île | `marche.py:177`→`_dvf_bati_type` `signaux.py:207` ; front `:102` | médiane DVF `dvf_mutations`, `type_local=Maison`, `_BAROMETRE_RETENUE` (`moteurs.py:717`), **pas de fenêtre glissante** | **2 623 €/m²** · « 2021–2025 · 15091 ventes » | 2623 / 15091 / 2021–2025 | OK |
| Prix acté maisons DVF — St-Denis | idem | idem, commune | 3 085 · 1810 | 3085 / 1810 | OK |
| Prix acté maisons DVF — St-Benoît | idem | idem | 1 948 · 532 | 1948 / 532 | OK |
| Écart demandé/acté — Île | `marche.py:181` ; front `:104` | `100·(dem−acté)/acté`, servi **seulement si les DEUX côtés ≥ 30** (`SEUIL_REF_TYPE=30`, `signaux.py:37`) | **+10,8 %** | (2907−2623)/2623 = +10,8 | OK |
| Écart demandé/acté — St-Denis | idem | idem | **−4,7 %** | (2939−3085)/3085 = −4,7 | OK (mais ≠ écart-par-commune, §3-d) |
| Écart demandé/acté — St-Benoît | idem | dem n=4 < 30 → masqué | « sous le seuil » | — | OK |
| Biens en vente — Île | `marche.py:200`→`client.compter` `client.py:261` ; front `:117` | `active`+`en_vente_longue`, `est_copro=false`, **`a_qualifier` INCLUS** | **103** | 103 | OK |
| Biens en vente — St-Denis / St-Benoît | idem | idem | 13 / **5** | 13 / 5 | OK (mais ≠ table, §3-a) |
| « dont N depuis + de 90 j » — tous scopes | `marche.py:201`→`compter(sup90=True)` (`statut=en_vente_longue`) ; front `:118` | compte `en_vente_longue` | **0** partout | 0 (0 `en_vente_longue` en base) | **VIDE** |

### Tableau « Par type de bien »

Toutes lignes, 3 scopes. Colonnes : En vente · Demandé €/m² · Acté €/m² · Écart · >90 j · Baisses 30 j.
Source : `_type_ligne`/`_demande_acte` `marche.py:169-194`, comptes `crows` `marche.py:160-167` ; front
`LigneType` `RadarMarcheColonne.tsx:35-52`.

| Scope · type | En vente (aff / recalc) | Demandé (aff / recalc) | Acté (aff / recalc) | Écart | >90 j | Baisses 30 j | Verdict |
|---|---|---|---|---|---|---|---|
| **Île** terrain | 8 / 8 | 322 / 322 (n=17) | 330 / 330 (n=12591) | sous seuil (dem n=17<30) | 0 | 0 | OK ; >90j/baisses VIDE |
| **Île** maison | 80 / 80 | 2907 / 2907 | 2623 / 2623 | +10,8 % | 0 | 0 | OK ; >90j/baisses VIDE |
| **Île** appartement | 35 / 35 | 3369 / 3369 (n=69) | 2564 / 2564 (n=12219) | +31,4 % | 0 | 0 | OK/⚠ (demande n=69 = 35 actifs + 34 `retiree`) ; « statistiques seules » |
| **St-Denis** terrain | 2 / 2 | 332 / 332 (n=7) | 485 / 485 | sous seuil | 0 | 0 | OK |
| **St-Denis** maison | 10 / 10 | 2939 / 2939 | 3085 / 3085 | −4,7 % | 0 | 0 | OK |
| **St-Denis** appartement | 17 / 17 | 3171 / 3171 (n=47) | 2391 / 2391 | +32,6 % | 0 | 0 | OK/⚠ |
| **St-Benoît** terrain | 0 / 0 | — | 237 / 237 | sous seuil | 0 | 0 | OK |
| **St-Benoît** maison | 3 / 3 | — (n=4<5) | 1948 / 1948 | sous seuil | 0 | 0 | OK ; ≠ « 4 annonces » (§3-b) |
| **St-Benoît** appartement | 0 / 0 | — | 1428 / 1428 | sous seuil | 0 | 0 | OK |

> **>90 j** et **Baisses 30 j** : **0 sur les 24 communes × 3 types**. La colonne >90 j lit
> `statut='en_vente_longue'` (0 en base) ; Baisses 30 j lit `pige_prix_historique` (1 ligne en base).
> Colonnes structurellement mortes aujourd'hui (§5).

### « Ce qui a bougé · 30 jours »

Source `marche.py:204-219` ; front `RadarMarcheColonne.tsx:139-150`.

| Chiffre | Périmètre | Île (aff/recalc) | St-Denis | St-Benoît | Verdict |
|---|---|---|---|---|---|
| Nouvelles | `active`/`en_vente_longue`, `a_qualifier=false`, **tous types (copro incl.)**, saisie ≥ J−30 | **127 / 127** | 30 / 30 | 3 / 3 | OK/⚠ (inclut appartements → > « biens en vente » 103, §3-e) |
| Baisses | prix en baisse < J−30 dans `pige_prix_historique` | **0 / 0** | 0 | 0 | VIDE (1 ligne d'historique) |
| Retirées | `event_log` dedup `pige:retiree:{id}`, ≥ J−30 | **101 / 101** | 60 / 60 | 1 / 1 | OK/⚠ (retraits en **bloc** du 26/09, pas un flux mensuel, §5) |
| De retour | changement de statut `retiree` puis re-vue < J−30 | **0 / 0** | 0 | 0 | VIDE |

### « Écart demandé / acté · maisons, par commune » (barres)

Source `marche.py:222-229` ; front `:153-171`. **Demande** = `marche.stats` médiane `med_bati`
(**maison+appartement+immeuble mélangés**, `marche.py:28-30`), retenue si n_bati ≥ 30. **Acté** =
`raw_rows`→`prix_ancien_communes` (`moteurs.py:722`, DVF **tous `type_local`**, ≥ 100 ventes).

| Barre affichée | Recalc (demande mixte / acté prix_ancien) | Verdict |
|---|---|---|
| **Saint-Denis +23,9 %** (seule barre, sur les 3 scopes) | (3060 − 2469)/2469 = **+23,9 %** ; n_bati demande = 82 | **OK arithmétiquement, KO de fond** (§3-d) |
| (aucune autre commune) | Seule St-Denis a n_bati ≥ 30 (Saint-Paul 22, St-Pierre 21, … < 30) | **une seule barre** (§5) |

### Pied de page & portes

| Chiffre | Source | Affiché | Recalc | Verdict |
|---|---|---|---|---|
| Dernière capture | `marche.py:237`, `max(pige_passes.captured_at)` | 27/09 23 h 42 | 27/09 23:42 | OK |
| Millésime DVF (pied) | `marche.py:232`, `_dvf_millesime` **seulement si commune** | Île : *rien* ; St-Denis « …31/12/2025 » ; St-Benoît « …30/12/2025 » | idem | OK/⚠ (Île n'affiche aucun millésime) |
| Porte Radar « N biens en vente » | `api.py:846`→`compter` ; front `RadarHub.tsx:88` | **103** | 103 | OK (= liste = marché) |
| Porte Veille « N parcelles / N alertes » | `api.py:850-853` | 9 suivis · 5 alertes | 9 / 5 | OK |
| Liste Radar « N biens » | `client.lister` `n_total` ; front `RadarEcran.tsx:122` | = filtre courant (103 sans filtre) | 103 | OK (= porte) |

---

## 3 · Incohérences (un même concept, deux chiffres)

**a) « 5 biens en vente » vs « 3 » dans le tableau (Saint-Benoît).** — *confirmé, cause trouvée.*
`biens_en_vente` (`client.compter`, `client.py:261`) compte `active`, `est_copro=false`, **et inclut
`a_qualifier=true`**. La table par type (`crows`, `marche.py:166`) **exclut `a_qualifier=true`**. À
Saint-Benoît, 2 terrains sont `a_qualifier` (biens #236 et #117) → 5 comptés dans le gros chiffre / la
porte / la liste, 3 dans la table (maison 3 + terrain 0). **Deux populations différentes pour le même mot
« en vente ».** (À l'échelle île : 103 vs 92 hors qualifier.)

**b) « médiane · 4 annonces » vs « 3 maisons en vente » (Saint-Benoît).** — *confirmé, cause trouvée.*
Le `n` de la médiane demandée (`radar_stats`, `marche.py:104`) compte **tous les statuts** (prix + surface
renseignés) : 3 maisons `active` + 1 maison `retiree` = 4. « En vente » (`crows`, `marche.py:162`) ne
compte que `active` = 3. **Le libellé « N annonces » de la médiane mélange les annonces retirées ; « en
vente » non.** Même mécanisme à l'île (« 132 annonces » de médiane maisons alors que 80 maisons actives).

**c) Bloc « Ce bien » 259 800 € Saint-Benoît sans sélection visible.** — *c'est le bien #248* (maison,
97 m² habitables, 385 m² terrain, 2 678 €/m², `active`). Il **est** dans la liste (les 5 biens de
Saint-Benoît : #254, #236, #248, #206, #117). La sélection **se voit** — carte à bordure et fond menthe
(`RadarEcran.tsx:64-65`) — **mais faiblement**, et il n'y a **ni défilement auto vers la carte
sélectionnée, ni libellé identifiant dans le bloc** (le bloc ne montre que €/m², prix, type — pas
d'adresse, pas de « bien #», `RadarMarcheColonne.tsx:227-235`). Sur une liste longue (jusqu'à 103 biens
île) ou après changement de filtre, la carte sélectionnée est hors écran → le bloc paraît orphelin. *Rien
de faux*, mais rien qui relie visuellement le bloc à sa ligne.

**d) Saint-Denis « écart maisons » = −4,7 % en haut, **+23,9 %** en barre — même page, même mot.** —
*nouvelle incohérence, la plus grave.* Les 4 chiffres et la ligne maison de la table disent **−4,7 %**
(demande maison 2939 vs acté maison 3085). La barre « écart par commune » — **libellée « maisons »** —
dit **+23,9 %** parce qu'elle calcule sur un **bâti mélangé** : demande `med_bati` = 3060 (maison **+
appartement + immeuble**) contre un acté `prix_ancien` = 2469 (DVF **tous types confondus**), au lieu de
maison-contre-maison. Deux bases de demande, deux bases d'acté, un même libellé, un signe opposé
(sous le marché vs +24 % au-dessus).

**e) « 127 nouvelles » (30 j) > « 103 biens en vente ».** — Les « nouvelles » comptent les appartements
(copro) que « biens en vente » exclut. Un lecteur voit plus d'entrées récentes que de biens au total.

**f) Deux seuils sur la même carte.** — La médiane demandée s'affiche dès n ≥ 5 (`SEUIL_N`), mais l'écart
n'apparaît qu'à n ≥ 30 (`SEUIL_REF_TYPE`). D'où des cartes qui montrent un prix demandé chiffré **et**
« sous le seuil » pour l'écart, côte à côte, sans expliquer que les seuils diffèrent.

---

## 4 · Ce qui manque (déjà en base, non montré)

- **Délai de vente / retrait** — `marche.stats` le calcule (`delai_median_j`, `marche.py:65`) mais
  `tableau()` ne le renvoie pas. Recalculé : **médiane 52,5 j sur n=64** (via `retiree_le − date_publication`).
  Un notaire/agent veut ce chiffre ; il existe et n'est pas affiché.
- **Part particulier / pro** — calculée aussi (`part_particuliers_pct`, `marche.py:67`), non affichée dans
  le marché. Recalculé : **6,6 % de particuliers** (15 / 228 ; 213 pro). Signal fort (marché très « pro »),
  absent de l'écran (seul un filtre existe dans la liste).
- **Surface de terrain** — présente par annonce dans la liste, mais le marché ne donne **aucune** statistique
  de surface (taille de lot médiane par commune) : 90 biens ont un terrain renseigné.
- **Historique de prix** — `bien_vs_marche` sait le rendre (`marche.py:305`), mais la base ne contient
  **qu'une ligne** → « aucune baisse enregistrée » partout, y compris pour un bien qui a réellement bougé.

---

## 5 · Ce qu'il faut enlever / changer, et le seuil de 30

**Combien de périmètres ont une vraie valeur** (sur les 3 scopes audités × types) :

| Bloc / colonne | Périmètres à vraie valeur | Recommandation |
|---|---|---|
| **> 90 j** (table) + « dont N > 90 j » + `biens_sup_90j` | **0** (0 `en_vente_longue` en base ; job `radar-cycle` non planifié — cf. RADAR-AUDIT-1) | **Changer la source** : calculer > 90 j depuis `date_publication` (comme le badge de la liste, `RadarEcran.tsx:81`) au lieu de `statut`, **ou** masquer la colonne tant que le cycle ne tourne pas. |
| **Baisses 30 j** (table + « ce qui a bougé ») + badge « Baisse » liste | **0** (1 ligne d'historique en base) | **Garder** (utile dès que les recaptures s'accumulent) mais **dire « 0 pour l'instant »** — dépend de recaptures répétées du même `list_id`. |
| **De retour** | **0** | Garder, même dépendance (`event_log` de changement de statut). |
| **Retirées 30 j** | 101 / 60 / 1 — mais **import en bloc** du 26/09 | **Changer le libellé** ou borner : ce n'est pas un flux de 30 jours, c'est le stock d'archives importé d'un coup. Trompeur tel quel. |
| **Écart par commune** (barres) | **1 seule** (St-Denis) ; libellé « maisons » mais calcul mixte ; diverge du chiffre du haut | **Corriger** (source maison-contre-maison, comme les 4 chiffres) **ou retirer** tant que < 2 communes atteignent n ≥ 30. Une barre unique n'est pas un « par commune ». |
| **Millésime DVF (pied)** | absent en vue Île | Afficher un millésime île (min/max des ventes) plutôt que rien. |

**Règle proposée pour le seuil de 30.** Aujourd'hui : la médiane demandée s'affiche à n ≥ 5, l'écart à
n ≥ 30 — donc l'écart est « sous le seuil » **presque partout** (sur la demande, seules Île-maisons n=132,
St-Denis-maisons n=35, Île-appts n=69 et St-Denis-appts n=47 franchissent 30 ; tout le reste est < 30).
L'acté DVF, lui, est presque toujours abondant (centaines à milliers de ventes) : le blocage vient
**toujours du côté demande**. Recommandation :
1. **Garder 30 pour le verdict** en toutes lettres (« marge de négociation probable ») — une affirmation a
   besoin d'un échantillon.
2. **Mais afficher l'écart en « indicatif · n=… » dès 5 ≤ n < 30** au lieu de « sous le seuil » sec, avec
   la mention du nombre d'annonces — la page cesse d'être majoritairement vide et reste honnête.
3. **Unifier le seuil du nombre et de l'écart** (§3-f) : soit les deux à 5 (indicatif), soit les deux à 30,
   pas 5 pour l'un et 30 pour l'autre sur la même carte.

---

## 6 · Synthèse

Tous les chiffres testés sont **arithmétiquement exacts** (affiché = recalculé sur les 3 périmètres). Les
problèmes sont de **cohérence** (deux chiffres pour un même concept), de **périmètre** (`a_qualifier` et
`retiree` comptés d'un côté pas de l'autre), et de **vide structurel** (colonnes à 0 faute de cycle de vie
et d'historique de prix). Aucune correction appliquée — audit en lecture seule.
