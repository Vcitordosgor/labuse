# DONNEES-4 — un oracle indépendant pour le Dossier

Branche `feat/donnees-4` depuis main **aa50ff56** (après merge de feat/donnees-3). Un commit.

## Le trou
`captures/rebranchement2/preuve_ecran_pdf.py` comparait la valeur des **extracteurs**
(`res.valeurs = collecte(fiche)`) au **PDF rendu depuis ces mêmes extracteurs**. Les deux colonnes
dérivent du même code : un extracteur qui lit une mauvaise clé renvoie `None`, le miroir imprime la
phrase d'absence, et « absent = absent » passe pour conforme. C'est ce qui avait caché le bug OCS GE
(`artif_pct`). Pas d'oracle indépendant sur le champ réel du payload.

## L'oracle (`src/labuse/exports/oracle_dossier.py`)
Pour chaque ligne du Dossier, l'oracle lit la valeur **là où la fiche RÉACT la lit** — le chemin du
COMPOSANT front (relevé par deux traçages indépendants des composants `fiche/*.tsx`), **pas** celui
de l'extracteur. Règle : **si le payload a une valeur au chemin du composant et que l'extracteur
renvoie `None` → écart « extracteur muet »**.

- `ORACLE` : 61 données → chemin(s) `f` du composant (feuille scalaire ou conteneur de liste).
- `ORACLE_FN` : 2 données à affichage CONDITIONNEL (`dpu_perimetre` : ligne seulement si
  `etat=='servi'` ; `peb_zone` : seulement si zone ∈ A/B/C/D) — l'oracle réplique la condition pour
  ne pas confondre un sentinel (`non_determinee`, `hors`) avec une valeur.
- `HORS_PAYLOAD` : 10 données que la fiche React rend depuis une **autre requête** que
  `/parcels/{idu}` (`getFaisabilite`, `getParcelExposition`, `getOrthoEquipements`, `/v2/score`,
  `modParcellePermis`) ou via `f.lines` (couche générique) — l'oracle du payload ne peut pas les
  confronter à l'écran, c'est dit. 61 + 2 + 10 = 73 = tous les extracteurs.

L'oracle est branché dans `preuve_ecran_pdf.py` : la branche « absence » demande d'abord à l'oracle
si le payload a une valeur → si oui, `ÉCART : extracteur MUET`, avant tout « absente dite ».

## Rejeu sur AN0347, BO0765, BO0852 et une parcelle simple (97411000AB0346)
`DONNEES-4-oracle-avant-apres.txt` :

```
===== AVANT (extracteurs d'origine) =====
EXTRACTEURS MUETS (l'oracle a une valeur, l'extracteur renvoie None) :
  nature_toit       AN0347='non déterminée — pans non nets…'
  pente_toit_deg    AN0347=11.6
TOTAL : 2 extracteur(s) muet(s).

===== APRÈS (extracteurs corrigés) =====
EXTRACTEURS MUETS : 0
```

## Les extracteurs muets trouvés — corrigés / signalés
- **`pente_toit_deg`** — lisait `toit.pente_deg` (clé absente) ; le toit porte `pente_mediane_deg`.
  **Corrigé** (mauvaise clé, comme OCS GE). La fiche React lit `toit.pente_mediane_deg`.
- **`nature_toit`** — lisait `toit.forme_libelle` / `toit.forme` (clés absentes, dérive de schéma) ;
  le toit porte `libelle` / `libelle_court`. **Corrigé** vers `libelle` (ce que lit React).

Faux positifs de l'oracle brut, **écartés** (l'extracteur renvoie `None` À BON DROIT, la fiche
React n'affiche pas de valeur non plus) — l'oracle a été affiné pour ne pas les signaler :
- `dpu_perimetre` (`etat='non_determinee'`) et `peb_zone` (`zone='hors'`) : React n'affiche qu'une
  **note** (FactNote), pas une valeur (FactRow) ; l'extracteur skippe le sentinel — correct.
- `capacite_logements` : rendu par `getFaisabilite`, pas le payload `f` ; `capacite_estimee` n'est
  qu'un drapeau `False` → **HORS_PAYLOAD**.

Divergence de clé **signalée** (pas un muet sur ces 4 parcelles, mais deux chemins distincts) :
- `historique_permis_liste` : l'extracteur lit `f.depots.parcelle`, la fiche React lit
  `f.historique_site.permis` (deux vues du permis). À trancher par Vic.

## Preuve — test qui casse si on remet `artif_pct`
`tests/test_oracle_dossier.py::test_oracle_attrape_artif_muet_si_mauvaise_cle` : sur un payload
`{le_bien:{ocsge:{part_artif_pct:12.6}}}`, l'oracle lit 12,6 et l'extracteur DOIT rendre 12,6 ; si
`_c_artif` relit `artif_pct` (la mauvaise clé), il renvoie `None` → assertion « extracteur MUET »
casse. Idem pour les deux toits, les sentinels DPU/PEB, et la couverture (chaque extracteur ∈ oracle
ou hors-payload).

## Portes de recette
- **tsc -b** vert (aucune modif front).
- **circuit verrous -w G8** vert.
- **pytest tests/ complet** : 0 échec nouveau (voir commit).
