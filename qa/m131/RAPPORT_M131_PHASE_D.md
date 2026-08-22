# M131 — Phase D : EP 1044, d'où vient « zone fermée à l'urbanisation »

**Rapport seul, aucun correctif.** La cascade est hors périmètre ; ce diagnostic
conditionne le futur traitement (rejoint M130-6 F.2).

## Constat

`EP 1044` est en zone **`Us`** — une zone **urbaine** (peu dense, gelée
provisoirement). Sa ligne SDP affiche : **« aucune (zone fermée à l'urbanisation) »**.
« Fermée à l'urbanisation » est le vocabulaire des zones **AU** (à urbaniser
futures) — il ne correspond pas au statut d'une zone **U gelée provisoirement**.

## La chaîne exacte (critère → cause → libellé)

| Étape | Fichier:ligne | Ce qui se passe |
|---|---|---|
| 1. Critère | `faisabilite/engine.py:194` | `if not rules.constructible_neuf:` — Us a `constructible_neuf=False` (branche `zones_au_st` de `plu_rules`, car `Us` ∈ `zones_au_st.liste` de Saint-Pierre). |
| 2. Cause moteur | `faisabilite/engine.py:201` | émet `cause="zone_transition"` — **la MÊME cause pour toute zone à construction neuve interdite** (Us gelée, AU0 fermées, AU*st). |
| 3. Réécriture cache | `faisabilite/residuel.py:64` | `zone_transition` → `"zone_non_constructible:Us"` (le cache écrit « la famille lisible + le code de zone »). Vérifié : `parcel_residuel.cause('EP1044') = zone_non_constructible:Us`, sdp = 0. |
| 4. Libellé affiché | `api/pdf_projet.py:23` (`_cause_txt`) | `"zone_non_constructible"` → **« zone fermée à l'urbanisation »**. |
| 5. Ligne SDP | `api/pdf_projet.py:370` | « SDP résiduelle : aucune (zone fermée à l'urbanisation) ». |

**Critère unique** : `constructible_neuf == False`. Il ne distingue pas *pourquoi*
la construction neuve est interdite — **gel provisoire d'une zone U** (Us) vs
**zone AU future fermée** (AU0/2AU) reçoivent le même `zone_transition`, donc le
même libellé « zone fermée à l'urbanisation ».

## Diagnostic

Le libellé « zone fermée à l'urbanisation » est **exact pour les AU** (2AU/AU0)
mais **imprécis pour `Us`** (zone urbaine existante, gelée *provisoirement* dans
l'attente d'une modification du SCoT — cf. préambule Us, règlement p.129). C'est
le **même point de conflation Us / AU0** que la dette **M130-6 F.2** : le
mécanisme `zones_au_st` regroupe une zone U gelée avec des zones AU fermées, et la
cause `zone_transition` / le libellé unique ne les séparent pas.

## Traitement (hors périmètre M131 — à arbitrer)

Distinguer, au niveau de la cause (`engine.py`) ou du libellé (`_cause_txt`), le
**gel provisoire d'une zone urbaine** (ex. « zone urbaine, construction neuve
suspendue ») de la **zone à urbaniser fermée**. Touche la cascade / l'affichage
des causes → **hors périmètre M131**, consigné, rejoint M130-6 F.2. Aucun
correctif appliqué.
