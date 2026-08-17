# AUDIT M100 — LES PARCELLES INVISIBLES (faux négatifs de filtre)

Audité le 2026-08-17, run servi q_v9_m81, base locale. **Aucune correction appliquée — Vic
arbitre, les correctifs seront des mandats dédiés.** Inventaire complet des critères
filtrables (recherche ~40 facettes, 28 outils, 7 outils Copilote, carte, suivis/veilles,
comparateurs) : chaque critère, sa colonne, sa fonction de comparaison — puis protocole M99
(variantes, coexistence, volumes) et chasse aux pliages divergents et exclusions muettes.

## Le compte, en tête

| famille de défaut | défauts confirmés | parcelles/objets concernés |
|---|---|---|
| critère à deux endroits (seuil divergent) | 1 | 29 228 parcelles (étiquette « fiable » sous la doctrine) |
| exclusion structurelle muette | 1 | 37 parcelles (rouge BODACC invisible à la facette Événement) |
| pliage asymétrique utilisateur↔colonne | 2 | dépend de la saisie (colonne PM 82 701 lignes 100 % désaccentuée) + 14 adresses |
| variante d'écriture (encodage) | 1 (latent) | 8 annonces mojibake / 8 parcelles — aucun servi faussé aujourd'hui |
| rapprochement par nom sans filet code | 1 | non mesurable en base (Copilote, garanti par prompt seul) |
| énumérations strictes silencieuses | 1 famille (risque) | couverture complète mesurée AUJOURD'HUI, dérive non gardée |
| candidats instruits et ÉCARTÉS | 5 | — |

**Total des parcelles rendues invisibles par un défaut servi aujourd'hui : 37** (facette
Événement). Les autres défauts sont soit des étiquettes trompeuses (29 228), soit
dépendants de la saisie (accents), soit latents (mojibake). Le détail est trié par volume.

---

## 1. Seuil « marché fiable » : 3 ici, 8 à la doctrine — 29 228 parcelles

**Nature : critère à deux endroits (motif « un critère = un seul endroit »).**
Le filtre `marche_fiable` qualifie un secteur de fiable à **n≥3 ventes**
(`app.py:1139-1143`, seuil codé en dur, antérieur à MANDAT_DVF) quand la doctrine figée
(`config/dvf_profils.yaml`, `seuil_effectif: 8` — « sous n≈8 la médiane oscille ±44 % »)
fixe la référence de marché à **n≥8**. Mesuré : **29 228 parcelles** ont un secteur à
3≤n<8 — étiquetées « données marché fiables » par le filtre alors qu'elles sont sous la
référence. Sens du défaut : faux POSITIF d'étiquette (pas des invisibles), mais la même
gravité de doctrine. Coexistence : sans objet (seuil, pas variante).

## 2. La facette Événement ne peut pas voir une écartée sous procédure — 37 parcelles

**Nature : exclusion structurelle muette.**
78 parcelles appartiennent à un SIREN dont la **dernière** annonce BODACC est dans la
liste ROUGE (procédure ouverte). 41 portent l'événement rouge au run ; **37 n'ont AUCUNE
ligne bodacc** : elles sont écartées à l'étage 0 (`faux_positif_probable`/`exclue`) et
l'étage 2 (couche bodacc) ne tourne pas pour elles — la comptabilité boucle exactement
(41+37=78, requêtes en historique de mesure ; cas témoin SIREN 438039448, résolution du
plan + LJ 2024-06-28, parcelles 97411000AE0896/897 : 62 lignes cascade, 0 bodacc).
Cohérent avec le périmètre par défaut (hors écartées) — mais en **voie manuelle**
(interrupteur analyse coupé), le filtre Événement ne peut structurellement jamais les
montrer, et rien ne le dit. Coexistence : sans objet.

## 3. Recherche propriétaire (Scan patrimoine M02) : les accents ne matchent jamais

**Nature : pliage asymétrique utilisateur↔colonne.**
`denomination ILIKE '%q%'` (`modules.py:197`) — ILIKE plie la casse mais PAS les accents,
et la colonne MAJIC est **100 % désaccentuée** (mesuré : 0 accent sur 82 701 lignes).
Toute saisie accentuée — « Société civile », « Réunion », « Pêcheurs » — rend **0
silencieux** ; la même saisie sans accents matche. Volume : dépend de la saisie (le stock
entier est concerné côté colonne). Coexistence : sans objet (la variante est côté saisie).
À noter : l'autocomplétion d'adresses, elle, plie les accents des deux côtés
(`translate()` symétrique, app.py:1545-1546) — le motif du correctif existe déjà ailleurs.

## 4. BODACC : mojibake à moitié mappé — latent, 8 annonces / 8 parcelles

**Nature : variante d'écriture (double encodage UTF-8).**
8 annonces sur 672 portent un libellé mojibake (4 formes). Le mapping de la cascade
(`config/cascade_rules.yaml:480-482`) n'en couvre que **2** ; les 2 non couvertes —
« Jugement d'ouverture d'une procÃ©dure de redressement judiciaire » (3) et « …de
sauvegarde » (1) — ont leur forme propre en liste **ROUGE** : classées « neutre » si
elles étaient servies. Contre-vérifié honnêtement : **aucune n'est la dernière annonce de
son SIREN** (les 4 SIREN ont des annonces propres plus récentes) → le servi n'est PAS
faussé aujourd'hui ; le défaut est **latent** (8 parcelles basculeraient mal si une
annonce mojibake redevenait déterminante — l'ingestion peut en produire de nouvelles).
S'y ajoute : le libellé BRUT est servi tel quel par les notifications (`events.py:326`)
et le Scan patrimoine (`modules.py:223`) — un utilisateur peut lire « DÃ©pÃ´t de
l'Ã©tat des crÃ©ances ». Coexistence : les deux graphies désignent le même libellé
(même nomenclature BODACC) — fusion sûre par nature du défaut d'encodage.
Variante voisine mesurée : « Autre jugement et ordonnance » (90) / « Autres jugements et
ordonnances » (1) — toutes deux neutres, sans effet servi.

## 5. Copilote : la commune est rapprochée par le prompt, sans filet code

**Nature : rapprochement par nom sans garantie.**
Le routeur demande au LLM « commune normalisée en toponyme réunionnais »
(`copilote_v2/router.py:121`) puis `compter_parcelles` passe la chaîne **brute** à
l'égalité stricte `p.commune = ANY(...)` (`outils.py:54` → `app.py:891-893`). Aucun
rapprochement code contre le référentiel `communes.py` : si le modèle rend « saint paul »
ou « St-Paul », le compte est **0 silencieux**. Atténuations réelles : la réponse cite
les critères interprétés (l'utilisateur peut voir la graphie utilisée), et la recette M78
mesurait 45/45 au gate. Volume : non mesurable en base (dépend des saisies) — le défaut
est l'absence de filet, pas un stock. Même motif sur `veilles.commune`
(`copilote_v2/veilles.py:81`, égalité stricte).

## 6. Autocomplétion adresses : 3 caractères hors table — 14 adresses

**Nature : pliage incomplet (table d'accents codée en dur).**
`_ADR_ACCENTS` (app.py:1518) plie 30 caractères mais pas **œ, æ, ÿ** : 14 adresses en
portent (ex. « rue des Bœufs ») — une saisie « boeufs » ne les trouve pas (et
réciproquement la graphie « oe » en base ne serait pas trouvée par « œ »). Volume : 14.

## 7. Famille de risque : les énumérations strictes qui ignorent en silence

**Nature : valeur inconnue → critère ignoré, requête ADOUCIE sans le dire.**
`tiers` (alias `_TIER_ALIAS`, outils.py:43-45 — 4 alias, valeur inconnue → None
silencieux), `signaux` (9 clés `_SIG_SQL`, app.py:965-999), `constructibilite` (5 clés),
`proprietaire_type` (3 clés), `etat_societe` (app.py:1091-1105 :
`etat_administratif='C'`, `famille IN ('radiation','pcl')`). Couverture mesurée
AUJOURD'HUI : complète — `bodacc_annonces_owner.famille` ne porte que radiation (208),
pcl (677), vente_cession (533, servie par le signal cession) ; `groupe_label` MAJIC est
une nomenclature fermée (10 valeurs, « Office HLM »/« …économie mixte » couvrent le motif
bailleur, 11 809 parcelles). Le défaut n'est pas le présent mais l'absence de garde :
une valeur amont NOUVELLE serait ignorée en silence (le motif M101-VTB, côté filtre).
Pas de volume aujourd'hui — famille à garder à l'œil, pas d'arbitrage requis.

---

## Candidats instruits et ÉCARTÉS (le test de coexistence a tranché)

| candidat | verdict |
|---|---|
| Abréviations de dénominations PM (« SCI X » vs « SOCIETE CIVILE IMMOBILIERE X » : 37 groupes, 74 dénominations) | **FUSION INTERDITE** — les 37 groupes portent TOUS des SIREN différents (0 groupe même-SIREN) : possiblement des entités réellement distinctes, pas des variantes. Dit, non tranché (mandat). |
| Noms de communes (parcels, sitadel, veilles) | 24/24/24 partout (brutes = casse = normalisées) — aucune variante. |
| Types SITADEL (`type`) | énumération propre PC:45 943 · DP:2 413 · PD:1 124 · PA:812 — pas de variante. |
| Classes DPE, catégories aménités OSM, subtypes risques (ppr/sup/friche/qpv/bruit/…) | 0 variante de casse ou d'écriture (mesuré kind par kind). |
| zone_plu / zonage / etat_sol / recherche IDU | sains post M99/M99-B/M101 — pliage PG des DEUX côtés (app.py:1055-1064), partition nu/bâti exacte, ILIKE simulplu ; l'inventaire d'un des agents a re-signalé zone_plu « divergent » par erreur : c'est le CORRECTIF M99-B qu'il lisait, contre-vérifié fonctionnel (NDé→10). |

## Les cas connus : toujours dits ?

- Copropriétés hors classement (M89) : **toujours dit** (RANG_PERIMETRE, « / N classées »)
  — vérifié au passage M96, inchangé.
- Exclusions DVF (M101) : **dites** en commentaire au point unique (VEFA/Échange/
  Adjudication/Expropriation hors médianes, VTB terrain seul).
- Cascade BODACC : les libellés hors listes → « neutre » par design, la décision est
  documentée pour « Liste des créances » (cascade_rules.yaml:478-479) ; restent
  non-documentés quelques libellés à 1-2 annonces (« Jugement de reprise de la procédure
  de liquidation judiciaire », « Jugement mettant fin à la procédure de sauvegarde ») —
  neutres aujourd'hui, à documenter ou classer un jour, volume ≤ 2 chacun.
- Totaux et périmètres : la ventilation par tier sépare les écartées (honnête) ; le rang
  porte son dénominateur nommé (M89) ; pas de compte nu trouvé dans les surfaces
  inventoriées — RAS sur l'échantillon parcouru, hors le cas n°2 (périmètre de la facette
  Événement jamais dit en voie manuelle).

## Annexe — l'inventaire des critères (résumé)

~40 facettes de la recherche (app.py:854-1162 : 15 numériques, 9 booléens/EXISTS, 8
énumérations, 3 textuels), 28 outils (patrimoine ILIKE, scoreur géométrique, annuaire PLU
FTS french + `upper(zone)=upper(:zone)` symétrique, permis/commune/nature égalité stricte
sur énumérations propres, comparateurs sur tiers), Copilote (7 outils, délégation à
filtre()/patrimoine()/…), carte (étiquettes, pas de filtre texte), suivis/veilles (IDU
strict 14 car., commune stricte, hash de filtres). Fonctions de comparaison citées ligne
à ligne dans l'historique de mesure de ce mandat (deux inventaires exhaustifs).
