# CAPACITÉ-1 — LOT B : correctifs de relecture

Branche `fix/capacite-1` (worktree `~/Desktop/labuse-capacite`). Aucune prod, aucun run servi recalculé,
aucun run île. Documents régénérés dans `~/Desktop/exports-audit-4/` (3 parcelles : HT0538 Saint-Pierre Ud ·
BI0351 La Possession N · DK0208 Saint-Paul UA). Chaque correction est citée depuis le **fichier livré régénéré**.

> Régénération directe (mêmes builders que les routes, parcelle par parcelle — `/tmp/regen_capacite.py`),
> cache de fiche vidé avant (une fiche périmée servait un `potentiel_transformation` vide). L'Étude de
> BI0351 et DK0208 reste un **document de refus** « simulation impossible » (aucun scénario d'implantation) :
> non touchée par B3/B4, donc non régénérée.

---

## B1 — Les 614 m² ne s'appellent plus « maximale réglementaire » ni « jusqu'à » : « estimation », facteurs écrits

Le 614 repose sur une **hypothèse** (occupation du gabarit 45 %, cf. DIAGNOSTIC §3) — ce n'est pas un maximum
réglementaire. Renommé **partout** (une seule source par document).

- **Source du libellé** (lu par Dossier/fiche/Comparatif/pré-dossier) : `declarations/fiche/reste_a_declarer.yaml`
  — `libelle: "Surface de plancher estimée, terrain libéré"` (était « SDP maximale réglementaire, terrain libéré »).
- **Facteurs écrits** sous la valeur : `src/labuse/exports/miroir.py` (dérivés des valeurs servies, aucun run).
- Libellés annexes alignés : `registre/donnees.py` (libellé canonique), `bilan/reperes.py` (Comparatif),
  `faisabilite/engine.py` (verdict : « estimation ~N m² » au lieu de « jusqu'à »), `api/pre_dossier.py`
  (« Surface de plancher estimée » au lieu de « jusqu'à »), `copilote_v2/resume_fiche.py`,
  `frontend/.../ComparePanel.tsx` (+ test `tests/test_capacite_max.py`), `flash/templates/rapport.html.j2`.

**Cité du Dossier régénéré** `97416000HT0538/01-dossier.pdf` §3 :
> `Surface de plancher estimée, terrain libéré    614 m²    estimé`
> `estimation : ~273 m² d'emprise × 45 % d'occupation (hypothèse, pas une règle du PLU) × 5 niveaux — hors stationnement et pleine terre`

**Cité du pré-dossier régénéré** `97416000HT0538/06-pre-dossier-pc.zip → …-regles-zonage.pdf` :
> `Capacité constructible — scénario « terrain libéré » … plancher estimée ~614 m². Pré-faisabilité sur
> règlement public (estimation, pas un certificat…)` (était « Surface de plancher jusqu'à ~614 m² »).

Plus aucune occurrence de « maximale réglementaire » / « jusqu'à » pour le 614 dans les documents livrés.

---

## B2 — BI0351 : la zone rouge du PPR rattachée à son VRAI aléa, pas à « Inondation » par défaut

Le PPR rouge de BI0351 est **multi-risque** : attribut `risque = INONDATION_MOUVEMENT_DE_TERRAIN` (mesuré en
base, 27 %+4 % = 31 %). L'Analyse d'annonce collait la zone rouge sur le **premier** aléa de la liste
(« Inondation ») et écrivait « mouvement de terrain : hors zonage PPR » (faux) + un niveau « Faible » (le dernier
vu, au lieu du plus fort).

- **Correctif** : `src/labuse/pige/api.py` `_risques_rows` — la zone PPR se rattache aux aléas que son libellé
  **nomme** (`ppr_hazards`), pas au premier ; le niveau affiché par aléa est le plus **fort** (repli ancien
  comportement si le libellé PPR ne nomme aucun aléa, pour ne pas orpheliner la zone). Test ajouté :
  `tests/test_annonce_pdf.py::test_risques_rows_ppr_multirisque_rattache_tous_les_aleas_nommes`.

**Cité de l'Analyse régénérée** `97408000BI0351/05-analyse-annonce-adresse.pdf` :
> `Inondation             Fort   Zone rouge · 31 %         Zone rouge du PPR La Possession (2018) …`
> `Mouvement de terrain   Fort   Zone rouge (même zone)    Zone rouge du PPR La Possession (2018) …`

Le mouvement de terrain porte désormais la zone rouge (« même zone », part dite une seule fois) et son niveau
**Fort** — plus de « hors zonage PPR » ni de « Faible ».

---

## B3 — HT0538 Étude p.3 : DPU, une seule formule (« non vérifié » des deux côtés)

Le DPU n'est **pas ingéré** pour Saint-Pierre → « non vérifié » (comme le Dossier §5). La colonne « Sur le
terrain » affichait pourtant « signalée », contredisant le libellé.

- **Correctif** : `src/labuse/exports/etude_faisabilite.py` — une contrainte « non vérifié / non ingéré »
  affiche « non vérifié » dans « Sur le terrain » et déplace la raison dans « Traitement » (plus jamais
  « signalée » en face de « non vérifié »).

**Cité de l'Étude régénérée** `97416000HT0538/08-etude-faisabilite.pdf` p.3 :
> `Droit de préemption urbain (DPU)   non vérifié   non vérifié — non ingéré pour cette commune ; à vérifier …`

---

## B4 — HT0538 Étude : couverture « À vérifier » honnête

Statut « À vérifier » (barème de stationnement non servi) mais le bandeau clamait « meilleure capacité
trouvée : 10 logements » et la colonne Places affichait « 0 ».

- **Correctif** : `src/labuse/exports/etude_faisabilite.py` — quand un garde-fou tombe, le bandeau dit
  « capacité **à vérifier** : au mieux ~N logements … À confirmer avant de retenir » (ton d'alerte) ; la colonne
  Places affiche « stationnement non vérifié » au lieu de « 0 » (barème non servi = non calculé, pas 0 exigé).
  Helper partagé `_bareme_stationnement_absent`.

**Cité de l'Étude régénérée** `97416000HT0538/08-etude-faisabilite.pdf` p.1 :
> `Logement collectif — capacité à vérifier : au mieux ~10 logements en R+4, stationnement aérien. À confirmer
> avant de retenir ce programme (voir « À vérifier » ci-dessous).`
> tableau : `Votre projet … R+4 … stationnement non vérifié … À vérifier`

---

## B5 — Exports texte (Markdown/HTML) alignés sur les PDF

Deux divergences : la fenêtre du marché du neuf (VEFA) servie « 36 mois » (les PDF disent « 5 ans ») et la
clause rassurante « (pas d'exclusion automatique) » servie sur une parcelle **non constructible** (BI0351).

- **Correctif** : helper unique `src/labuse/api/risques_arbitrage.py::ajuster_clause_affichage` (VEFA → « 5 ans » ;
  clause « exclusion automatique » retirée si non constructible, zone rouge + vigilance conservées), appelé par
  les exports texte (`src/labuse/api/export.py`, Markdown ET HTML) **et** par le Comparatif
  (`src/labuse/exports/blocs/comparatif.py`, qui portait sa propre copie) → une seule formule.

**Cité de la fiche Markdown régénérée** `97416000HT0538/10-export-fiche.md` :
> `Marché du logement neuf (VEFA) sur la commune : … (158 ventes VEFA / 5 ans) …` (était « / 36 mois »).

**Cité de la fiche Markdown régénérée** `97408000BI0351/10-export-fiche.md` (zone N, non constructible) :
> `PPR zone rouge sur 31 % de la surface — vigilance forte.` (la clause « (pas d'exclusion automatique) » a disparu).

**Cité du Comparatif régénéré** `_comparatif/cmp-comparatif-3-parcelles.pdf` : colonne BI0351 « … zone rouge sur
31 % de la surface — … » (clause retirée) ; marché du neuf « … ventes VEFA / 5 ans ».

---

## Fichiers régénérés (`~/Desktop/exports-audit-4/`)

| Parcelle | Documents régénérés |
|---|---|
| 97416000HT0538 | 01-dossier · 05-analyse-annonce · 06-pre-dossier-pc.zip · 08-etude-faisabilite · 10/11-export-fiche |
| 97408000BI0351 | 01-dossier · 05-analyse-annonce · 10/11-export-fiche (Étude = refus inchangé) |
| 97414000DK0208 | 01-dossier · 05-analyse-annonce · 10/11-export-fiche (Étude = refus inchangé) |
| _comparatif | cmp-comparatif-3-parcelles.pdf |

## Tests

- `tests/test_annonce_pdf.py` (B2, + nouveau test multi-risque), `tests/test_capacite_max.py` (B1 frontend),
  `tests/test_faisabilite.py` (verdict), `tests/test_risques_arbitrage.py` : **verts**.
- Hook pré-push (secrets · front tsc+vitest · pytest unitaires · cohérence 12 témoins) : voir § ci-dessous.

---

# CAPACITÉ-1 — LOT C : une seule « surface à retenir », deux grandeurs nommées (décision Vic, rejet de ma proposition)

La proposition du LOT A (faire du scénario « la » capacité) est écartée : le solveur est optimiste là où une
règle manque (à Saint-Pierre le stationnement **existe**, art. Ud6 ≈ 1 place / 75 m², il n'est pas ingéré →
888 m² est un **majorant**), il ne rend rien sur 8 parcelles / 11, et le plus grand chiffre irait contre la
règle « jamais de faux positif ». Documents régénérés : **HT0538** et **AD0887** (Le Tampon, Étude complète) +
**BI0351** (analyse). Chaque point cité depuis le fichier livré.

## C1/C2 — deux grandeurs nommées + LA règle unique « surface à retenir »

- **Deux noms, jamais confondus** : « **estimation rapide** » (moteur analytique, toute parcelle, base de la
  fiche/Dossier/Comparatif/classement) et « **scénario d'implantation** » (Étude).
- **Une seule fonction** `src/labuse/faisabilite/surface_retenue.py:surface_a_retenir`, lue par le Dossier (§3,
  via l'extracteur `robinet_fiche._c_surface_a_retenir` + `verdicts.verdict_potentiel`) ET par l'Étude
  (`etude_faisabilite`). Elle vaut le scénario **seulement si** une Étude existe et que son barème de
  stationnement est appliqué ; sinon l'estimation rapide. L'estimation rapide est lue **en direct**
  (`estimation_rapide_m2` → `parcel_faisabilite`, table rase) pour concorder entre documents même sur une
  parcelle bâtie (colonne `sdp_max` du run partielle). Le Dossier relit le scénario **persisté** (révision),
  sans rejouer le moteur (trop lent).

**Cité — HT0538 Dossier §3 ET Étude** (même phrase) :
> `Surface à retenir : 614 m² (estimation rapide). Le scénario dessiné atteint 888 m², non retenu tant que le
> stationnement n'est pas vérifié.`

**Cité — AD0887 Dossier §3 ET Étude** (même phrase) :
> `Surface à retenir : 795 m² (scénario d'implantation, stationnement déduit). L'estimation rapide donnait
> 1 047 m², hors stationnement.`

## C3 — l'Étude explique l'écart en une phrase chiffrée

**Cité — HT0538 Étude** : `Écart avec l'estimation rapide : occupation supposée 46 % du gabarit contre 67 %
dessinée ; le scénario ne déduit PAS le stationnement (règle existante, non ingérée par LABUSE).`
(Les % d'occupation sont **dérivés par parcelle** `sdp ÷ (zone × niveaux)`, d'où ~45–49 % selon l'assiette.)
**Cité — AD0887 Étude** : `… occupation supposée 49 % du gabarit contre 37 % dessinée ; stationnement déduit.`

## C4 — « règle existante, non ingérée par LABUSE » (plus « non opposable » / « aucun ratio »)

Corrigé dans `etude_faisabilite.py` (section Stationnement + garde-fou), `implantation/controles.py` (libellé
du contrôle), `faisabilite/engine.py` (avertissement) **et `DIAGNOSTIC.md`**.
**Cité — HT0538 Étude** : `Stationnement non vérifié — la règle de stationnement de cette zone existe au
règlement du PLU mais n'est pas ingérée par LABUSE …` ; contrôle : `Stationnement | règle existante, non
ingérée par LABUSE | … | À confirmer`.

## C5 — BI0351 : le mouvement de terrain affiche ses trois niveaux avec leurs parts

**Cité — BI0351 Analyse d'annonce** :
> `Mouvement de terrain   Fort 4 % · Moyen 27 % · Faible 69 %   Zone rouge (même zone)   Zone rouge du PPR La
> Possession (2018) …`
(plus « seulement le plus fort » ; la part de chaque niveau est dans la colonne NIVEAU). Le rattachement B2
reste : la zone rouge porte inondation ET mouvement de terrain.

## C6 — garde-fou : un seul « surface à retenir » par parcelle

`tests/test_surface_retenue.py` : règle pure (sans/avec Étude, stationnement appliqué ou non, jamais le plus
grand par défaut) + test `reel` `test_un_seul_surface_a_retenir_par_parcelle` qui **échoue si le chemin Dossier
et le chemin Étude divergent** pour HT0538 (tous deux retiennent 614, estimation rapide). **Vert.**

## C7/C8 — le Comparatif ET le pré-dossier lisent la MÊME fonction (relance Vic)

La règle devait être lue par *tous* les documents : le Comparatif et le pré-dossier sont maintenant
branchés sur `surface_a_retenir(estimation_rapide_m2, scenario_etude_persiste)` — la même expression que
le Dossier (§3) et l'Étude.

- **Comparatif** : `compare()` (api/app.py) pose `surface_a_retenir` par parcelle ; `exports/blocs/comparatif.py`
  ajoute la ligne **« Surface à retenir »** (sous « Plancher possible · reconstruction »). Sur AD0887, le
  plancher reconstruction (1 047 m², estimation rapide) n'est **jamais** présenté comme capacité sans la ligne
  qui tranche.
  **Cité — `_comparatif/cmp-comparatif-ad0887.pdf`** (colonnes AD0887 · HT0538 · DK0208) :
  > `Plancher possible · reconstruction   1 047 m²   614 m²   153 m²`
  > `Surface à retenir   795 m² (scénario d'implantation)   614 m² (estimation rapide)   153 m² (estimation rapide)`
- **Pré-dossier** : `api/pre_dossier.py` ajoute la phrase « surface à retenir » à la section Capacité.
  **Cité — `97422000AD0887/06-pre-dossier-pc.zip → …-regles-zonage.pdf`** :
  > `… retenir : 795 m² (scénario d'implantation, stationnement déduit). L'estimation rapide donnait 1 047 m², hors stationnement.`
  **Cité — `97416000HT0538/06-pre-dossier-pc.zip`** :
  > `… Surface à retenir : 614 m² (estimation rapide). Le scénario dessiné atteint 888 m², non retenu tant que le stationnement n'est pas vérifié.`

## C9 — garde-fou étendu aux quatre documents

`tests/test_surface_retenue.py::test_un_seul_surface_a_retenir_tous_documents` (paramétré HT0538 **et**
AD0887) : le chemin « persisté » (Dossier/Comparatif/pré-dossier, expression partagée) doit égaler le chemin
LIVE de l'Étude, HT0538 → 614 (estimation), AD0887 → **795 (scénario), jamais 1 047**. **Vert.**

## Hors lot (à faire, listé seulement)

1. **Ingérer les barèmes de stationnement** des communes où ils manquent (Saint-Pierre art. Ud6, etc.) — alors
   l'Étude déduira le stationnement et « surface à retenir » pourra retenir le scénario.
2. **Recaler le 45 %** (coef d'occupation) sur les résultats du solveur là où le stationnement est connu
   (ex. occupation dessinée mesurée), pour rapprocher estimation rapide et scénario.

## Tests LOT C

- `tests/test_surface_retenue.py` (règle + garde-fou reel), `tests/test_annonce_pdf.py` (C5 niveaux), registre
  intègre (`surface_a_retenir` déclarée + servie par le robinet constructibilité) : **verts**.
