# M26-B — Constat : charges supportables incohérentes fiche ↔ copilote (sujet BACK)

**Origine** : revue Point B (Vic) — chiffres jugés anormaux sur les 20 restituées.
**Verdict** : pas de faute d'unité côté front ; payload fidèle à son moteur ; mais une
**divergence d'hypothèses entre la fiche et le copilote** sur la même parcelle.
Aucune correction au M26-B (front seul) — mandat back à tirer.

## Vérifications faites (parcelle #01 du run `93c22e53`, IDU 97415000CX1395)

| Grandeur | Payload copilote | Contre-épreuve directe | Verdict |
|---|---|---|---|
| `prix_probable_eur` | 204 288 € | `dvf_secteur_medianes` secteur `97415000CX`, terrain, 14 ventes : 336 €/m² × 608 m² = 204 288 € | **exact à l'euro** |
| `surface_m2` / `sdp_m2` | 608 / 467 | fiche `/modules/faisabilite/…` : SDP 467, SHAB 368 | cohérent |
| `charge_fonciere_eur` | **449 339 €** | fiche (même `compute_bilan`, même SHAB 368) : **216 579 €** | **divergent ×2,07** |

Fourchettes des 20 restituées (euros) : prix 97 950 → 444 268 ; charge −236 204 → 1 165 550
(0 € et négatifs = opération non viable même à foncier gratuit — sortie légitime du bilan
à rebours, mais troublante à l'écran sans explication).

## Cause prouvée

- fiche : `api/modules.py:801` → `hyp = Hypotheses()` (défauts du code) ;
- copilote : `copilote/moteurs.py:357` → `hyp = Hypotheses.charger()` (hypothèses chargées).

Reproduction (exacte à l'euro) :
`compute_bilan(368, 608, sector_price(…), hyp)` → central **216 579** avec `Hypotheses()`,
**449 339** avec `Hypotheses.charger()`.

## À trancher au mandat back

1. Quelle source d'hypothèses fait foi (la fiche est probablement celle en défaut :
   elle ignore les hypothèses chargées) — une seule vérité pour fiche, copilote et PDF.
2. Présentation des charges ≤ 0 dans le payload copilote (mention explicite « opération
   non viable au prix du marché » plutôt qu'un montant négatif nu ?) — décision produit.

## Au passage — golden

`qa/golden_check.py` vise par défaut `LABUSE_API_BASE=127.0.0.1:8010` ; rien n'écoute
sur :8010 sur ce poste → 32 « api.\* absent » trompeurs. Pointé sur l'instance réelle :
**116/116 PASS** (28/07, instance de ce clone). À savoir pour les prochains mandats.
