# RECETTE-10 — le Financier au propre, et ce que vaut le score

Branche `fix/recette-10` depuis `fix/recette-9` · worktree `~/Desktop/labuse-recette6`.
**Règle de preuve** : un travail n'est fait que prouvé sur l'artefact final (PDF régénéré ou capture
depuis le vrai chemin). Aucun merge, aucune bascule, `:8020`/`q_v14` intacts.

Artefacts : `docs/audit-2026-09/captures-recette-10/`.

---

## T1 🔴 — La surélévation était fausse dans l'autre sens — FAIT

**Le défaut.** RECETTE-9 T9 a branché le LiDAR sur la surélévation mais a comparé l'égout **mesuré**
(3,0 m) à la règle de **faîtage** (10,0 m) : `10,0 − 3,0 = 7,0 m disponibles`. E1 comparait un faîtage
à une règle d'égout (marge sous-estimée) ; T9 a fait l'inverse (marge gonflée de plus du double). La
règle citée deux pages plus haut dans le même Dossier dit pourtant **10 m au faîtage · 7 m à l'égout**.

**Le bon calcul — les deux contraintes, la plus serrée mord** (parcelle `97411000EL0157`, Saint-Denis) :
- à l'égout : 7,0 (règle `he_m`) − 3,0 (égout mesuré) = **4,0 m**
- au faîtage : 10,0 (règle `hf_m`) − 6,9 (faîtage mesuré) = **3,1 m**
- **disponible réel : 3,1 m, limité par le faîtage.**

Recalcul à la main sur trois parcelles mesurées (table `batiment_hauteur_lidar`, règles `he/hf` de zone) :

| parcelle | égout mes. | faîtage mes. | he | hf | marge égout | marge faîtage | **retenue** | mord |
|---|---|---|---|---|---|---|---|---|
| 97411000EL0157 | 3,0 | 6,9 | 7 | 10 | 4,0 | 3,1 | **3,1** | faîtage |
| 97411000AB0006 | 4,4 | 8,3 | 7 | 10 | 2,6 | 1,7 | **1,7** | faîtage |
| 97411000AB0009 | 4,3 | 7,0 | 7 | 10 | 2,7 | 3,0 | **2,7** | égout |

(les trois cas, la contrainte mordante bascule selon la géométrie du toit — c'est exactement ce que le
LiDAR apporte : deux hauteurs distinctes, chacune appariée à SA règle.)

**Le correctif.**
- `faisabilite/potentiel.py::surelevation_mesuree(he_regle, hf_regle, egout_mesure, faitage_mesure)` :
  nouveau point de calcul unique. Chaque contrainte apparie règle et mesure **de la même base** ; la
  plus serrée décide ; renvoie `{marge_m, possible, contrainte, contraintes[]}`. `surelevation`
  expose désormais `he_regle_m`/`hf_regle_m` bruts (les deux règles, pas seulement le faîtage).
- `api/app.py::_potentiel_transformation_block` : quand le LiDAR a mesuré, appelle `surelevation_mesuree`
  au lieu de `hauteur_regle − égout`. Sert `hauteur_contrainte` (« égout »/« faîtage ») + `hauteur_contraintes`.
- `exports/blocs/potentiel.py` : la phrase dit **laquelle** des deux mord et montre les deux calculs.
- Fiche parcelle (`constructibilite.tsx`) : « possible (marge ~3,1 m, limité par le faîtage) ».
- `exports/collecte.py` : le collecteur registre `marge_surelevation_m` sert la marge mesurée LiDAR.

**Le test anti-inversion** (`tests/regles/test_surelevation.py`) : une règle d'égout ne se compare
jamais à un faîtage, ni l'inverse — chaque marge = règle − mesure appariées par base ; le résultat ne
peut valoir aucun croisement (ni `10−3=7`, ni `7−6,9=0,1`). Plus le cas EL0157 recalculé (3,1, faîtage).

**Autres cohabitations vérifiées** : `copilote/moteurs.py` (Densifier) dérive un NOMBRE DE NIVEAUX de
`he_m` (`int(he//étage)`), pas une marge — pas d'inversion. `exports/blocs/apporteur.py` n'imprime que
la hauteur du bâti, aucun calcul de surélévation. Le chemin BD TOPO (sans LiDAR) reste faîtage-contre-
faîtage (RECETTE-7, inchangé).

**Preuve — artefact final.** Dossier régénéré `captures-recette-10/T1-dossier-EL0157.pdf` (+ archive JSON).
Bloc 3 imprime : « Surélévation possible — **3,1 m disponibles, limité par le faîtage** (mesuré au
LiDAR HD). égout 3,0 m mesuré contre 7,0 m réglementaires (marge 4,0 m) · faîtage 6,9 m mesuré contre
10,0 m réglementaires (marge 3,1 m). » Chemin réel : `_q_v2_fiche` → `construire(..., 'dossier')`.

---

## T3 — Natures fausses dans le bilan (sourcé → ƒ dérivé) — FAIT

**Le défaut.** `Coût de construction -717 k€` portait la pastille **sourcé**. C'est un PRODUIT
(plancher × €/m²) : le taux au m² est sourcé, le **montant ne l'est pas**. Idem `Taxe d'aménagement`.
Cause : `exports/blocs/financier.py` tamponnait le MONTANT selon l'origine de son ENTRÉE (pré-remplie
sourcée → « sourcé »).

**Le correctif — toutes les lignes des deux tableaux reprises depuis la nature réelle du montant :**
- `financier_bilan.py::_postes` : tout montant PRODUIT d'une formule affichée par le bloc
  (construction, honoraires, VRD, stationnement, aléas, redevance, portage, frais d'acquisition,
  taxe d'aménagement) est **ƒ dérivé**. Seuls la **démolition** et la **dépollution**, montants
  forfaitaires saisis tels quels, restent **projet**.
- `financier.py::_bilan_rebours` : suppression de l'override qui rendait le montant « sourcé ». Le
  taux sourcé reste montré dans l'encart « Hypothèses du porteur » (là est sa place). Seule exception :
  la taxe SAISIE au forfait par le porteur → `projet`.
- `_bilan_rebours` « Marge visée » (marge % × CA) et `_face_prix` « Ce que l'opération supporte »
  (CA − Σ − marge) → **ƒ dérivé** (n'étaient pas des estimés/projets).

**Preuve — artefact final** `captures-recette-10/T3-T4-financier-charge-negative.pdf` (Financier réel,
compte de test isolé puis purgé) : Coût de construction **-1 658 k€ · ƒ dérivé** ; Honoraires · VRD ·
Taxe d'aménagement · Marge visée · Charge foncière **tous ƒ dérivé** ; le €/m² sourcé reste dans
l'encart « Hypothèses du porteur ». Test `test_recette10_financier::test_t3_*`.

---

## T4 — Une charge foncière négative ne se dit pas en euros négatifs — FAIT

**Le défaut.** « elle supporte au mieux **-141 788 €** de charge foncière » — un euro négatif ne veut
rien dire pour un lecteur.

**Le correctif** (`financier.py`) — trois endroits où le signe négatif passait tel quel :
- **Verdict** (`_verdict`) : « Dans ces hypothèses, l'opération ne peut supporter **aucun achat de
  terrain** : il lui manque {|charge|} pour seulement atteindre l'équilibre à un prix de terrain nul. »
- **Tuile hero** : « aucune » + « charge foncière — manque {…} à terrain nul » (plus de « -142 k€ »).
- **Face au prix** (`_face_prix`) : « Ce que l'opération supporte » → « aucune — manque … » ; « Seuil de
  rentabilité » négatif → « aucun prix d'achat viable — il manque … même à un terrain nul » ; « Marge
  résiduelle » négative → « négative (X %) — au prix demandé, l'opération perd de l'argent ».

**Preuve — artefact final** (même PDF) : verdict « l'opération ne peut supporter **aucun achat de
terrain** : il lui manque **1 055 098 €** pour seulement atteindre l'équilibre à un prix de terrain
nul » ; « Ce que l'opération supporte : **aucune — manque 1 055 098 €** » ; « Marge résiduelle :
**négative (-196,1 %) — l'opération perd de l'argent** ». Test `test_t4_*`.

---

## T5 — Garde : prix au bailleur social au-dessus du prix libre — FAIT

**Le défaut.** Le questionnaire a accepté **5 500 €/m² au bailleur social** contre **4 500 €/m² en
libre**. Une vente EN BLOC à un bailleur est TOUJOURS inférieure au prix libre (décote de
commercialisation en bloc).

**Le correctif** — sur le modèle exact de la garde de vraisemblance du prix de sortie (`_hors_marche`,
RECETTE-6 E2) : `financier_bilan.py::_hors_marche` ajoute une garde **relationnelle** — `prix_bailleur >
prix_libre` ⇒ hypothèse hors marché, le bilan n'est PAS publié, le champ est nommé, avec un conseil de
correction dédié (« il doit rester sous le prix de vente libre »). La borne absolue (12 000 €/m²) reste
active en plus.

**Preuve — artefact final** `captures-recette-10/T5-financier-bailleur-hors-marche.pdf` : généré sur
l'**état réel du questionnaire de la recette** (compte NULL, bailleur 5 500 / libre 4 500 / part
sociale 20 %). Le Financier affiche : « **Hypothèse hors marché** — le bilan n'est pas établi. Le champ
« Prix de vente au bailleur social » vaut **5 500 €/m²** : il dépasse le prix de vente libre (4 500 €/m²)
— une vente EN BLOC à un bailleur social est toujours inférieure au prix du marché libre. Corrigez le
prix au bailleur … ». Tests `test_t5_*`.

---

## T2 — Le questionnaire Financier : solide, ou on le retire — FAIT

### T2a — le bandeau qui ne disparaissait pas

**Le défaut.** La bannière « LABUSE n'a pas pu chiffrer de programme… renseignez le nombre de
logements » (`data-financier-programme`) s'affichait sur **les quatre étapes** et **restait après**
que le porteur ait répondu (elle lisait `data.programme.auto`, statique côté serveur, jamais l'état de
saisie). Un avertissement qui ne disparaît pas devient du décor.

**Le correctif** (`FinancierQuestionnaire.tsx`) : la bannière ne s'affiche **qu'à l'écran qui porte le
champ `logements_vises_saisi`** ET tant que ce champ est **vide** ; dès qu'il est renseigné, elle
disparaît. Prouvé par `FinancierQuestionnaire.test.tsx::T2a`.

### T2b — le tri des questions

Analyse des 20 champs (qui remplit · effet sur le bilan · si vide) → verdict :

| champ | qui le remplit | effet sur le bilan | si vide | verdict |
|---|---|---|---|---|
| Prix de vente prévu (€/m²) | le porteur (obligatoire) | c'est le chiffre d'affaires | bilan non établi | **garder** |
| Régime de TVA | le porteur (obligatoire) | HT vs TTC | bilan non établi | **garder** |
| Coût de construction (€/m²) | pré-rempli, souvent ajusté | 1er poste du bilan | médiane régionale | **garder** |
| Prix demandé pour le terrain | le porteur | la confrontation charge/prix | pas de face-à-face | **garder** |
| Marge visée (%) | pré-rempli, ajusté | déduit du CA | 9 % d'usage | **garder** |
| Nb de logements visés | le porteur si pas de potentiel | débloque la surface vendable | programme non chiffré | **garder** (conditionnel) |
| Typologie moyenne | le porteur si pas de potentiel | surface vendable | T3 par défaut | **garder** (conditionnel) |
| Part de logement social (%) | rare | pondère le CA si bailleur | 0 % | **affiner** |
| Prix de vente au bailleur (€/m²) | rare | CA de la part sociale | ignoré | **affiner** |
| Frais d'acquisition (%) | pré-rempli | frais d'acq. | 7 % | **affiner** |
| Coût de démolition | si bâti existant | poste démolition | non chiffré | **affiner** |
| Dépollution / étude de sol | rare | poste dépollution | non chiffré | **affiner** |
| Honoraires techniques (%) | pré-rempli | % du coût | 12 % | **affiner** |
| VRD (€/m²) | pré-rempli | × terrain | 90 €/m² | **affiner** |
| Coût par place de stationnement | rare | × logements | non chiffré | **affiner** |
| Provision pour aléas (%) | pré-rempli | % du coût | 4 % | **affiner** |
| Taxe d'aménagement | pré-remplie (calcul LABUSE) | poste taxe | calculée | **affiner** |
| Durée de portage (mois) | pré-remplie | portage | 29 mois | **affiner** |
| Taux d'emprunt (%) | rare | portage | forfait 3 % du CA | **affiner** |
| **Scénario du projet** | pré-rempli « reconstruction » | **aucun** (W3 chiffre toujours la reconstruction) | reconstruction | **supprimer** |

Implémentation : `financier_questionnaire.TRI` + `tri_champ()` ; servi par champ (`app.py::_champ`,
clé `tri`). Le front (`FinancierQuestionnaire.tsx`) garde les **garder** visibles, replie les **affiner**
derrière « Affiner les hypothèses (N) » (fermé par défaut), n'affiche **jamais** les **supprimer**. Le
`scenario_saisi` reste dans `CHAMPS` (donc résolu et servi au document, « reconstruction ») mais n'est
plus une question. Prouvé par `test_t2b_tri_des_questions` + `FinancierQuestionnaire.test.tsx::T2b`.

Effet : l'écran « Votre projet » passe de 4 à 3 questions (scénario retiré) dont 1 seule d'usage
repliée ; « Vos coûts » de 6 champs à 1 visible (le coût de construction) + 5 sous « Affiner » ;
« Vos conditions » de 6 à 3 visibles + 3 sous « Affiner ». Le porteur voit d'abord ce qui pilote.

### T2c — verdict franc

**Le Financier, tel qu'il est maintenant, est une esquisse crédible — PAS un document bancable en
l'état.** Ce qu'il fait bien : un bilan à rebours déterministe, reproductible au centime, chaque poste
tracé (sourcé/dérivé/projet), les gardes de vraisemblance (prix de sortie, coût, bailleur < libre),
HT explicite avec le régime, sensibilité double, charge foncière à 3 bornes, et il refuse de se
générer quand l'indispensable manque. Un banquier y lit une intention chiffrée honnête.

**Ce qui manque pour le rendre bancable**, et l'ordre de grandeur du travail :
1. **Le plan de financement** (apport, dette, DSCR, échéancier de décaissement) — aujourd'hui
   explicitement renvoyé à l'établissement prêteur. C'est LE bloc qu'un banquier attend. ~1 module
   dédié (écran + moteur) : estimation **moyenne** (2–3 j).
2. **La valeur locative cadastrale** pour chiffrer la taxe foncière de portage (aujourd'hui « dite,
   jamais chiffrée ») — dépend d'une donnée non ingérée par parcelle : **faible** si on accepte une
   saisie porteur, **élevé** si ingestion (source MAJIC restreinte).
3. **Les coûts réels** (démolition, dépollution, VRD) restent des hypothèses — un vrai document
   bancable cite des **devis**. Hors périmètre LABUSE (le document le dit déjà dans « ce qu'il
   n'établit pas ») : **nul** côté code, c'est une limite assumée.
4. **La TVA réelle** (marge vs récupération vs taux réduit accession) — aujourd'hui un choix de régime
   + renvoi expert-comptable. Passer à un calcul par montage : **moyen** (règles fiscales DOM).

Recommandation : **assumer l'esquisse** — le document s'annonce déjà comme indicatif (« ne remplace ni
un bilan promoteur professionnel, ni une expertise »). Le seul ajout qui changerait sa nature vers le
bancable est le **plan de financement** (point 1). Tant qu'il n'est pas là, garder le bandeau
« Bilan indicatif » en tête, ce qui est le cas.
