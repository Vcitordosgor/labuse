# M38 — BILAN : « Permis déposés (pas seulement accordés) »

**Branche `m38-permis-deposes` · base main post-M37 (14ae2116) · NON mergée** (tu merges
`--no-ff` après revue visuelle). Modèle Opus. Objectif : ingérer la **datation au dépôt** des
permis, l'exposer en contexte de fiche, mesurer ce qu'elle changerait — **sans re-fit du modèle P**
(hors périmètre) et **sans changer un seul tier**.

## Ce que le mandat supposait vs ce qui existe (constat P0, vérifié sur pièces)

La prémisse — « un permis autorisé arrive des mois après le dépôt ; les refus/abandons sont
invisibles » — se **scinde en deux biais dont un seul est corrigeable** :

- ✅ **datation au dépôt** : `DR_DEPOT` (Sitadel3/SDES, même dataset déjà ingéré) donne la date de
  dépôt EXACTE, remplie à **99,9 %**, à granularité **parcelle** (99,3 %). Délai dépôt→autorisation
  médian **276 j**. → corrigeable.
- ❌ **refus / abandons / dossiers en instance** : le dataset open data est **autorisations-seules**
  (0 état « refusé », aucun datafile « déposés »). Ces permis **n'existent nulle part** en ouvert. →
  non corrigeable, on ne fabrique pas une donnée absente.

Arbitrage Vic : GO sur le **périmètre réel** (datation au dépôt + exposition contexte), fenêtre
**36 mois** (paramètre nommé), **deux lignes hiérarchisées** parcelle/secteur, étiquette
d'honnêteté imposée. Détail : `M38_P0_CONSTAT.md`.

## Livré

**P1 — Ingestion (`[M38-P1]`)**
- `sitadel_permits.date_depot` (Date), migration idempotente `ensure_sitadel_depot` (durable).
- Validateur `_date_depot` : même discipline que la date d'autorisation (invalide/future → None,
  brut tracé, compteur bruyant). Capté par backfill **et** delta (colonne du CSV déjà téléchargé —
  **aucune nouvelle source**). Backfill : `date_depot` rempli à **99,3 %** (49 936/50 292).
- Table dédiée aux permis (pas une feature de scoring) ; `date_depot` lu par **aucun calcul servi**.
- 4 verrous unitaires (`tests/test_permit_depot.py`).

**P2 — Bloc fiche « Activité de dépôt » (`[M38-P2]`)**
- `permits.depots_recents()` : **deux lignes distinctes, jamais fusionnées** — « sur cette
  parcelle : N dépôts sur 36 mois » (rattaché IDU) et « sur le secteur : N dépôts sur 36 mois »
  (section cadastrale, préfixe IDU 10). Fenêtre = `DEPOTS_FENETRE_MOIS` (**paramètre nommé**).
  Retourne None hors couverture → **aucun bloc vide**.
- Étiquette d'honnêteté (mot pour mot, arbitrage §4) :
  > **« activité de dépôt (permis aboutis — les refus et dossiers en cours ne sont pas publiés) »**
  Granularité affichée : « permis autorisés, datés au dépôt ». Jamais de visibilité temps-réel
  sous-entendue.
- **Sourcé + millésime = point de calcul UNIQUE** : l'ingestion écrit `source_millesime` sur la
  ligne `data_sources` SITADEL (horizon réel des données = **2026-06**) ; le bloc le lit.
- Front : `DepotsBlock.tsx` (badge « Sourcé Sitadel3 · 2026-06 », deux lignes, libellé), monté sous
  « Viabilisation et réseaux ». `tsc --noEmit` vert.
- **3 captures** : `qa/m38/deck_depots.html` (parcelle+secteur / secteur-seul / hors-couverture=null).

**P3 — Mesure à blanc (`[M38-P3]`) → recommandation : PAS de bascule**
- Reproduit la feature servie `SitadelLayer` (400 m, 60 mois, PC, saturation 15) puis redate la
  fenêtre sur le dépôt. **Rien de servi modifié.** Script `qa/m38/mesure_p3.sql`.
- Ampleur : **197 244 parcelles (50,2 %)** changeraient de magnitude, très majoritairement à la
  **baisse** (161 009 baisse / 36 235 hausse) ; **4 567** perdraient le signal de zone ; toutes
  communes touchées (Le Tampon, Saint-Denis, Saint-Paul en tête).
- Diagnostic : la redatation **dégrade** le signal au lieu de le rafraîchir —
  (1) **censure à droite** (dépôts récents en instruction non publiés : 10 916 PC déposés/60 mois vs
  12 257 autorisés/60 mois) ; (2) **16 % d'anomalies source** (5 720 PC avec dépôt postérieur à
  l'autorisation) qui produisent les fausses hausses.
- Conclusion « constater avant présumer » : le dépôt éclaire la **fiche** (P2), pas le **calcul
  servi**. Un usage servi supposerait un re-fit P (hors périmètre) + une bascule gardée type-M32
  décidée par toi — la mesure **n'incite pas** à l'ouvrir. Détail : `M38_P3_MESURE.md`.

## Vérifications (toutes vertes)

| Contrôle | Résultat |
|---|---|
| Golden (117 parcelles, base↔API) | **117/117 PASS**, 0 incohérence |
| Re-mesure M34/M35 (1 071 parcelles, verdict↔tier 2 sens) | **0 divergence — PASS** |
| Vigilances M37 — SHA256 global du dump exhaustif | **482da6f6… identique** (0 vigilance touchée) |
| Tiers changés par M38 | **0** (aucune écriture servie) |
| Tests validateur dépôt | 4/4 |
| Typecheck front | vert |

## Piste future (notée, non touchée — arbitrage Vic §1)

Le portail régional / DEAL (dépôts en instance temps-réel) reste **hors périmètre M38**. Si un jour
tu veux la vision temps-réel des dossiers en cours (le seul manque non couvrable par l'open data
Sitadel), c'est une source distincte à instruire — pas un prolongement de ce mandat.

## À toi

Rien n'est mergé ni servi. Revue visuelle du bloc via `qa/m38/deck_depots.html`. Ma recommandation
tient en une ligne : **merger P1+P2** (datation au dépôt captée + contexte fiche honnête), **ne pas
basculer** la feature servie (P3 le démontre). Commande de merge quand tu valides :
`git merge --no-ff m38-permis-deposes`.
