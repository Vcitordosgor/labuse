# RAPPORT CRÉDIBILITÉ — mandat du 12/07/2026 (revue externe)

**Branche : `fix/credibilite-scoring`** (depuis main `b49994e`, 4 commits + rapport — **aucun merge**).
Preuves : `audit_shots/credibilite/` (avant/après). Tests : `tests/test_ux_v1.py` (13 dont 3 nouveaux, verts ; 1 skip documenté sur labuse_test vide).

## 1. Enclavement — `cd29629`

**Diagnostic.** Le signal vient de la couche cascade `acces` (phase 1, source BD TOPO) :
bonus **+3** (`acces_direct_voirie`) si un tronçon est à ≤ 25 m ; sinon ligne `PASS`,
**weight NULL — purement informatif**, rangée dans l'onglet Marché. Il ne pèse ni en Q ni
en A. Un mécanisme séparé (audit O1, `declassement.py`) rétrograde en « à creuser » si la
voirie est à > 6 m — entre « pas au contact » et « > 6 m », rien ne se voyait.
**Volumétrie** (run `q_v3_datagap`) : 293 078 parcelles `PASS` **dont 601 chaudes** (plus de
la moitié des chaudes matrice) ; 138 585 `POSITIVE`. **Fiabilité** : BD TOPO est un filaire
d'AXES publics — dessertes privées et servitudes de passage n'y figurent pas (voirie ingérée
sur les 24 communes, 235 643 tronçons ; largeurs réelles seulement sur SD+SP, cf. dette voirie).

**Fix (sans recalcul).** Badge ambre « **Accès à vérifier** » en Synthèse, au niveau des
scores, libellé honnête : signal informatif non pondéré, limites de la source dites, action
concrète (« à lever sur place ou au plan cadastral »). La ligne Marché est inchangée.

**Proposition de pondération — NON appliquée.** Un malus −5 Q ferait basculer **259 des
601 chaudes concernées** sous le seuil Q 65 (36 % de toutes les chaudes de l'île) sur un
signal à fort taux de faux positifs. Recommandation : ne pas pondérer en l'état ; si Vic
veut un jour peser l'enclavement, le faire APRÈS (a) ré-ingestion voirie post-fix A1 sur
les 22 communes restantes et (b) un signal gradué par distance réelle (contact / ≤ 6 m /
> 6 m) plutôt qu'un booléen — l'étage intermédiaire est déjà « à creuser » via O1.

## 2. Prix au m² — `52b58c7`

**Diagnostic : pas un bug, deux métriques légitimes jamais nommées.**
- **699 €/m²** (ligne cascade `dvf`, onglet Marché) = médiane de `valeur ÷ surface TERRAIN`,
  tous types de biens, 10 mutations ≤ 250 m / 5 ans.
- **2 745 €/m²** (Bilan fiche + PDF Flash) = médiane du prix au m² **BÂTI**, type
  « appartement », 25 ventes ≤ 500 m (`dvf_secteur_medianes`). Le PDF Flash nommait déjà
  ses cartouches (« Prix médian bâti » / « Prix médian terrain ») — il était déjà propre.

**Fix.** Nommage partout : à la source pour les futurs runs (`phase2.py` → « médiane
terrain X €/m² (valeur ÷ surface terrain, tous biens) ») ; **re-libellé pur à la lecture**
pour les lignes déjà stockées (`_relabel_dvf_terrain`, testé — les données ne bougent pas) ;
Bilan → « MARCHÉ — PRIX DE SORTIE BÂTI (SECTEUR) », « médiane bâti », calculette → « prix
de sortie bâti ». Les deux chiffres coexistent, nommés.

## 3. Arithmétique des compteurs — `6b671c3`

**Diagnostic** (Saint-Pierre, 167 chaudes) : 131 parcelles portent une personne morale à
SIREN, regroupées en **80 dossiers propriétaires distincts** ; 36 parcelles sont sans
identité publique (personnes physiques — l'open data DGFiP ne couvre que les morales).
131 + 36 = 167 ✓. L'affichage « 80 dossiers (+36 sans identité) » additionnait des
DOSSIERS et des PARCELLES.

**Fix.** `/stats` sert le compteur manquant `chaudes_avec_dossier` ; libellé : « soit
**131 parcelles avec dossier propriétaire (80 propriétaires identifiés) · 36 personnes
physiques — non couvertes par l'open data** ». Test DB structurel :
`avec_dossier + sans_identite == chaude` et `dossiers ≤ parcelles`.

## 4. Fraîcheur des signaux V — `22a1921`

**Diagnostic.** 3 385 / 41 516 signaux V portent une `date_evenement` (BODACC LJ/RJ/cession/
radiation, cessation RNE, DPE) ; les autres sont des signaux d'ÉTAT (âge dirigeant, dormance,
siège hors commune) — sans date d'événement par nature. Le statut des procédures existait
déjà par code (`BODACC_LJ` « en cours » vs `BODACC_LJ_CLOT` « clôturée ») mais noyé dans le
label. La liste ne recevait aucune date.

**Fix (affichage seulement, zéro re-pondération).**
- Panneau « Pourquoi ce score » : pastille d'âge par signal daté (verte < 6 mois · ambre
  6-18 · rouge > 18) + « il y a N mois » ; chips **EN COURS** / **CLÔTURÉE** sur les
  procédures (tooltip : « le signal reste pertinent tant que la parcelle est au nom de la
  société » pour les clôturées).
- Liste : `/parcels` et le GeoJSON commune servent `v_dernier_signal` (max des dates de
  signaux) ; le badge V porte la pastille, tooltip avec la date exacte. Sans signal daté :
  pas de pastille et tooltip « signaux d'état courant » — jamais un âge déduit de
  `computed_at` (toujours récent, donc menteur). Vérifié : 104 pastilles sur la liste île.

## Preuves

| Item | Avant | Après |
|---|---|---|
| 1 | `avant_1_synthese_sans_avertissement.png` · `avant_1_ligne_marche.png` | `apres_1_synthese_avertissement.png` |
| 2 | `avant_2_bilan_mediane.png` | `apres_2_ligne_marche_terrain.png` · `apres_2_bilan_mediane_bati.png` |
| 3 | `avant_3_compteur_dossiers.png` | `apres_3_compteur_dossiers.png` |
| 4 | `avant_4_signaux_sans_age.png` | `apres_4_signaux_ages_statut.png` · `apres_4_badges_liste_age.png` |

Confirmations : aucun poids ni seuil modifié (les scores sont identiques au run de
référence) ; le seul endpoint étendu est `/stats` + `/parcels`/GeoJSON (champs ajoutés,
rien de retiré) ; DA intacte ; jamais de merge.
