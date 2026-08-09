# M54-EXPO · Volet B — Rapport de MESURE (avant tout code)

Mandat : pour les 3 endpoints « douteux », mesurer la redondance avec l'existant AVANT de
décider. Redondant → retrait sur preuve. Différent/complémentaire → brancher (explain) ou
proposer une UI minimale et **s'arrêter pour validation Vic** (watch-zones/alertes).

---

## B1 — `GET /parcels/{idu}/explain` → **DIFFÉRENT → à brancher**

**Ce que fait l'endpoint** (`app.py:3284` → `assistant.explain_parcel`, assistant.py:337) :
synthèse IA **en prose de TOUTE la fiche** (verdict, capacité, résiduel, contraintes) via
l'API Anthropic, avec repli déterministe `rules_summary` si clé absente/timeout (jamais 500).

**Surfaces IA déjà présentes sur la fiche (mesuré) :**
| Surface | Fichier | Ce que c'est | Couvre une synthèse fiche ? |
|---|---|---|---|
| `AvisIA` | AvisIA.tsx:9 | Cartouche **statique** (CLIENT.avisIa) — disclaimer, identique partout | **Non** (texte fixe, pas une synthèse par parcelle) |
| `AskBar` / `/ask` | AskBar.tsx, api.ts:411 | **Q&R** IA groundée (l'utilisateur pose une question) | **Non** (à l'initiative de l'utilisateur, pas une synthèse en 1 clic) |
| `faisabiliteExplain` | api.ts:464 (`/modules/faisabilite/{idu}/explain`), câblé Fiche.tsx:836 | Prose IA **de la FAISABILITÉ** uniquement | **Non** (périmètre faisabilité, pas le verdict/toute la fiche) |

**Preuve de non-redondance** : aucune surface ne fournit une **synthèse IA en un clic de la
fiche entière**. `faisabiliteExplain` est le plus proche mais strictement limité à la faisabilité.
**Verdict : DIFFÉRENT.** → **Brancher** un bouton discret « Synthèse IA » sur la fiche.
⚠ Caveats à porter au branchement : (1) appel Anthropic (coût) — le repli déterministe existe ;
(2) l'endpoint n'a **pas** de gate quota (contrairement à `/ia/search`, `/ia/entretien` qui sont
`auth+quota`) — à confirmer avec Vic si on veut l'aligner sur la porte IA. Branché en Volet A′.

---

## B2 — `GET/POST/DELETE /watch-zones` + `/alertes*` → **COMPLÉMENTAIRE → UI proposée, STOP Vic**

**Ce que fait le système** (`app.py:3623-3690` → `labuse/alertes.py`) : l'utilisateur **dessine
un polygone** (zone de veille) ; le moteur croise des faits réels déjà ingérés et produit deux
types de « nouveautés » (alertes.py:8-9) :
- `dvf_in_zone` : une **vente DVF** tombant dans la zone dessinée (alertes.py:94 `ST_Contains`) ;
- `permit_near_followed` : un **permis SITADEL** à ≤ R d'une parcelle suivie (alertes.py:103).

**Comparaison au système events/cloche (M-T)** :
| Capacité | events/cloche (M-T) | watch-zones/alertes | Verdict |
|---|---|---|---|
| Permis près d'une parcelle **suivie** | `event_log kind='permis'` (events.py) | `permit_near_followed` | **REDONDANT** (même fait, deux chemins) |
| **Vente DVF** dans un **polygone dessiné** | — (aucun équivalent) | `dvf_in_zone` | **UNIQUE** |
| **Dessiner** une zone géographique de veille | — (veille = critères/parcelle) | `POST /watch-zones` (polygone) | **UNIQUE** |
| Veille par critères / requête | `/events/searches`, `/events/veille-nl` | — | (events uniquement) |

**Preuve** : le recouvrement se limite au `permit_near_followed` (déjà couvert par la cloche).
Le cœur de watch-zones — **dessiner une emprise et capter les ventes DVF qui y tombent** — n'a
**aucun équivalent** dans events (veille géographique ≠ veille par parcelle/critère). Table et
cloison `compte_id` vivantes (M-K). **Verdict : COMPLÉMENTAIRE, pas redondant.**

### UI minimale proposée (NON construite — attente validation Vic)
1. **Dessin de zone** : réutiliser l'outil « mesure » polygone de `MapView` (déjà présent) → au
   double-clic de fermeture, bouton « Créer une veille sur cette zone » → `POST /watch-zones`
   `{name, commune, geometry}`. Effort : moyen (brancher le polygone existant + un nom).
2. **Panneau « Mes veilles »** : liste des zones (`GET /watch-zones`) + flux d'alertes
   (`GET /alertes?only_new`), chaque item « acquitter » (`POST /alertes/ack`), bouton global
   « Rafraîchir » (`POST /alertes/refresh`). Effort : une page/onglet (moyen).
3. **Dédup avec la cloche** : masquer les `permit_near_followed` du flux alertes (déjà dans la
   cloche) OU au contraire retirer l'émission permis d'alertes et ne garder que `dvf_in_zone` —
   **décision Vic** (deux sources pour le même fait sinon).

**→ STOP. On ne construit pas cette UI sans l'arbitrage Vic** (périmètre + dédoublonnage permis).

---

## Synthèse Volet B
- **explain** : différent → **branché en Volet A′** (bouton « Synthèse IA », avec caveats coût/quota).
- **watch-zones/alertes** : complémentaire (unique = DVF-en-zone dessinée) → **UI proposée
  ci-dessus, arrêt pour validation Vic** avant tout code. Rien retiré (aucune preuve de pure
  redondance ; seul `permit_near_followed` doublonne, à arbitrer, pas à supprimer unilatéralement).
