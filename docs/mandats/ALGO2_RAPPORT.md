# ALGO-2 — Features propriétaire · Rapport (A : inventaire — POINT D'ARRÊT)

**Branche** `feat/algo2-proprio` (base main, aucun code de feature écrit — le mandat A
l'exige). Champion `q_v7_defisc` INTOUCHÉ ; tiers au bit près jusqu'à décision Vic.
**Note session : mandat « Modèle Fable », session exécutée sur Opus 4.8.**

## A — INVENTAIRE (mesuré en base, 26-27/07/2026)

| Source | Couverture réelle | Profondeur historique | AS-OF (anti-fuite) |
|---|---|---|---|
| **Panel DGFiP PM** `pm_proprietaires_millesimes` | 72 709 → 81 161 parcelles/an (**~19 % du frame** — le reste = personnes physiques, hors périmètre DGFiP-PM par construction) | **6 millésimes : 2019-2024** | ✅ **OUI** — propriétaire as-of 01/01/Y = millésime Y-1 → **les 6 folds walk-forward (2020-2025) sont TOUS couverts** ; 2017-2019 (train) → bin « inconnu » consigné, comme la fenêtre DVF |
| DGFiP PM courant `parcelle_personne_morale` | 82 701 parcelles (19,2 %) | millésime unique | ⚠ seul = fuite ; sert le SCORING 2026, le panel sert le train |
| **SIREN valide** (clé de C) | **~87 %** des lignes PM (≈10,4 k lignes/an sans SIREN → fallback dénomination, qualité à MESURER en C) | par millésime | ✅ |
| **BODACC** `bodacc_annonces_owner` | 1 418 annonces matchées propriétaires (volume FAIBLE — features rares) | **2008 → 2026, daté** | ✅ parfait (`date_annonce`) |
| **INPI/enrichment** `owner_enrichment` | 9 703 SIREN enrichis, `date_creation` **99,97 %** (immatriculation, dès 1900) | historique par construction | ✅ (immatriculation < 01/01/Y) |
| Groupes DGFiP (type détenteur) | PM non remarquables 33 921 · Commune 24 536 · HLM 7 681 · État 5 804 · SEM 4 128 · Dépt 3 960 · EP 2 213 | par millésime | ✅ |
| Dormance RNE (`date_mise_a_jour_rne`) | snapshot 2026 SEULEMENT | **aucune** | ❌ **non entraînable as-of** |
| Âge dirigeant (`v_pm_propension_vendre`) | 9 337 SIREN | — | ⛔ **BOUSSOLE : personne physique → écarté d'office** (`nb_dirigeants`, compte anonyme, reste licite) |
| Indivision structurelle | **0 signal trouvé** (cascade : 0 ; groupes DGFiP : pas de classe indivision) | — | ❌ inexistant |
| RNIC | 2 220 copros | — | déjà consommé (flag copro du modèle) |

### Part PM dans les 4 communes cibles (le plafond de l'espoir du mandat)

| Commune | Parcelles PM (2024) | % du parc |
|---|---:|---:|
| Saint-Denis | 11 639 | **30,5 %** |
| Saint-Paul | 12 260 | **24,0 %** |
| Le Tampon | 5 249 | **12,3 %** |
| Saint-Joseph | 3 472 | **12,0 %** |

Lecture honnête : le bloc propriétaire a une vraie portée à **Saint-Denis/Saint-Paul**
(au-dessus de la moyenne île 19 %) ; au **Tampon et à Saint-Joseph** — les deux communes
significativement faibles d'ALGO-1b — il ne touchera qu'**une parcelle sur huit**.
L'objectif « remonter les grandes » est plausible pour SD/SP, modéré pour Tampon/St-Joseph.

### Verdict d'inventaire par feature candidate (B)

| Feature | Verdict | Motif |
|---|---|---|
| B1 type détenteur (PM/public/HLM/SEM…) | **GO** | groupes DGFiP par millésime, as-of ✅ ; PP = absence (flag, pas d'identité) |
| B2 tenure fine (continue + bins fins) | **GO** | DVF ext 2014+ déjà as-of dans le pipeline |
| B3 multi-détention (portefeuille commune/île) | **GO sous condition C** | SIREN 87 % ; le solde exige la résolution d'entités (précision ≥ 95 % ou refus) |
| B4 ancienneté société (immatriculation) | **GO** | date_creation 99,97 % des 9 703 enrichis (≈77 % des SIREN propriétaires — solde en « inconnu ») |
| B5 dormance (dépôts de comptes / RNE) | **ÉCARTÉE** | aucune profondeur historique : `date_mise_a_jour_rne` = snapshot 2026 → entraîner dessus = fuite pure. (Réexaminable si l'INPI historisé est ingéré un jour.) |
| B6 détresse BODACC as-of | **GO prudent** | daté 2008-2026 ✅ mais 1 418 annonces → feature RARE (attendre peu du coefficient) |
| B7 indivision/succession | **ÉCARTÉE** | aucune donnée STRUCTURELLE en base ; la reconstruire passerait par du nominatif (⛔ boussole) |

**Écartées boussole/faisabilité, motifs gravés** : âge dirigeant (personne physique
identifiable) ; B5 (fuite temporelle) ; B7 (rien de structurel, nominatif interdit).

---

## ⛔ POINT D'ARRÊT (exigé par le mandat A)

L'inventaire est présenté AVANT tout code de feature. Si tu valides :
1. **C d'abord** : résolution d'entités (SIREN direct 87 % + dénomination normalisée pour
   le solde), échantillon vérifié à la main, **refus de servir sous 95 % de précision** ;
2. **B** : B1, B2, B3 (si C ≥ 95 %), B4, B6 — B5 et B7 écartées ;
3. **D** : re-train complet challenger, walk-forward 6 folds seed 974, RR@1158 hors copro
   + IC95 + ECE + signes + **RR par commune** (Tampon/St-Joseph/SP/SD), permutation,
   **ablation bloc propriétaire** (delta avec IC), arène + gate boussole golden ;
4. **E** : verdict honnête — pas de promotion sans ΔRR significativement > 0 ;
   la bascule reste ta décision.

Attente à cadrer dès maintenant (honnêteté) : couverture PM ~19 % île → le bloc ne peut
déplacer qu'une minorité de rangs ; l'effet le plus probable est à Saint-Denis/Saint-Paul.
