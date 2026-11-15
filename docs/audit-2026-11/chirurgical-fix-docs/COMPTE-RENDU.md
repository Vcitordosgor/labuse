# CHIRURGICAL-FIX-DOCS — compte rendu

> Corrections des écarts relevés par AUDIT-CHIRURGICAL-2 (`docs/audit-2026-11/chirurgical-2/ECARTS-2.md`).
> Branche **`fix/chirurgical-docs`**, créée depuis `origin/main` puis **merge** de `audit/chirurgical-1`
> (pour garder les rapports d'audit). La branche `audit/chirurgical-1` reste à son dernier commit d'audit
> (`91c8cf50f`), **sans code modifié**.
> Une autre session corrige en parallèle sur `fix/chirurgical-1` (E100–E119 + lot H) — voir §Fusion.

---

## LOT E — « Surface à retenir » (E5)

**Symptôme** — BW2635 (copropriété bâtie) : le Dossier écrivait « Surface à retenir : **3 317 m²** » (> la
parcelle, 2 003 m² ; 4× la SDP résiduelle 827), alors que l'Étude retenait **2 625 m²**.

**Cause (pourquoi Dossier et Étude divergeaient)** — `exports/etude_faisabilite.scenario_etude_persiste`
reconstruisait la config d'étude PAR DÉFAUT **sans** `terrain` ni `niveaux_sous_sol`, mais l'empreinte
`implantation.service._study_id` HACHE ces clés, et la prod persiste la révision avec les défauts de
`EtudeIn` (`terrain="libere"`). Résultat : `terrain=None` ≠ `"libere"` → **study_id différent** → l'esquisse
n'était **pas relue** (`charger()` → None) → le Dossier retombait sur l'estimation rapide (la plus grande),
pendant que l'Étude calculait l'esquisse en direct. Prouvé : lookup `EF-a775dd0d172c` (None) vs persisté
`EF-67596bb6e11b` (trouvé).

**Correctifs**
1. `exports/etude_faisabilite.py` (**changement minimal**, une autre branche y travaille) —
   `scenario_etude_persiste` reconstitue la config par défaut COMPLÈTE (mêmes clés/défauts que `EtudeIn`,
   dont `terrain="libere"`). → Dossier et Étude relisent la MÊME esquisse (BW2635 : 2 625 des deux côtés).
2. `faisabilite/surface_retenue.py` — `surface_a_retenir(..., bati=…, copropriete=…)` : sur une parcelle
   **bâtie**, le chiffre retenu nomme son scénario **« Terrain libéré (démolition) : Y m² »** (Y = la plus
   prudente entre estimation rapide et esquisse — la règle « plus petite des deux » inchangée), distinct de
   la SDP **« bâti conservé »** (rendue par le §3). En **copropriété**, la démolition est signalée *« peu
   réaliste… chiffre indicatif »* et n'est jamais le chiffre mis en avant. Jamais un chiffre nu sans scénario.
3. `exports/robinet_fiche._c_potentiel` — passe `bati`/`copropriete` (lus sur la fiche servie :
   `le_bien.nb_batiments`/`emprise_batie_m2`, `score_v2.copro`/`coproprietes`).

**Après** — §3 BW2635 : *« …bâti conservé ≈ 827 m²… Terrain libéré (démolition, peu réaliste en copropriété
— chiffre indicatif) : 2 625 m² (esquisse…). L'estimation rapide donnait 3 317 m². »*
**Garde-fou** — `tests/test_surface_retenue.py` : +4 tests unitaires (bâti → démolition nommée ; copropriété
→ jamais le plus grand + « peu réaliste » ; bâti SANS Étude → scénario nommé, jamais un chiffre nu ; terrain
nu → libellé historique). Test `reel` étendu à **BW2635** (2 625, jamais 3 317) — 3/3 passent (65 s).

---

## LOT F

### E4 — Numéro de rapport unique
`exports/numeros.numero_rapport` portait `idu[-4:]` → deux parcelles de même suffixe (AY0153 / CO0153)
recevaient le même numéro le même jour (434 582 parcelles, 4 358 suffixes). **Fix** : on porte l'**IDU
entier** (comme l'affirmait déjà l'en-tête du module). `provenance.py` : regex du n° de rapport élargie au
suffixe alphanumérique. Tests : `test_exports2_lot1` (forme IDU entier **+ nouveau test d'unicité AY0153 ≠
CO0153**), `test_exports2_lot2`, `test_annonce_pdf` mis à jour.

### E7 — Apporteur : date d'approbation du PLU = celle de la fiche
`exports/blocs/apporteur.py` imprimait `statut_plu.approbation_sudocuh` (approbation d'ORIGINE Sudocuh,
ex. 08/12/2018), périmée vs la fiche (document opposable `plu_fraicheur.horizon`, ex. 2023-08-11). **Fix** :
l'Apporteur prend la date **opposable de la fiche** (`horizon`), Sudocuh en repli ultime. Vérifié sur 4
parcelles (AD0887 11/08/2023, AM0838 17/09/2025, IS0448 05/08/2026, HT0538 25/06/2024 = fiche). Garde-fou :
`tests/test_apporteur_plu_date.py`. **Fichier partagé (Apporteur) — changement minimal, voir §Fusion.**

### E8 — Estimer : prix de secteur = celui de la fiche ; le chiffre ESTIMER-3 est nommé
L'« estimation du prix au m² » (ESTIMER-3, pondérée pour LE bien) était lue comme le prix du secteur et
divergeait de la fiche (AY0153 +13,7 %, BW2635 +17 %). **Fix** : `pige/api.rapport_parcelle` expose
`est["secteur_fiche"]` = **médiane `prix_ancien` de la fiche** (écran == PDF) ; `exports/blocs/annonce._estimation`
affiche **« Prix médian du secteur (fiche) : N €/m² »** (= fiche) et nomme l'autre chiffre **« Prix estimé au
m² — ce bien … ce n'est pas le prix médian du secteur »**. Vérifié : AY0153 2 333, BW2635 3 000 = fiche.
Garde-fou : `tests/test_estimer_secteur_fiche.py`. **Fichiers partagés (Estimer : annonce.py, pige/api.py) —
changement minimal, voir §Fusion.**

### E11 — Dossier : table des comparables = même population que le chiffre de tête
`exports/robinet_fiche._c_comparables` servait les comparables ESTIMER-3 (des ventes de **terrain** pour un
terrain nu) sous le médian de tête **bâti** (`prix_ancien`). **Fix** : la table est filtrée à la famille du
médian servi (bâti → ventes bâties ; jamais du terrain sous une médiane de bâti) ; si rien ne correspond
(bien nu), pas de table (le repère « Terrain nu — secteur » reste au §8). Vérifié : HT0538/CV0446 → plus de
table terrain ; AD0887 → 8 ventes Maison conservées. Garde-fou : `tests/test_dossier_comparables_population.py`.

### C-iii — Dossier §2 cohérent avec §3
`exports/verdicts.verdict_zonage` disait « urbaine, constructible » (niveau famille) même quand le §3
concluait « non retenue — habitat interdit » (AM0838 zone UE, AO1198 terrain exigu). **Fix** : quand le bloc
potentiel porte une `cause` de non-constructibilité, le §2 nomme la famille (« zone urbaine ») mais dit
*« cette parcelle n'est pas retenue comme constructible (voir §3) »* ([warn]). La **saturation** (zone
constructible, SDP consommée, sans `cause`) garde « constructible ». Garde-fou :
`tests/test_dossier_section2_coherente.py`. **Fichier partagé (Dossier : verdicts.py) — changement minimal.**

---

## LOT G — Plafond d'export (clarification + relèvement Intégral)

- **Plan du compte de test** : `AUDIT-TEST` était en plan **`integral`** (créé puis supprimé par l'audit).
- **Relèvement (décision Vic)** : le plafond **Intégral passe de 30 à 120 exports/jour**. Les autres formules
  ne changent pas. Essentiel est désormais **pinglé** à 30 dans `PLAFONDS_JOUR` (il suivait le défaut) pour ne
  pas bouger par accident. Le message de dépassement dit le **chiffre** ET l'**heure de remise à zéro** (minuit,
  heure de La Réunion — le compteur est journalier). Test : `tests/test_offres.py` (chiffre + remise à zéro +
  `PLAFONDS_JOUR` 120/30 sans inversion).
- **Plafonds par plan** (`quota.PLAFONDS_JOUR` / `PLAFOND_DEFAUT`, par JOUR, par compte, `kind="export"`,
  compteur `usage_compteurs`) :
  | Plan | Plafond export / jour |
  |------|-----------------------|
  | **Intégral** (349 €/mois) | **120** (était 30) |
  | **Essentiel** | 30 **+** quota mensuel de Dossiers parcelle = **20/mois** (`config.dossier_quota_mois`) |
  | `interne` / `illimite` (admin/legacy, non commercial) | illimité (10⁹) |
  | **Flash** (rapport à l'unité) | **hors quota** (jamais compté) |
- **Pas d'inversion de prix** : Essentiel (moins cher) reste à 30 < Intégral (plus cher) à 120. Aucune formule
  moins chère ne dépasse une formule plus chère.
- **Documents gatés** (comptent un export chacun — `porte_export`) : **Dossier, Gabarit, Apporteur, Estimer
  (par parcelle), Estimer (par lien), Étude de zone, Pré-dossier, Comparatif** = 8 types. **NON gatés** :
  Bilan (PDF/Excel), Courrier, Étude de faisabilité, stationnement, Flash.
- **Consommation d'UNE parcelle** (jeu complet de ses documents gatés) : Dossier + Gabarit + Apporteur +
  Estimer-parcelle + Étude-de-zone + Pré-dossier = **6 exports**. (Comparatif et Estimer-par-lien sont
  transverses, hors « une parcelle ».) → avec 30/jour (Intégral), **le plafond est atteint après ~5
  parcelles/jour** ; d'où le 429 rencontré en générant les 12 parcelles de l'audit. L'audit a contourné
  proprement (mode pilote sans session, hors quota, + Apporteur rendu en process) — aucune donnée servie
  touchée.

---

## Hors mandat — à traiter ailleurs (listés, non corrigés ici)
- **E9** — citations PLU sans verbatim justificatif (AY0153 zone UA absente des extraits ; CV0446 U5 non
  rattachable, extraits St-Joseph `pagination_ambigue` + `article_ref` mal parsé ; AR1517 « Ua » alors que le
  règlement n'a qu'une zone « U »). Problème de **données** `plu_reglement_extrait` (ingestion), hors du
  périmètre « documents » de ce lot.
- **E6** — l'Étude de faisabilité chiffre un collectif sur une zone à habitat interdit (AM0838). **Traité
  ailleurs** (moteur d'implantation `exports/etude_faisabilite.py` — une autre branche y travaille).

---

## Fusion avec `fix/chirurgical-1` (session parallèle : E100–E119 + lot H)

L'autre session touche Bilan Excel, **alertes de l'Apporteur**, notice PCMI4, **Comparatif**, **libellés du
Dossier**, **Estimer sur parcelle non constructible**. Sur les fichiers partagés, j'ai fait le **plus petit
changement possible** — à reporter au merge :

| Fichier partagé | Mon changement (CHIRURGICAL-FIX-1) | Zone |
|-----------------|-------------------------------------|------|
| `exports/blocs/apporteur.py` | E7 : la ligne « PLU approuvé le … » prend `statut_plu.horizon` avant `approbation_sudocuh` (bloc `_coup_d_oeil`, ~l.182) | une seule branche `if isinstance(plu, dict)` |
| `exports/blocs/annonce.py` | E8 : dans `_estimation`, reformulation de la note bâti + ligne « Prix médian du secteur (fiche) » (`est["secteur_fiche"]`) | bloc bâti + construction `gauche` |
| `pige/api.py` | E8 : `rapport_parcelle` pose `est["secteur_fiche"]` depuis `fiche.prix_ancien` (juste après `_est_bloc_depuis_estimer3`) | 7 lignes additives |
| `exports/verdicts.py` | C-iii : `verdict_zonage` tempère « constructible » si `potentiel_verdict.cause` (branche `fam in _CONSTRUCTIBLE`) | 1 branche |
| `exports/robinet_fiche.py` | E5 (bati/copro dans `_c_potentiel`) + E11 (filtre `_c_comparables`) | 2 extracteurs distincts |
| `exports/etude_faisabilite.py` | E5 : config par défaut complète dans `scenario_etude_persiste` (4 lignes) | 1 fonction |
| `exports/numeros.py`, `exports/provenance.py` | E4 : IDU entier + regex | non partagés avec leur lot a priori |

Aucun des changements ne touche le Bilan Excel, la notice PCMI4, ni le chemin « Estimer sur parcelle non
constructible » (E8 porte sur le libellé du prix bâti, pas sur le cas non constructible).

---

## Vérification
Tous les tests touchés/ajoutés verts : `test_surface_retenue` (8+3 reel), `test_apporteur_plu_date` (2),
`test_estimer_secteur_fiche` (2), `test_dossier_comparables_population` (3), `test_dossier_section2_coherente`
(3), `test_exports2_lot1/2`, `test_annonce_pdf` — **55 passed** (hors `reel`). Hook complet rejoué au push.
