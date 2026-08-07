# M51-P2 — Saint-Benoît : les fiches AU vs la calibration servie (LECTURE SEULE · liste d'écarts)

**Aucun changement de calibration.** Constat sur pièces (`97410_reglement_20200206.pdf`, opposable
GPU idurba `97410_PLU_20200206`, garde idurba+sha OK, ingéré P1). Les arbitrages viennent sur cette liste.

## Les fiches AU passées une à une (18 présentes — **N°04 absente**)
| Fiche | zone | recul voirie | régime 1AU | ER | PPR | secteur (p.PDF) |
|---|---|---|---|---|---|---|
| N°01 | AUp | 3 m | oui | oui | oui | Beauvallon pôle d'activités (54) |
| N°02 | AUb | **10 m** | oui | oui | — | Bourbier les Hauts – ch. Montjol (55) |
| N°03 | AUe | 3 m | oui | oui | oui | Beaulieu zone commerciale (56) |
| N°05 | AUa | 3 m | oui | — | — | Le Conardel habitat (57) |
| N°06 | AUb | 3 m | oui | — | — | Bras-Canot Sarda Garriga (59) |
| N°07 | AUb | 3 m | oui | oui | oui | Bras-Canot Prévoisy (60) |
| N°08 | AUa | 3 m | oui | oui | — | Le Cap les Bas Lataniers (61) |
| N°09 | AUa | 3 m | oui | oui | — | Le Cap les Bas Jonquilles (62) |
| N°10 | AUb | 3 m | oui | — | — | Le Cap les Bas Palmistes (63) |
| N°11 | AUb | 3 m | oui | — | — | Le Cap les Bas Impasse Louis (64) |
| N°12 | AUb | 3 m | oui | — | — | Le Cap les Hauts Lot. Baies (65) |
| N°13 | AUb | 3 m | oui | — | — | Le Cap les Hauts Lee-Fong (66) |
| N°14 | AUb | 3 m | oui | — | oui | Sainte-Anne ch. Blémir (67) |
| N°15 | AUb | 3 m | oui | oui | — | Sainte-Anne ch. Jacquemin (68) |
| N°16 | AUb | 3 m | oui | — | — | Sainte-Anne ch. Morange (69) |
| N°17 | AUb | 3 m | oui | — | — | Petit Saint-Pierre ch. Gallias (70) |
| N°18 | AUa | 3 m | oui | oui | — | Petit Saint-Pierre ch. Impérial (71) |
| N°19 | AUb | 3 m | oui | — | oui | Cambourg Amaryllis II (72) |

*(Pages PDF — pagination du document AMBIGUË, 2ᵉ bloc « Page 1..114 » ; ces p.PDF sont celles du fichier.)*

## Ce que la calibration SERT pour AU (`config/plu_saint_benoit.yaml`)
- `zones: {}` — **hauteurs AU DÉ-CALIBRÉES** (secteurs graphiques, arbitrage Vic 28/07) ✔ cohérent :
  les 18 fiches ne donnent **aucune hauteur** → la dé-calibration est confirmée, **pas d'écart** ici.
- Règles génériques AU servies : emprise 80 % (Art. AU 5), limites séparatives 1 m (Art. AU 7),
  espaces libres 20 % perméable (Art. AU 9), stationnement (Art. AU 12).
- `zones_au_st` (habitat interdit, capacité zéro) : Ue, Up, Ut, AUe3, AUp1.

## ÉCARTS — pour ton arbitrage (rien appliqué)
1. **Recul voirie NON servi.** Chaque fiche impose un **recul de 3 m** de la voie (**10 m** pour la
   fiche N°02, AUb Bourbier). La calibration sert le recul *séparatif* (1 m) mais **pas le recul
   voirie**. Un recul de 3–10 m réduit l'emprise constructible d'une parcelle AU → la capacité AU
   servie peut être **sur-estimée**. Le plus fort : N°02 (10 m). **Arbitrage : intégrer le recul
   voirie AU (3 m défaut, 10 m N°02) ou l'assumer hors périmètre ?**
2. **Régime 1AU (opération d'ensemble) — les 18 fiches le portent** : « constructions acceptées
   seulement dans une opération d'ensemble réalisant les équipements internes, OU après leur
   réalisation ». **Arbitrage : la capacité AU servie reflète-t-elle cette porte 1AU** (une parcelle
   AU isolée n'est pas constructible seule) **ou est-elle comptée comme constructible directe ?**
3. **N°04 ABSENTE** de la séquence AU (01-03, 05-19). 18 fiches AU, pas 19. **Constat brut, non
   fabriqué** : soit un trou de numérotation, soit une fiche classée hors bloc AU. **Arbitrage :
   vérifier en mairie si N°04 existe (zone AU non couverte ici).**

## Couvert AILLEURS (référencé par les fiches, PAS un écart de calibration)
- **PPR R1 non constructible** (8 fiches, ex. N°19 Cambourg : « secteurs en zone R1 non constructible,
  PPR approuvé 02/10/2017 ») → servi par la **couche PPR** (campagne PPR rouge/bleu). *À vérifier :
  la couche PPR est-elle active sur ces secteurs AU de Saint-Benoît ?* (hors calibration règlement).
- **Emplacements réservés** (8 fiches) → couche ER/servitudes, pas la calibration règlement.
- **Boisements à conserver** (N°19) → EBC/servitude, hors calibration.

## Incertitude M40 — RECONSIGNÉE, non fabriquée
L'annuaire sert le **PLU 2020 opposable** (idurba `97410_PLU_20200206`, présent au GPU, garde OK).
D'**éventuelles modifications n°2/n°3** approuvées postérieurement **ne sont PAS au GPU** (à confirmer
en mairie, hors open-data) — comme en M40. Rien n'est inventé : le verbatim servi est celui du 2020.

---

# M51-P2 — MESURES (les 4 réponses ; rien appliqué)

## Écart 1 — Recul voirie : DÉJÀ SERVI (5 m défaut), impact réel MARGINAL
**Constat qui renverse la question** : le moteur (`faisabilite/engine.py`) applique DÉJÀ un recul
voirie — `recul_voirie_defaut_m = 5 m` quand la zone n'est pas calibrée (Saint-Benoît `zones:{}` →
défaut 5 m, source « Art. 6 à_vérifier → hypothèse »). Ce n'est donc PAS « recul voirie absent » :
c'est un **défaut 5 m**.
- **17 fiches sur 18 = recul 3 m < 5 m servi** → capacité **CONSERVATRICE** (sur-recul de 2 m), **aucune
  sur-estimation**. Appliquer le 3 m exact AUGMENTERAIT légèrement la capacité — non requis pour la justesse.
- **Seule exception : N°02 (AUb2, Bourbier les Hauts) = 10 m > 5 m** → sous-recul de 5 m. Parcelles
  concernées : **4, TOUTES `reserve_fonciere`**, non déclassées. Impact géométrique mesuré (inset 5 m→10 m) :
  **perte d'emprise 27–57 %** (AE0025 32 %, AE0027 28 %, AE0250 27 %, AE0251 57 %) → SDP réduite >10 % pour
  les 4 **si** on corrigeait.
- **Verdict (ta règle) : MARGINAL** — 4 parcelles, toutes déjà en réserve (pas de brûlante/chaude). →
  **correction en config possible (recul_voirie 10 m pour AUb2/Bourbier), note au bilan, PAS de bascule.**
  ⚠ **Wrinkle à ton arbitrage** : ajouter une entrée `zones: {AUb2: …}` repasse `resolve_zone(AUb2)` en
  `calibree=True` → change le chemin `au_statut` de cette zone (aujourd'hui `conditionnelle_operation` via
  le sentier générique). Une correction recul-seul a donc un effet de bord sur la classification. **Je
  n'ai rien écrit** — tu tranches la forme (entrée dédiée recul-only sans toucher `calibree`, ou on
  documente le sous-recul de 4 parcelles réserve et on laisse).

## Écart 2 — Régime 1AU : PAS D'ÉCART, Saint-Benoît est raccordé
`parcel_au_statut` (chaîne train 6, AU-OUVERTURE) SERT déjà Saint-Benoît :
- **237 parcelles AUa/AUb = `conditionnelle_operation`** (la porte « opération d'ensemble » — zones AUa5,
  AUb2, AUb6…, = les fiches) ;
- **12 AUe3/AUp1 = `declasse_au_fermee`** (habitat interdit, cohérent `zones_au_st`).
Les 18 fiches **confirment le servi**. La porte 1AU est portée par la classification. **Rien à corriger.**
*(Nuance non bloquante : `conditionnelle_operation` est une VIGILANCE — les parcelles restent tiérées ;
si tu voulais que la porte pèse davantage sur le tier, c'est un débat de calibration séparé, pas un écart.)*

## Écart 3 — N°04 absente : consigné à ta liste mairie
Ajouté à la liste mairie Saint-Benoît : **« fiche AU N°04 absente du règlement GPU 2020 »** (avec les
modifs n°2/n°3, hors open-data). Rien d'autre — ta main.

## PPR R1 — couche ACTIVE, PAS de trou
**Correction d'un chiffre du bilan P2 : 5 fiches référencent le PPR (N°01, 03, 07, 14, 19), pas 8**
(le 8 était les emplacements réservés — confusion ER↔PPR, corrigée). Couche `ppr` présente pour
Saint-Benoît (3 INTERDICTION + 4 PRESCRIPTION) ; **268 parcelles Saint-Benoît `declasse_non_constructible`**.
Croisement spatial des parcelles AU **servies** ∩ PPR INTERDICTION (R1) :
- **AUb14 : 3 parcelles correctement déclassées** (la couche fire).
- **AUb7 (4 servies) et AUb19 (18 servies) : 0 intersection avec le R1** — les parcelles servies sont
  HORS R1 ; le « secteur R1 » des fiches est ailleurs dans la zone (cohérent : les fiches parlent de
  *secteurs*, pas de la zone entière).
→ **Aucune parcelle AU servie en R1 sans vigilance. Pas de trou de couche (famille EP0228).** On est tranquilles.

## Synthèse pour clôture
| écart | verdict | action |
|---|---|---|
| 1 Recul voirie | déjà servi 5 m ; 17/18 conservateur ; N°02 sous-recul, **4 parcelles réserve** | marginal → config (ta forme) + bilan, pas de bascule |
| 2 Régime 1AU | **pas d'écart** — raccordé (237 conditionnelle_operation) | rien |
| 3 N°04 absente | consigné | liste mairie (ta main) |
| PPR R1 | couche active, **pas de trou** (0 servie en R1) | rien |
