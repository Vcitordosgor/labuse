# MANDAT EXPORTS-2 — construire les cinq documents

**Objet** : remplacer les exports actuels par **cinq documents — Dossier · Résumé · Financier · Apporteur · Pré-dossier PC** servis par un seul builder, dont chaque chiffre est lu par son id du registre. Les maquettes du 05/09 (`docs/audit-2026-09/EXPORTS/maquettes/`) sont la forme ; la relecture du 07/09 (`RELECTURE-DOCUMENTS.md`) ajoute les blocs et corrige le Financier.

**Branche** : `feat/exports-2`, depuis `main`.
**Préalable bloquant** : `feat/circuit-1` mergée sur `main`. Sans le registre, ce mandat n'a pas de sol. Si ce n'est pas le cas à l'étape 0 : arrêt, signalement.

**Règles** : étape 0 stricte (pwd, branche, arbre propre) · aucun sous-agent sur git · un commit par lot, jamais avant la recette du lot · chaque chiffre imprimé porte un id du registre — un chiffre sans id n'est pas imprimé · aucune valeur par défaut silencieuse : un champ non renseigné s'imprime « non chiffré » · les gabarits sont ceux des maquettes, pas une réinterprétation · DA v3 : mint = structure et sourcé, ambre = saisi par le client, aucun mauve.

**Décisions déjà prises** (ne pas rouvrir) : architecture à cinq documents (04/09) · les 12 arbitrages (`ARBITRAGES-EXPORTS.md`) · la liste des sources par document (`EXPORTS-SOURCES.md`) · surélévation à l'égout · CERFA selon le scénario · aucun palier LABUSE dans aucun document · pas de version en ligne ni d'anonymat pour l'Apporteur.

**Trois décisions validées par Vic le 07/09** :
1. **TVA** : le bilan travaille **HT**. Le prix de sortie DVF (TTC) est converti par le taux du régime saisi (8,5 % par défaut à La Réunion). Le régime est un champ obligatoire du questionnaire ; chaque ligne du bilan porte HT ou TTC ; le document renvoie à l'expert-comptable pour le régime réel.
2. **Questionnaire** : quatre écrans, une vingtaine de champs (§ lot 4).
3. **PDF Projet** (chaîne FPDF `api/pdf_projet.py`) : supprimé (décision Vic 07/09) — le Financier le remplace, sa route redirige vers le Financier, la chaîne disparaît au lot 8.
4. **Lettre de vérification de zonage** (`/lettre-zonage`) : **supprimée** (décision Vic 07/09). Ni Vic ni Fable ne l'ont jamais ouverte, aucun client ne l'a demandée, et la section 2 du Dossier couvre le zonage entièrement. Route et chaîne supprimées au lot 8 ; pas de redirection, pas d'extrait.

---

## Lot 0 — Le registre avant les documents

Coordonné avec CIRCUIT-2 lot 6 : si la session CIRCUIT a déjà fait une partie, la reprendre, ne pas la doubler. Lire `docs/CIRCUIT/` et `src/labuse/registre/` avant d'écrire une ligne.

| # | Travail |
|---|---|
| 0.1 | Déclarer les moteurs manquants dans `moteurs.csv` et le registre : `potentiel` (`faisabilite/potentiel.py`), `zone_servie` (`faisabilite/zone_servie.py`). Renommer `marche_communes` en un nom qui dit ce qu'il est devenu : le point d'appel unique de tout prix (`marche_service.py`). |
| 0.2 | Mettre à jour les `fonction` périmées par EXPORTS-1 : `prix_ancien_median_eur_m2`, `prix_sortie_bati_eur_m2` (plus `calcul=front`), `sdp_residuelle_m2`, `capacite_logements`, `classe_residuel`, `type_proprietaire`, `zone_plu_famille`, les cinq ids de permis (fenêtre dans le libellé, ou fusion). |
| 0.3 | **Portée `projet`** ajoutée à `Chiffre` (à côté de `run` et `live`) : un chiffre saisi par le client, sans réservoir, tamponné par l'id du projet et la date de saisie. |
| 0.4 | **Ids à créer** (libellé, unité, définition, moteur, réservoirs) : emprise bâtie, hauteur du bâti, nombre de bâtiments, marge de surélévation, surface de plancher, surface vendable, chiffre d'affaires HT, coût de construction, honoraires techniques, VRD, stationnement, démolition, aléas, frais d'acquisition, redevance d'archéologie, marge et frais, charge foncière (trois bornes), sensibilité coût, sensibilité prix de sortie, écart au prix demandé, seuil de rentabilité, prix de revient au m², prix d'achat historique de la parcelle (D-a), permis déposés sur la parcelle (D-b, si rattachable), ventes retenues / écartées du nuage, part des logements raccordés (EGOUL), mixité (seuil, quota, déclenchement), ER, EBC, DPU, PEB, zonage A/B/C. |
| 0.5 | **Garde de couverture** comme règle du registre : tout chiffre `nombre` porte `couverture` ou `non_couvert`. Test `test_registre` étendu. |
| 0.6 | `labuse registre sync` ; `verifier()` vide. |

**Recette** : `verifier()` sans problème ; la sonde passe ; aucun id orphelin.

---

## Lot 1 — Un builder, un catalogue de blocs

| # | Travail |
|---|---|
| 1.1 | `src/labuse/exports/` : un module par bloc du catalogue (`EXPORTS-SOURCES.md`), chaque bloc = une fonction qui lit **des ids** (`Valeur` du registre) et rend un fragment HTML. Aucun calcul dans un bloc, aucune requête SQL dans un bloc. |
| 1.2 | Un seul rendu : WeasyPrint 69, `maquette.css` versionné comme `exports/theme.css`, `@page` avec cartouche (nom du document, IDU, adresse, n° de rapport, « données LABUSE au », version du modèle, page x/y). |
| 1.3 | Chips de nature à chaque ligne : sourcé / estimé / dérivé / projet, dérivées de la portée et du `calcul` de l'id — pas écrites à la main dans le gabarit. |
| 1.4 | Le « verdict » de section : une fonction par section, déterministe, phrases à trous remplies par les ids. Aucun appel IA. |
| 1.5 | Pieds de section générés depuis les réservoirs des ids effectivement lus (le mécanisme d'EXPORTS-1 lot 6.1, généralisé). |
| 1.6 | Numéro de rapport unique par document (`DP-`, `RE-`, `FI-`, `AP-`, `PC-` + date + IDU) et **archivage JSON des `Valeur` lues** à côté de tout PDF vendu ou envoyé (Flash, Apporteur, Financier) — reproductibilité à l'identique, test dédié. |
| 1.7 | `scripts/recette_exports1.py` devient un cas de la sonde de cohérence : les quatre témoins au golden, `fiche.json` en référence, mots interdits en contrôle distinct. |

**Recette** : un bloc rendu sur les quatre témoins ; le test doré tourne dans la sonde.

---

## Lot 2 — Dossier (= Flash)

Gabarit : `maquette-dossier.html`, dix sections. Le Flash est le même document sans la section 9, sous-titre « Rapport Flash », préfixe `FL-`.

| # | Travail |
|---|---|
| 2.1 | Les dix sections branchées sur les ids. Section 3 = `potentiel` (trois lignes + verdict). Section 2 = zonage complet (destinations et CDAC via `plu_destinations`, servitudes traduites, ER/EBC, DPU, drapeau « prescriptions non vérifiables » sur les quatre communes). |
| 2.2 | **Ajouts de la relecture** : prix d'achat historique de la parcelle (section 1 ou 5) · divisibilité (section 3, `divisible_classe`) · permis déposés sur la parcelle (section 5, si D-b est rattachable — sinon le dire dans le compte rendu) · gabarits voisins (section 3, LiDAR MNH ou BD TOPO) · copropriété (section 1, si la donnée existe). |
| 2.3 | **Correction** : la section 7 sert le périmètre réellement calculé avec son mode dans le titre (« 10 min en voiture » tant que le piéton n'est pas branché). Jamais un titre piéton sur un chiffre voiture. |
| 2.4 | Section 9 : encart « renseignez votre opération » si aucun questionnaire rempli pour ce projet ; sinon la section reprend le bloc Financier. Absente du Flash. |
| 2.5 | Flash : plus aucun renvoi vers l'app ; glossaire en fin (SDP, PPR, U1a, VEFA, ABF, CDAC) ; archivage JSON + PDF à l'achat (`flash_commandes` inchangée). |

**Recette** : Dossier sur les quatre témoins (T3 zone N doit dire « non constructible » avec sa cause ; T4 le drapeau à cheval) ; Flash = Dossier moins section 9, diff vérifié ; aucun ◌ dans le rendu (les blocs marqués ◌ dans la maquette sont branchés ou absents, jamais imprimés avec une valeur d'exemple).

---

## Lot 3 — Résumé

Nom du document : **Résumé** (décision Vic 07/09 — remplace « PDF »). Gabarit : `maquette-pdf-resume.html`, trois pages. Mêmes blocs que le Dossier, sélection courte. Ajouts : la ligne du prix d'achat historique ; le renvoi « version complète : Dossier parcelle · bilan chiffré : Financier ». Remplace l'export brut de la fiche (chaîne sans métadonnées Producer), qui disparaît au lot 8.

---

## Lot 4 — Le questionnaire du Financier (écran de l'app)

Peut être détaché en mandat séparé si la session le demande ; il est ici parce que le lot 5 ne peut pas exister sans lui.

Quatre écrans, persistés dans le Projet de l'utilisateur, chaque champ portant un id de portée `projet`. **Tout champ vide reste vide** : il s'imprime « non chiffré », il n'est jamais remplacé par un défaut.

| Écran | Champs | Pré-remplissage |
|---|---|---|
| 1 · Votre projet | scénario (reconstruction / réhabilitation / surélévation) · logements visés · typologie moyenne · part de logement social ou intermédiaire · stationnement (sol / sous-sol / silo) | `potentiel` (scénario dominant, fourchette de logements) ; mixité de la zone |
| 2 · Le foncier | prix demandé · prix déjà refusé · frais d'acquisition (%) · commission d'apporteur · démolition · dépollution / étude de sol | frais 7 % proposés ; démolition « non chiffré » |
| 3 · Vos coûts | coût de construction €/m² · honoraires techniques (%) · VRD et raccordements · coût par place de stationnement · aléas (%) · taxe d'aménagement | fourchette sourcée EPTB/CDC ; VRD modulés par la viabilisation ; TA calculée |
| 4 · Vos conditions | prix de sortie €/m² · prix de vente au bailleur (part sociale) · marge visée (%) · **régime de TVA** · durée de portage (mois) · apport et taux (facultatif) | neuf observé, ancien en repère ; 8,5 % ; durée = délai d'instruction + 20 mois |

Chaque pré-remplissage affiche sa source en une ligne sous le champ. Le bouton « Financier » de la fiche ouvre l'écran 1 si aucun questionnaire n'existe pour ce projet, sinon le document.

**Recette** : un questionnaire rempli sur T1, un questionnaire vide sur T2 (le document doit sortir quand même, avec « non chiffré » partout où il faut et un résultat en « maximum »).

---

## Lot 5 — Financier

Gabarit : `maquette-financier.html`, corrigé par la relecture.

| # | Travail |
|---|---|
| 5.1 | **HT partout** (décision Vic 07/09) : CA HT = prix de sortie TTC ÷ (1 + taux du régime) ; chaque ligne porte HT ou TTC ; encart « régime retenu : … — à confirmer avec votre expert-comptable ». |
| 5.2 | **Les postes** : chiffre d'affaires (part libre + part sociale au prix bailleur) · frais d'acquisition · démolition · dépollution · construction · honoraires techniques · VRD · stationnement · aléas · taxe d'aménagement · redevance d'archéologie · portage (durée × taux, ou forfait si le client n'a pas saisi de taux) · marge et frais. Chaque poste : sa valeur, sa nature (projet / estimé / dérivé), « non chiffré » si vide. |
| 5.3 | **Charge foncière** à trois bornes, jamais un point seul ; **sensibilité double** (coût de construction × prix de sortie, tableau 3 × 3) ; **seuil de rentabilité** : le prix d'achat qui atteint la marge visée ; **prix de revient au m²**. |
| 5.4 | **Verdict** en tête, déterministe, avec la mention « maximum » si un poste est non chiffré. |
| 5.5 | Face au prix demandé : écart, marge résiduelle, comparaison au terrain nu de marché et à la valeur de réhabilitation — le bloc de la maquette. |
| 5.6 | Calendrier sommaire (acquisition → études → chantier → livraison) déduit de la durée de portage. |
| 5.7 | Marché en regard, nuage retenues/écartées, vigilance non chiffrée, « ce que ce document n'établit pas » — repris du Dossier, mêmes ids. |

**Recette** : sur T1 avec questionnaire rempli, refaire le calcul à la main dans le compte rendu (comme la relecture l'a fait) et le retrouver au centime ; sur T2 sans questionnaire, document en « maximum » sans une seule valeur inventée.

---

## Lot 6 — Apporteur

Gabarit : `maquette-apporteur.html`. PDF à champs remplissables (WeasyPrint `pdf_forms=True` sur les `input` et `textarea` du gabarit — vérifier le rendu dans Aperçu et Acrobat). Questionnaire adaptatif : blocs conditionnels sur bâti / personne morale / usage industriel proche. Ajouts : mention de non-mandat en tête (« ce document ne vaut pas mandat… »), date d'émission et validité 90 jours, prix d'achat historique, case « le propriétaire est-il joignable, par quel canal ». Émetteur = compte de l'utilisateur, non modifiable. Archivage JSON + PDF à la génération.

---

## Lot 7 — Pré-dossier PC

Corrections listées dans `maquettes/LISEZMOI.md` et l'audit : CERFA 13406 ou 13409 selon le scénario du `potentiel` (liste de pièces adaptée) · PCMI4 gagne PPR, bruit, servitude PM1, ABF · fiche de zonage gagne destinations, articles, délai d'instruction, taxe d'aménagement, redevance d'archéologie · PCMI1 : parcelle repérée par un cercle, ratio d'échelle · PCMI2 : deux bâtiments, cotes des côtés · plus de ligne coupée sur deux pages · `EPSG` retiré des légendes.

---

## Lot 8 — Éteindre l'ancien

Après recette des lots 2 à 7 seulement. Supprimer : `briques_pdf.py` (Banquier), `argumentaire.py` (Argumentaire), l'export brut de la fiche, `pdf_zone.py` et `pdf_projet.py` (chaînes FPDF), la route et la chaîne `/lettre-zonage`, le gabarit Flash 1.4. Routes anciennes → redirection vers le nouveau document équivalent (Banquier et Argumentaire → Financier, avec l'encart questionnaire s'il n'est pas rempli). Boutons de la fiche, dans cet ordre : **Dossier · Résumé · Financier · Apporteur · Pré-dossier PC** — cinq, et rien d'autre. Aucun bouton « PDF », « Banquier », « Argumentaire », « Projet » ni « Lettre de zonage » ne subsiste. La page publique Flash inchangée côté paiement, nouveau document côté livraison.

---

## Recette finale

1. `generer.sh` sur les quatre témoins → cinq documents chacun, plus le Flash.
2. Sonde de cohérence verte : écran = PDF sur chaque id lu ; mots interdits à zéro ; zéros gardés.
3. Le Financier de T1 recalculé à la main dans le compte rendu.
4. **Captures avant/après au cadrage de Vic** pour chaque document (règle RETOURS-12) — un document n'est « fait » qu'avec ses captures.
5. Aucun ◌, aucune valeur d'exemple, aucun renvoi vers l'app dans un document livré hors compte.
6. Sur la bascule q_v12 si elle est faite ; sinon sur q_v11, et une seconde passe de recette après bascule.

## Compte rendu attendu
Par lot : ids créés ou modifiés, fichiers, témoins avant/après, recette. En fin : ce qui n'a pas pu être rattaché (D-b, D-e), les questions ouvertes, et la liste des chaînes supprimées au lot 8.
