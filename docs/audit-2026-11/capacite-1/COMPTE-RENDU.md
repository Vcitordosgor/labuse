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
