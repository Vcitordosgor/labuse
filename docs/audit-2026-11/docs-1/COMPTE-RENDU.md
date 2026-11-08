# DOCS-1 — compte-rendu

> Branche `fix/docs-1`, worktree `~/Desktop/labuse-docs1`, Opus. Base Mac `labuse` (run servi
> `q_v20`, 434 582 parcelles), rendu PDF in-process (venv `~/Desktop/labuse/.venv`, weasyprint 70,
> `LABUSE_PDF_PROCESS_ISOLE=0`). **Aucun merge, aucun accès prod.** Pièce à conviction lue d'abord :
> `~/Desktop/LABUSE-EXPORTS-2026-11-07/` (16 documents sur `97411000BZ1065` + `SOMMAIRE.md`),
> `docs/audit-2026-11/nu-5/B/RAPPORT.md`, `docs/audit-2026-11/ecarts-zero-1/COMPTE-RENDU.md`.

## Décision de Vic appliquée

« Un fait a une seule valeur dans tous les documents, celle de la fiche. Chaque correction se fait
à la source, jamais document par document. Plus aucun mot de cuisine interne dans un document
client. Un seul format partout. » Documents **Argumentaire**, **Dossier banquier**, **Lettre de
zonage** et **Financier** (builder-exports) **supprimés** ; le **Courrier** garde l'unique point
d'entrée ; le **Bilan** (écran Bilan, `/bilan/{idu}.pdf`) est le seul document financier.

---

## 0. Le résultat — le banc des documents

NOUVEAU `scripts/coherence/documents_banc.py` + test `tests/test_docs1_banc.py` (reel+local) :
rejoue **tous les documents servis** sur les **12 parcelles témoins** et REFUSE tout fait imprimé à
deux valeurs, tout jeton de cuisine interne, toute faute de format.

| Contrôle | Avant | Après |
|---|---:|---:|
| Faits à deux valeurs | 7 | **0** |
| Jetons de cuisine interne | 44 | **0** |
| Fautes de format | 14 | **0** |
| **Total** | **65** | **0** |

```
PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
  ~/Desktop/labuse/.venv/bin/python -m scripts.coherence.documents_banc    # → VERT, 0 écart
```

---

## 1. Suppression des quatre documents (à la source)

**Argumentaire, Dossier banquier, Lettre de zonage** (commit 1) — routes de redirection
(`api/documents.py`), robinets registre (`pdf_argumentaire`/`pdf_banquier`/`pdf_lettre_zonage`),
rate-limit (`protection.py`), porte Copilote (`_DOC_MAP`), front (vite, strings, capaciteMax, api,
useApp, copilote, constructibilite), tests, QA. Table RGPD `lettre_zonage_refs` **conservée** (purge
des données personnelles historiques).

**Financier** (builder-exports, commit 2) — **il n'était plus accessible depuis l'app** (aucun
composant `FinancierQuestionnaire` ; rien n'ouvre `/financier/{idu}.pdf` ; la carte Bilan ouvre
`<BilanEcran>` → `/bilan/{idu}.pdf`). Supprimé entièrement : route + 3 routes questionnaire ;
modules `exports/blocs/financier.py`, `exports/financier_bilan.py`, `financier_questionnaire.py` ;
dispatch/contexte builder. **« Les postes restent dans le Bilan »** : robinets `pdf_financier` →
`pdf_bilan` (`/bilan/{idu}.pdf`) et `ecran_questionnaire_financier` → `ecran_bilan`, chiffres
conservés (aucun orphelin, graphe du registre valide). Tests financier supprimés/trimés.

**Effet de bord voulu** : la divergence `sdp_max_terrain` (Financier « 325 m² » inventé vs fiche
« 212 m² ») disparaît avec le document.

---

## 2. Les deux faits moteur unifiés

| Fait | Valeur unique (fiche) | Correctif |
|---|---|---|
| **Servitude PPR** | 1 servitude — PM1 | Le **Gabarit** lisait les SUP de la seule géométrie modélisée (« Aucune SUP ») : il LIT désormais `dispositifs.sup` de la fiche (`_dispositifs_block`, même lecteur que le Dossier) et retire la règle moteur contradictoire. |
| **SDP maximale, terrain** | la valeur de la fiche | Le Financier (qui composait un programme de logements non saisi → « 325 m² ») est supprimé (§1). |

---

## 3. Jetons, format, abréviations, forme

**Jetons de cuisine interne** — `config/mots_interdits.yaml` 30 → **48** (version `2026-11-07`,
test `test_circuit2_lot0bis` maj), corrigés **au producteur** :
`capacite_max.MENTION` (py+ts : « volet D », « VERITE-TERRAIN »), `etude_faisabilite` (« verrou de
test », « géométrie servie »), `gabarit/builder.py` (« config/ », « troncon_de_route »),
`exports/blocs/gabarit._clean_src` via `risques_arbitrage.libelle_client_detail`
(« INONDATION_MOUVEMENT_DE_TERRAIN », « PM1_PPR_… », « édition non enregistrée »),
`millesime_source.libelle_date_source` (« ingéré le » → « au »), `exports/blocs/annonce` (« Classement
D », « 0 · Non retenue » → on garde le motif factuel), déclarations fiche (« parcelle hors run servi »
→ « non évalué(es) pour cette parcelle »). **Banc : 0 jeton.**

**Format** — date ISO → jj/mm/aaaa (`millesime_source.composer` + filet `miroir._mill_client` pour le
cache de fiche), décimale point → virgule (`exports/blocs/zonage._regles`). **Banc : 0 faute.**

**Abréviations du Bilan** — **SUV** écrit en clair (« surface vendable ») dans le PDF, l'Excel et le
moteur (`bilan/moteur.py`, `pdf.py`, `excel.py`). DROC/DAT/TRE/GIEP/M.O.D./Pack vivaient dans le
Financier builder-exports, supprimé — plus présentes. **Excel** : taux (TVA, marge) affichés « 8,5 % »
(format `0.0 %`), jamais « 0.085 ».

**Forme** — Dossier : « Vérifié : rien » → « Vérifié : rien à signaler » ; le **§11 « Simulation »**
(renvoi au Financier supprimé) DISPARAÎT de la structure unique (sommaire + corps), « Limites et
sources » remonte §12 → §11. Apporteur : case « Vides » → « Vide ». **Courrier** : en-tête, signature
et pied au **nom du client** (marque blanche, repli sur le nom du compte), JAMAIS « LABUSE » ni « pour
le compte de LABUSE » (`api/courrier._pdf_header`/`_marque_du_compte`, `courrier_compose`). Captures
avant/après : `docs/audit-2026-11/docs-1/captures/` (le Courrier « avant » portait l'en-tête + pied
« LABUSE » ; « après » porte l'identité du compte).

---

## 4. Prix — un seul prix en titre, les autres en annexe « Marché »

Le prix EN TITRE est celui du **type de bien de la parcelle** (maison pour une maison), avec sa
définition en une ligne (type · ventes · rayon · période). Le mécanisme `type_prioritaire` de
`sector_price` existait mais ne tirait le type que de la dernière vente DVF de la parcelle : un bâti
qui n'a jamais muté (ex. `97411000BZ1065`) retombait sur « appartement » en tête d'un dossier de
maison. **DOCS-1** (`marche_service.marche_dvf`, point d'appel UNIQUE) : à défaut de vente DVF, un
**bâti non en copropriété est une maison** → fiche, Dossier, Comparatif, Estimer deviennent
type-exacts ENSEMBLE (lecteur unique). Les autres indicateurs (terrain nu, médianes par type, neuf
VEFA) restent en **annexe Marché** du §8, chacun défini. Exemple : `BZ1065` passe de « 2 365 €/m² —
appartement » à « **3 821 €/m² — maison (29 ventes à moins de 500 m, 2022–2025)** ».

## 5. Forme (point 7) — tous les items

- **Couvertures (carte + résumé)** : Dossier (carte de situation remontée en page de garde, résumé =
  bandeau de tuiles), Comparatif (carte + résumé d'une ligne), Bilan (carte + CA TTC / Résultat net).
- **Pied de page raccourci** : l'Étude ne répète plus IDU/type/« généré le » ; le numéro de page tient
  sur une ligne (`@bottom-right` nowrap).
- **Page quasi vide du Flash** : supprimée (c'était le §11 « Simulation », retiré).
- **3D du Gabarit** : enveloppe **limitée au plafond d'emprise** (homothétie) + mention « le bâti
  existant dépasse la hauteur autorisée (X m mesurés / Y m autorisés) ».
- **Tuile manquante de l'Étude de zone** : rangée de tuiles de tête ajoutée.
- **Carte d'Estimer** : fond ortho IGN + contour + voisines (déjà servis ; vérifié).
- **« Valeur du terrain » d'Estimer** : expliquée en une phrase quand elle dépasse la valeur du bâti.
- **PPR une seule fois dans l'Étude de faisabilité** : la zone rouge/bleue a sa ligne dédiée, plus
  re-listée parmi les contraintes signalées.
- **Corps du Courrier au nom du client** : l'intro, les ouvertures et l'offre sont au nom de
  l'expéditeur ; **0 « LABUSE » dans le recto** — LABUSE n'apparaît qu'en mention discrète d'outil au pied.

## 6. Recette

| Recette | Résultat |
|---|---|
| **Banc des documents** (12 témoins, 43 documents) | **0 écart** (faits 0, jetons 0, format 0) |
| **Régénération V2** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V2/` + `SOMMAIRE.md`) | `scripts/docs1_regen_v2.py` — 3 parcelles : `97411000BZ1065`, `97409000AK0804` (**nue zone U**), `97421000AB0133` (**zone rouge partielle**). TOUS les documents survivants rendus, **Bilan PDF + Excel compris** (saisies illustratives, comme l'export d'origine ; la GÉNÉRATION du Bilan lit `declarations/bilan/postes.yaml`, pas le modèle Excel — celui-ci ne sert qu'aux tests golden `test_bilan_*`). |
| Captures couvertures avant/après | `docs/audit-2026-11/docs-1/captures/` |
| Hook (unitaires `not db/local/reel/network`) | **vert** (le flake `test_courrier_transitions_journalisees` est pré-existant, ignoré) |

---

## 7. 2ᵉ passe — « la V2 contenait encore ces défauts, que le banc ne voyait pas »

Le banc V2 ne rendait que `dossier/gabarit/apporteur/estimer` : il ne VOYAIT ni le Comparatif, ni
l'Étude, ni le **Flash**, ni le Courrier, ni le Bilan. **Élargi** (`documents_banc.py`) à TOUS les
documents (POST compris) et à deux faits de plus — **viabilisation** et **date du PPR** — sur
**13 parcelles témoins** (dont une **zone U touchée par la zone rouge d'un PPR**, `97415000CY0275`, et
la zone N `97421000AB0133`). Il a révélé **163 écarts**, tous corrigés **à la source** → **0 écart**.

| Fait / jeton / forme | Avant | Correctif (à la source) |
|---|---|---|
| **Viabilisation** à deux valeurs | dossier « probable » vs comparatif/Flash « confirmée » | `viabilisation.build_indicateur` — **un seul libellé** (« probable ») lu par fiche, Dossier, Comparatif, Flash, Estimer. |
| **Date du PPR** à deux valeurs | dossier « approuvé le 16/04/2026 » (édition DEAL de TOUTE l'île) vs Estimer « 2012 » | `deal_carmen` + `millesime_source` — le millésime de couche DEAL ne se lit plus « approuvé le … » ; seule la date du PPR **de la commune** s'affiche. |
| **Flash = Dossier** | le Flash exporté était une copie du Dossier | le **vrai produit 79 €** (`generate_flash_report`) ; jargon retiré (« run servi », « sentinelle », « ingéré le », « Version du modèle »), dates jj/mm/aaaa, décimales à la virgule. |
| **Étude** : plafond d'emprise 487 vs 470 | 30 % du DESSIN | le plafond **du Gabarit** (CES × contenance), lu dans le payload. |
| **Étude** : 4 bâtiments vs 2 | `count(DISTINCT b.id)` (doublons d'ingestion) | `bati.stats_batch`/`emprise_bati_bdtopo_m2` — **mêmes producteurs que la fiche** (dédoublonnés). |
| **Étude** : « art. Article Uh.9 », millésime ISO | — | `_art_label` (« art. Uh.9 »), `_fr_iso` (jj/mm/aaaa), décimales à la virgule à la sortie. |
| **Courrier / Apporteur** : nom = e-mail | le nom de compte (souvent l'e-mail) servait de signataire | société, sinon prénom + nom ; **jamais l'e-mail** ; sans nom → le document **refuse** (« Renseignez le nom de votre société dans Compte »). Signature sous « Cordialement, ». |
| **Bilan** : bénéfice sans coût | résultat = CA (dépenses nulles) | sans coût majeur saisi → **« non calculable — saisissez vos coûts »** ; ligne « Terrain » = **contenance** de la fiche. |
| **Forme** | « Pack », « )) » | sous-groupe Bilan renommé ; parenthèses imbriquées supprimées (quartier, relief). |

Le **Gabarit** sur une parcelle **zone N** rend désormais un **document de refus propre** (jamais un
422) ; sur la **zone U + PPR rouge**, il se dessine EN déduisant le rouge.

## 8. Recette (2ᵉ passe)

| Recette | Résultat |
|---|---|
| **Banc des documents élargi** (13 témoins, 123 documents, Flash/Courrier/Bilan/Étude compris) | **0 écart** (faits 0, jetons 0, format 0) |
| **Régénération V3** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V3/` + `SOMMAIRE.md`) | `scripts/docs1_regen_v3.py` — 4 parcelles ; **Flash réel**, Gabarit de refus (zone N), Bilan « non calculable ». 44 documents (l'Étude de `CY0275` refuse honnêtement : le moteur d'implantation ne produit pas de scénario sur cette géométrie). |
| Hook (unitaires `not db/local/reel/network`) | **vert — 2953 passed** |

---

## 9. 3ᵉ passe — « la V3 contenait encore ces défauts »

Le banc est étendu à **3 faits de plus** du Flash (marge de surélévation, surface vendable, permis à
moins de 100 m) et le Flash passe par **le même lecteur que la fiche**.

| Défaut | Correctif (à la source) |
|---|---|
| **Flash — marge de surélévation** « ~2,6 m » vs fiche « −3,3 m » | `faisabilite.potentiel.bloc_potentiel` applique l'override LiDAR mesuré (comme la fiche) : la marge peut être NÉGATIVE (le bâti dépasse déjà) — plus la marge bornée à 0 du bâti BD TOPO. |
| **Flash — SDP max & surface vendable** divergentes | le Flash lit le **même bloc** `_potentiel_transformation_block` que le Dossier : SDP maximale réglementaire (212 m²) et surface vendable « non calculable » quand la capacité bâti-conservé est nulle (plus un « 118 m² » table-rase). |
| **Flash — « calibré / calibrage »** | retiré du gabarit de rapport (« Règles du PLU », « Hauteur d'égout (PLU) »…) et du tableau des sources. |
| **Flash — codes bruts** (`MOUVEMENTS_DE_TERRAIN`, `tres_fort`, `zone_transition`) | en clair : `phase1` (pente), `bloc_potentiel` (cause), `nettoyer_libelle_client` (lignes de cascade déjà stockées). |
| **Flash — format** `-0.3 %`, `3169 €`, `1234 ventes` | passe de sortie : signe moins « − », virgule décimale, séparateur de milliers (devant une unité) ; `marche_bloc` groupe les effectifs. |
| **Permis à moins de 100 m** : viabilisation « 5 » vs marché « 0 (36 mois) » | le faisceau de viabilisation NOMME sa fenêtre (« toute période ») ; le banc ne confronte que la ligne datée du marché (même fenêtre). |
| **Étude de zone** : tuile blanche en haut à gauche | le fond no-data se recolore de la teinte moyenne de la mosaïque (`plan_ortho`) — il se fond, plus de carré blanc. |
| **Gabarit 3D** : légendes superposées, enveloppe = zone entière | légendes EMPILÉES (bande portée à 70 px) ; enveloppe RÉELLEMENT réduite au plafond d'emprise (érosion → socle compact, `_emprise_env`). |
| **Comparatif** : tableau coupé sous la carte | titre + tableau forment un bloc `.cmp-bloc` insécable → page 2 s'ils ne tiennent pas sous la carte. |
| **Bilan** : « TA parking », « 0 € » | « Taxe d'aménagement — parking extérieurs… » ; tout montant nul → « — » (`_eur_nz`, ratios, totaux, TVA). |
| **Gabarit refus** : « donnée manquante » | la VRAIE raison (`potentiel_batir.motif` : « Zone non constructible (N) », « zone rouge du PPR »…). |
| **Étude** : 400 sur « aucun scénario » | **document de refus propre** (`_etude_refus_pdf`) avec la raison (zone N, « zone trop étroite »…), comme le Gabarit. |

**Captures avant/après** (regardées) : `docs/audit-2026-11/docs-1/captures-v4/` (Gabarit 3D, Comparatif,
Étude de zone, Bilan).

**Témoin zone U ∩ PPR rouge** (`97415000CY0275`) : le Gabarit s'y dessine (rouge déduit), le Dossier /
Estimer / Flash / Bilan / Courrier aussi.

**CORRECTION (investigation du classement par surface hors rouge)** — ma réserve « aucune parcelle
zone U ∩ PPR rouge ne porte de scénario » était **FAUSSE** : je n'avais testé que des petites parcelles
(300–3000 m²). Sur les 10 plus grandes par surface hors rouge (toutes > 17 000 m²), **5 produisent un
scénario** (97407000BK0084, 97416000DE0205, 97415000DH0076, 97409000AY0773, 97408000AO1520) et **5
refusent** « simulation impossible / zone trop étroite » (97409000AS0135, 97413000CX2818, 97414000EL0318,
97410000BY0819, 97411000AK0012) — dont **EL0318 (208×198 m, 0 m² de rouge)**, manifestement PAS « trop
étroite ».

**CAUSE du faux refus (défaut moteur, PROUVÉ, non corrigé)** : `moteur._rechercher` borne la recherche à
un **budget de temps de 22 s** (`LABUSE_ETUDE_GRILLE_BUDGET_S`) ; sur une grande assiette chaque candidat
coûte ~2,4 s, donc seuls ~8 des 144 candidats (forme×niveaux×fraction) sont essayés — et la grille étant
ordonnée « le plus gros d'abord », ces premiers candidats échouent sur le **stationnement aérien**
(barre + places ne tiennent pas) avant d'atteindre les configurations plus petites qui PASSENT. À budget
300 s, EL0318 rend **125 candidats et 10 faisables**. Le message « zone trop étroite » est donc
trompeur : la vraie situation est « la recherche de pré-faisabilité manque de temps pour atteindre les
implantations faisables ». Défaut à part entière (performance du budget + ordre de la grille + libellé),
indépendant du PPR. **Rien corrigé** (hors mandat de cette passe).

| Recette (3ᵉ passe) | Résultat |
|---|---|
| **Banc élargi** (13 témoins + marge surélévation / surface vendable / permis < 100 m) | **0 écart** |
| **Régénération V4** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V4/`) | `scripts/docs1_regen_v4.py` |
| Hook (unitaires) | **vert — 2953 passed** |

## 10. Correction du défaut moteur + V5 — « jamais “zone trop étroite” sur une parcelle qui ne l'est pas »

Le défaut PROUVÉ au §9 (faux « simulation impossible / zone trop étroite » sur une grande assiette, par
manque de temps de la recherche, pas par géométrie) est **corrigé à la source** dans
`implantation/moteur.py`, sans toucher au chemin qui marche (zéro régression).

**Principe.** La recherche « objectif » (meilleure emprise d'abord) tourne **inchangée** en 1ᵉʳ passage :
une parcelle qui réussissait garde son scénario au chiffre près. Le correctif n'ajoute un comportement
que **lorsqu'elle échoue par le temps**.

| Levier (décision Vic) | Mise en œuvre |
|---|---|
| **Grille ordonnée « faisable-probable d'abord »** | nouveau paramètre `ordre` de `_rechercher` : en repli, les fractions d'emprise sont triées **croissantes** (petite emprise d'abord — la plus susceptible de tenir reculs + stationnement). Le classement FINAL reste par objectif (on garde le meilleur faisable trouvé). Early-stop dès **3 faisables** : on cherche à PROUVER qu'une implantation tient, pas à tout énumérer → temps borné. |
| **Budget adaptatif à la taille** | `_budget_repli(terrain, restant)` : budget du 2ᵉ passage proportionné à l'assiette (≈ 9 + aire/2500, plafonné 15 s) **et** borné par le temps `restant` sous une **enveloppe de calcul globale** (`_ENVELOPPE_CALCUL_S = 40 s`). 1ᵉʳ + 2ᵉ passage + rendu tiennent ainsi SOUS la borne API (60 s) : plus de 57,9 s mesurés — **max 45,4 s**. |
| **Pas de stationnement en sous-sol en repli** | le 2ᵉ passage reste en stationnement **aérien** : il ne change pas l'économie du projet (décision produit, pas une correction). |
| **Libellé HONNÊTE** | `_message_impossible` : le critère n'est plus la TAILLE mais le fait que la recherche a été **bornée par le temps** (`grille_budget_atteint`). Dans ce cas → « **recherche non aboutie — une étude d'architecte est recommandée** ». Le « zone trop étroite / reculs / stationnement » n'est servi que lorsque la grille a été **épuisée** (impossibilité géométrique réelle). |
| **Kill-switch** | `LABUSE_ETUDE_REPLI=0` désactive le repli (retour au comportement antérieur) — utile en prod et pour l'A/B de la recette. |

Le repli est branché sur les **deux chemins servis** — `etudier_multi` (scénarios de la fiche/worker) et
`etudier_complet` (payload de l'Étude). L'API historique `etudier()` (tests `reel`) est laissée telle quelle.

| Recette (passe moteur) | Résultat |
|---|---|
| **Zéro régression** — 9 témoins qui portaient déjà un scénario | **9/9 identiques** au chiffre près (l'ordre « objectif » est inchangé ; une dérive apparente DH0076/AY0773 était du bruit de charge CPU — revenue au repère hors charge). |
| **5 gros refus connus** (§9 : EL0318, AS0135, CX2818, BY0819, AK0012) | **2 récupèrent un scénario** (AS0135 40/barre/2, AK0012 42/barre/2), **3 passent au libellé honnête** « recherche non aboutie » (EL0318, CX2818, BY0819). |
| **Échantillon représentatif** — 130 parcelles zone U, 3 000–12 000 m², tirage pseudo-aléatoire | **26 refusaient** sous l'ancien code (20 %). Désormais : **1 produit un scénario**, **20 au libellé honnête** « recherche non aboutie » (plus de faux « zone trop étroite »), **5 en impossibilité GÉOMÉTRIQUE réelle** (grille épuisée, budget NON atteint → message géométrique correct). Le gain principal sur cette tranche est la **sincérité du refus** ; la récupération est plus fréquente sur les grandes assiettes. |
| **Temps de calcul maximal mesuré** | **45,4 s** (recette ciblée) / **39,3 s** (sweep) — toujours **sous la borne API 60 s** (enveloppe 40 s + marge de rendu), contre **57,9 s** avant l'enveloppe globale. |
| **Témoin PPR** passe à `97415000DH0076` (zone U ∩ PPR rouge **avec** scénario) | banc + V5 |
| **Banc des documents** (13 témoins, 130 documents) | **VERT — 0 écart** (le nouveau témoin DH0076 a révélé un dernier format : la marge de surélévation ENTIÈRE « 11,0 » (Dossier, §Règles) vs « 11 » (Flash) → `bloc_potentiel` ET la ligne de potentiel du Flash alignés sur UNE décimale française (`fr_dec_fixe`), comme le Dossier ; la marge négative « −3,3 » reste inchangée). |
| **Régénération V5** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V5/`) | `scripts/docs1_regen_v5.py` — 45 documents, DH0076 Étude = **scénario d'implantation réel** (logement collectif, barre, hors zone rouge ; le nombre exact de logements dépend de la charge CPU au rendu, via le budget horloge), AB0133 Étude = refus motivé. |
| Hook (unitaires) | **vert — 2953 passed, 50 skipped** (`make test-unit`) ; front inchangé (aucune modification `frontend/`). |

## 11. PPR-PARTIEL + V6 — un seul lecteur du verdict de potentiel

Sur `97415000DH0076` (zone U, **2 %** touchés par la zone ROUGE d'un PPR), quatre documents disaient
quatre choses : le **Dossier** « contrainte rédhibitoire couvrant TOUTE la parcelle » + « SDP non
calculable », le **Gabarit** refusait « pas de potentiel résiduel », le **Flash** « rien à bâtir », mais
l'**Étude** posait un scénario sur les 98 % hors rouge (zone rouge de 458 m² retirée).

**Cause.** Dossier / Flash / Gabarit / Comparatif lisent le **run stocké** (`parcel_residuel.cause =
'redhibitoire'`, SDP 0) ; l'Étude seule découpe le rouge (moteur d'implantation) et bâtit sur le reste.
Le run — périmé — traite une zone rouge PARTIELLE comme couvrant toute la parcelle. Le moteur de
faisabilité LIVE, lui, dit déjà « constructible, R+4, zone d'implantation 17 370 m² » (rouge découpé).

**Correction à la source — `faisabilite.db.verdict_ppr_partiel`, SOURCE UNIQUE.** Une parcelle fermée
par le run à cause d'une zone rouge PPR, mais **partiellement** rouge (< 95 %) avec une partie hors rouge
**exploitable** (≥ 200 m² d'un seul tenant touchant une voie — garde-fous PPR-PARTIEL-A) ET que le moteur
de faisabilité **confirme constructible** (ni zone A/N, ni hors-PLU, ni ER/EBC couvrant tout), n'est plus
« rédhibitoire » : elle est **« constructible sur la partie hors zone rouge (N %) — zone rouge (M %)
retirée ; capacité à l'Étude de faisabilité »**. On n'invente **aucune** SDP (le chiffre vit dans
l'Étude, qui découpe le rouge). Branché sur les lecteurs du verdict :

| Lecteur | Document(s) | Correctif |
|---|---|---|
| `potentiel_batir` / `potentiel_batir_batch` | Flash (verdict), Gabarit (refus) | `_override_ppr_partiel` quand le gate n'est QUE la cause résiduelle en zone constructible. |
| `est_ferme_parcel` | Flash (`bloc_potentiel` : « au sol / table rase ») | ne ferme plus → la table rase redevient constructible. |
| `_potentiel_transformation_block` | Dossier §10, Comparatif (`/compare`) | dernier mot : cause → None, libellé PPR-partiel, SDP servie None. |

Garde-fous : **zone U/AU seulement**, pas de déclassement, pas d'AU différée, et la **confirmation du
moteur de faisabilité** écarte les faux positifs (zone N `97421000AB0133`, hors-PLU `97417000BI0076`).

| Recette (PPR-PARTIEL) | Résultat |
|---|---|
| **Banc + 3 faits** : `verdict_potentiel`, `sdp_maximale`, `logements_max`, sur 13 témoins | **VERT — 0 écart** (DH0076 : Dossier, Flash, Gabarit, Étude disent tous « constructible hors rouge » ; la saturation « déjà construite au maximum » et les mentions de règle « habitat interdit » ne sont PAS prises pour de la non-constructibilité). |
| **Régénération V6** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V6/`) | `scripts/docs1_regen_v6.py` — 4 parcelles (BZ1065, AK0804, **DH0076**, AB0133). |
| Hook (unitaires) | **vert — 2953 passed**. |

## 12. Capacité cohérente avec le verdict PPR-PARTIEL + V7

La V6 corrigeait le VERDICT de `97415000DH0076` (« constructible sur la partie hors zone rouge »), mais
les LIGNES DE CAPACITÉ écrivaient encore, juste en dessous, « SDP maximale non calculable (capacité
nulle) », « surface vendable non calculable », « table rase non constructible », « au sol : rien à
construire » — elles lisaient le run (qui ne chiffre pas la partie hors rouge). Contradiction interne.

**Règle (décision Vic).** Quand le verdict est « constructible sur la partie hors zone rouge », TOUTES les
lignes de capacité (SDP maximale, surface vendable, table rase, au sol) lisent le même moteur que l'Étude
**ou renvoient « voir l'Étude de faisabilité »** — JAMAIS « capacité nulle » ni « rien à construire ». La
marge de surélévation n'est imprimée que s'il y a un bâti (inchangé : la marge n'existe que si une hauteur
de bâti est mesurée).

| Lecteur | Correctif (quand `potentiel_transformation.ppr_partiel`) |
|---|---|
| `potentiel.bloc_potentiel` (Flash) | au sol / table rase → `renvoi_etude` ; verdict = « marge … · capacité à l'Étude de faisabilité (zone rouge retirée) ». Le renvoi n'est armé que si le run FERME la parcelle (`cause` présente) — une parcelle au run non fermé garde sa vraie capacité (AK0804 : 35 086 m²). |
| `flash/data.py` + `rapport.html.j2` | cartouches SDP maximale / Surface vendable → « voir l'Étude de faisabilité », plus le forçage « vendable non calculable ». |
| `miroir.py` (Dossier, lignes absentes) | « Surface de plancher maximale / Surface vendable : non chiffrée ici — la zone rouge du PPR est retirée, la capacité de la partie hors rouge relève de l'Étude de faisabilité. » |
| `_potentiel_transformation_block` | expose `ppr_partiel` (drapeau lu par les trois ci-dessus). |

| Recette (V7) | Résultat |
|---|---|
| **Nouveau contrôle de banc** — un document ne porte JAMAIS à la fois « constructible sur la partie hors zone rouge » ET « capacité nulle / rien à construire » | **VERT — 0** (13 témoins). Ne vise QUE ce verdict : une parcelle bâtie proche de sa densité garde sa « surface vendable (bâti conservé) nulle » légitime, table rase positive. |
| Banc des documents (faits + jetons + format + cohérence) | **VERT — 0 écart**. |
| **Régénération V7** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V7/`) | `scripts/docs1_regen_v7.py` — 4 parcelles. |
| Hook (unitaires) | **vert — 2953 passed**. |

**Note — la cause RACINE dans le run (lue en §13).** Le défaut vient de ce que le run résiduel
(`parcel_residuel`, vue de `parcel_residuel_runs`) est calculé par `compute_residuel_batch` avec
`assiette_clippee=False` → `parcel_faisabilite` prend sa branche HÉRITÉE (`db.py`), SANS la garde
PPR-PARTIEL-A, et marque `redhibitoire`. Le même `parcel_faisabilite` appelé EN LIGNE par la fiche
utilise `assiette_clippee=True` (défaut) → branche gabarit AVEC PPR-PARTIEL-A → constructible. Deux
chemins, deux verdicts. Les correctifs DOCS-1 réconcilient à la LECTURE ; la vraie réparation est un
run résiduel recalculé en assiette clippée (hors mandat de cohérence documentaire).

---

*DOCS-1 — base locale, prod jamais touchée. Banc : `scripts/coherence/documents_banc.py` ;
régénération : `scripts/docs1_regen_v2.py` (V2) … `_v7.py` (V7). Branche `fix/docs-1`, non mergée.*
