# MANDAT PLU-LE TAMPON — RAPPORT (ÉCLAIREUR ancien format)

> Commune n°2, statut SÉRIE mais cadrage « éclaireur » (revue GO) : premier règlement ANCIEN
> format (articles préfixés 1-14, 137 p.), son coût réel décide du plan de nuit sur les
> communes restantes. Contrainte respectée : AUCUNE mesure en base (écart repli/calibré,
> échantillon, comptes de pool par zone) — extraction PDF → YAML + golden uniquement ;
> les mesures se feront en une passe groupée sur GO de Vic.

## 1 · Temps effectif MESURÉ (horodatages système, 27/07/2026)

| Heure | Jalon |
|---|---|
| 21:41:48 | START — Point A allégé : inventaire manifeste (30 libellés, 391 polygones) par awk ; concordance millésime RÉUTILISÉE de l'audit fraîcheur du matin (`97422_PLU_20230811` = GPU ✓, zéro travail neuf) ; pré-identification O12 (Ue, 1AUe, 2AUe + famille 2AU*) |
| 21:42:16 | Texte intégral extrait (137 p., règlement déjà téléchargé lors du sondage pilote) |
| 21:42 → 21:45:19 | **Lecture des 8 chapitres** : Ua détaillé, puis Ub/Uc/Ud/Ue en batch grep (articles 6/7/9/10/12/13 aux positions attendues), chapitre AUindicée in extenso (renvois), caractères de zones (secteurs Uav/Ucto/indice m), vérif COS (zéro occurrence) — **~3 min** |
| 21:45:55 → 21:47:41 | **Écriture du YAML complet** (15 entrées + 5 gels 2AU + décisions A/N) + smoke sur les 30 libellés — **~2 min** |
| 21:47:58 | Golden (API démarrée avec `PGOPTIONS lock_timeout=1000` pour ne pas poser de convoi de verrous pendant le job O12 — leçon §9 appliquée) |
| *(commit)* | *(horodaté au commit ci-dessous)* |

**EXTRACTION PURE : ~6 minutes** (lecture 3 + écriture/smoke 2 + Point A ~1). Bout-en-bout
avec golden et rapport : ~20-25 min.

## 2 · L'ancien format coûte-t-il plus cher ? NON — il a coûté MOINS cher, et voici où

Comparaison directe avec Saint-Pierre (moderne, 227 p., 45 libellés, 27 min d'extraction) :

| Poste | Saint-Pierre (moderne) | Le Tampon (ancien) | Verdict |
|---|---|---|---|
| Localisation des règles | Chapitres 1/2/3, sections numérotées par thème | Articles préfixés Ua6/Ua7/Ua9/Ua10/Ua12/Ua13 aux MÊMES positions dans chaque chapitre | Ancien = grep direct, PLUS RAPIDE |
| Emprise | Règles À TIROIRS par tranche de surface (arbitrage pool servi requis, requête DB) | « Non réglementée » PARTOUT (comme Saint-Paul) | Ancien = trivial ici |
| Habitat interdit | Tableaux de destinations V/X/V* à interpréter | Prose courte (caractère de zone + Art. 1.2 « sont interdits ») | Équivalent, prose légèrement plus rapide |
| Renvois | Chapitres communs U/AU explicites | Chapitre AU unique à renvoi d'indice + renvoi spécial AUto→Ucto | Ancien = 1 chaîne à résoudre (~5 min incl. lecture), SEUL surcoût notable |
| COS résiduel post-ALUR | n/a (2024) | **Non rencontré** (zéro occurrence — révision 2018 propre) | Piège théorique, pas vu |
| Hauteurs | he+hf systématiques + bonus conditionnels nombreux | he+hf systématiques (Ue : égout seul), bandes en limite en note | Équivalent |
| Règles conditionnelles | Bonus mixité/CBS, gabarits de front de rue | Densités MINIMALES 1AU (note), gel conditionnel 2AU | Équivalent |

**Réserves d'honnêteté** : (a) Le Tampon est une révision 2018 très bien tenue — un ancien
règlement de 2007 (type Saint-Leu) peut être plus sale ; (b) 137 p. vs 227 p. et 30 libellés
vs 45 ; (c) la contrainte « pas de DB » a retiré le poste d'arbitrage des tranches… qui
n'existait pas ici de toute façon (emprise non réglementée). Même corrigé de tout ça,
l'ancien format ne montre AUCUN surcoût structurel.

## 3 · Les leçons du §9 ont-elles fait gagner du temps réel ? OUI — ~10-15 min évitées

| Leçon appliquée | Gain concret |
|---|---|
| Concordance millésime déjà auditée (garde-fou du matin) | Point A ramené à ~1 min (vs 12 min au pilote) |
| « Tableau des destinations / Art. 1 D'ABORD » | Ue identifié habitat-interdit (y compris gardiennage) et Ucto/tourisme AVANT de lire leurs articles chiffrés — pas de lecture inutile |
| Pré-identification O12 (`o12_zones_activite.yaml` : Ue, 1AUe, 2AUe) | Les 3 zones à vérifier en priorité connues d'avance ; le règlement a CONFIRMÉ la liste (niveau « inféré » → désormais « explicite » pour Le Tampon) |
| « Préambules porteurs de droit » | Caractères de zones lus systématiquement → secteurs Uav/Ucto/indice « m » et système AU compris en une passe |
| Conventions de gravure établies (null sourcé, gel via zones_au_st, renvois explicites pour codes à préfixe chiffré) | Zéro hésitation de schéma, friction F2 réappliquée telle quelle |
| Pipeline outillé (dump texte paginé, smoke resolve_zone sur le manifeste) | Déjà écrit au pilote, réutilisé tel quel |
| Piège convoi de verrous (base partagée) | API golden lancée avec `lock_timeout` → zéro blocage du job O12 |

## 4 · Le Point d'arrêt A est-il automatisable pour une série sans supervision ?

**Mécanique (scriptable tel quel, prouvé sur 2 communes)** :
- Concordance de millésime : API GPU `?grid=insee` vs idurba du manifeste (c'est déjà la
  logique du garde-fou `check-plu-fraicheur`) + alerte dépublication.
- Téléchargement de l'archive + extraction du règlement (chemin standard
  `Pieces_ecrites/3_Reglement/`) + md5 + nombre de pages + offset PDF/imprimé (détectable en
  comparant numéros imprimés en pied de page).
- Inventaire des libellés du manifeste + surfaces + croisement liste O12.
- Détections d'alerte : COS (grep), « Non réglementé » par article, présence de chaque
  libellé du manifeste dans le texte du règlement (les absents = à examiner).

**Jugement requis (NON automatisable sans supervision)** :
- Rattacher chaque libellé GPU à son chapitre/secteur quand la casse ou la graphie divergent
  (UCto↔Ucto, UCtom↔« indice m » : introuvables par grep naïf, résolus par lecture du
  caractère de zone).
- Décider la CATÉGORIE d'une zone (habitat interdit ? gel conditionnel ? STECAL ?) — c'est
  de la lecture de prose (Ue interdit l'habitat Y COMPRIS le gardiennage : un pattern-match
  « gardiennage » aurait conclu l'inverse du texte).
- Résoudre les chaînes de renvoi (AUto→Ucto) et leur périmètre exact.
- Choisir la valeur quand plusieurs coexistent (bandes en limite vs hauteur générale).

**Format recommandé pour le plan de nuit** : Point A automatisé en pré-vol (le script sort un
dossier par commune : concordance, règlement extrait, inventaire, alertes), extraction et
catégorisation par Fable commune par commune. Le pré-vol peut tourner EN AMONT pour les 19
communes de série en une passe (~30 min de machine, aucun verrou base).

## 5 · Couverture livrée (config/plu_le_tampon.yaml)

30/30 libellés du manifeste traités : 9 calibrés habitat admis (Ua, Uav, Ub, Uc, Ucm, Ud,
1AUa, 1AUb, 1AUc) · 6 calibrés habitat interdit sourcé (Ue, UCto, UCtom, 1AUe, 1AUto, 1AUcto)
· 5 gels conditionnels 2AU* (ouverture soumise à l'aménagement des 1AU du pôle SAR,
Art. AUindicée 2.2.3) · 10 A/N non calibrés sur décision motivée (dont STECAL Aba et Nto1-5).
Zéro valeur non sourcée ; `source.reglement_grave` posé (md5 réel du PDF).
Emprise « Non réglementée » partout (situation Saint-Paul) → aucune friction de tranche.

Écart de discipline documenté : les lots U et AU ont été gravés d'UN TENANT (un seul commit de
contenu) — le chapitre AU unique à renvois rend le découpage artificiel ; golden passé sur
l'état complet.

## 6 · Golden et validation

- **Golden : DIFFÉRÉ à la fenêtre groupée — impossibilité PROPRE, documentée.** Le golden
  exige l'API locale, dont le boot exécute un `ALTER TABLE parcels` (ACCESS EXCLUSIVE). Le job
  O12 écrivait sur `parcels` au moment du run : tout boot d'API aurait posé le verrou en file
  et bloqué les autres sessions (le convoi du début de soirée). La parade tentée
  (`PGOPTIONS -c lock_timeout`) est INOPÉRANTE : `db.py` passe `connect_args={"options": …}`
  qui ÉCRASE PGOPTIONS (constaté : API pendue au startup, orphelins nettoyés proprement,
  aucun verrou laissé). → Correction de la leçon §9 « base partagée » : il n'existe AUCUN
  moyen sans modification de code de booter l'API sans risque de convoi pendant une
  ingestion ; le golden se passe en fenêtre calme, point. (Piste pour un mandat outillage :
  flag `LABUSE_SKIP_SCHEMA_HEAL=1`, une ligne dans le lifespan.)
- **Porte de lot effectivement utilisée : smoke `resolve_zone` sur les 30/30 libellés du
  manifeste** (sortie en session : chaque libellé dans sa catégorie attendue) + relecture
  systématique des numéros de page par script (14 corrections de citations appliquées avant
  commit — 3 pages fausses sur Ue, précisions Uc2.2).
- Le fichier ne touche que la commune Le Tampon (mode progressif) — le golden du pilote a
  déjà validé 3 fois que l'ajout d'un YAML communal ne bouge ni les 116 parcelles de
  référence ni les tiers. À confirmer au golden groupé.
- Mesures DB (échantillon, écart repli/calibré, pool par zone) : EN ATTENTE du GO groupé.

## 7 · Chiffres pour le plan de nuit

- **Extraction pure : 6 min (ancien format) vs 27 min (moderne, avec tranches)** — la vraie
  variable n'est PAS l'âge du format mais (a) la présence de règles à tiroirs et (b) la
  propreté du document.
- Projection par commune de série (Point A pré-volé) : **15-40 min de travail effectif**
  par commune, golden compris — soit, pour les 19 restantes calibrables : **1 à 2 jours-homme
  au total**, très en-deçà de l'estimation 3-5 j-h d'hier soir. Réserve : règlements anciens
  non révisés (pré-2010) et communes à secteurs proliférants peuvent doubler leur coût
  unitaire ; Saint-André/Saint-Leu restent hors série (sources).
