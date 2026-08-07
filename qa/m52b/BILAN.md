# M52-B — Sélecteur de profil à l'activation de l'analyse (dernier geste de code)

**Branche** `m52b-selecteur-profil` (base main post-M52). **PRÉSENTATION / UX SEULE — 0 tier, 0 calcul,
0 endpoint nouveau.** Pré-applique des filtres qui EXISTENT DÉJÀ. Commité + poussé, **jamais mergé**.

## Contexte (décision Vic 07/08)
La recherche « année de construction » est close : BDNB ne couvre pas le 974, fichiers fonciers
Cerema restreints, DPE 974 non obligatoire avant 2028 → **donnée inexistante à l'échelle**. La ligne
« ABSENTE » de la section « Les données » reste telle quelle. À la place : un sélecteur de profil pour
que le promoteur qui **accepte le bâti** ne perde aucune opportunité — sans jamais inventer la donnée
manquante.

## Le geste livré
À l'activation de « Afficher l'analyse LABUSE », un sélecteur léger **« Vous cherchez ? »** apparaît en
tête du panneau (`FiltreLabuse`) : **Terrain nu · Bâti (réhab / démolition) · Les deux** (défaut : Les deux).

| Profil | Filtres EXISTANTS pré-appliqués | Étiquette |
|---|---|---|
| **Terrain nu** | `etatSol = [nu]`, `modeBRentable = false` | — |
| **Bâti** | `etatSol = [bati_marginal, bati_sature, bati_revele]`, `modeBRentable = true` | « trié par **signal d'activité** — performance non mesurée séparément (le backtest couvre le classement principal) » |
| **Les deux** (défaut) | `etatSol = []`, `modeBRentable = false` | — |

- **Zéro calcul, zéro endpoint** : le clic ne fait que `setFilters(...)` sur deux champs qui existaient
  déjà (état du sol + mode B rentable) ; le compteur SQL `/filtre` des deux voies se recale tout seul.
- **Bâti = tri par signal, DIT honnêtement** : le segment bâti est servi par le MÊME tri (le classement,
  `rang`/×N par défaut) ; le backtest ne le valide pas séparément → on l'affiche. Cohérent avec la mention
  Renouvellement M48 : les occupées gardent leur motif, jamais masquées.
- **Choix mémorisé en session, re-cliquable (chips visibles, pas un tunnel)** : la puce active est
  **DÉRIVÉE de l'état réel des filtres** (jamais un état fantôme) → toujours cohérente avec le compteur
  « Retenues par l'analyse ». Si l'utilisateur affine l'état du sol à la main hors des 3 combinaisons,
  aucune puce n'est allumée — on ne ment pas sur le périmètre.

## Micro-correction consignée (règle Lot D audit RR : jamais la fausse précision)
Encart « qualité commune » : **« île 6.73 » → « île ~6,7 »**. La valeur brute (`6.73`) reste en config
(`config/qualite_commune.yaml`) et dans le payload (`rr_ile`) ; un champ d'affichage additif `rr_ile_dit`
(« ~6,7 », une décimale, virgule FR, tilde d'approximation) est servi et utilisé par la fiche + le libellé.

## Fichiers touchés
- `src/labuse/api/app.py` — `_qualite_commune` : `rr_ile_dit` (affichage ~X,Y), utilisé dans le libellé. **Additif.**
- `frontend/src/lib/types.ts` — `QualiteCommune.rr_ile_dit?`.
- `frontend/src/components/fiche/Fiche.tsx` — affiche `rr_ile_dit ?? rr_ile`.
- `frontend/src/components/panel/FiltreLabuse.tsx` — composant `ProfilSelecteur` + insertion en tête de carte.

## Vérification
- **`tsc --noEmit` : vert** (0 erreur).
- **`npm run build` : OK** (dist régénéré, servi par l'API sur `/socle/`).
- **Golden : 117/117 PASS, 0 FAIL, 0 incohérence base↔API** (API courante sur :8010, run servi `q_v8_calibre`).
  Les champs figés par le golden (`tier_v2`, `motif`, `matrice_statut`, `score_v2.verbal`, `pourquoi`,
  effectifs des 5 tiers) sont **inchangés** → 0 tier, 0 calcul prouvé. `qualite_commune` n'est pas capté
  par le golden : la micro-correction ne le fait pas bouger (aucune régénération nécessaire).
- **Backend `_qualite_commune('97420')` → `rr_ile: 6.73 | rr_ile_dit: ~6,7`**, libellé « … — île ~6,7. ».

## Captures (`qa/m52b/captures/`) — écran réel, méthode reproductible
`capture_profil.mjs` : `/socle/` → clic `[data-verdict-on]` → sélecteur `[data-profil-selecteur]` →
clic de chaque `[data-profil]` → screenshot sélecteur + panneau résultats.
- `M52B_selecteur_defaut.png` — arrivée = **Les deux** actif (défaut).
- `M52B_selecteur_{les_deux,terrain_nu,bati}.png` — les 3 puces ; **bâti** montre l'étiquette honnête.
- `M52B_liste_les_deux.png` — compteur **77 308**, aucune puce d'état du sol active.
- `M52B_liste_terrain_nu.png` — état du sol **Nu** allumé (pré-appliqué).
- `M52B_liste_bati.png` — état du sol **Bâti marginal/saturé/révélé** allumés + étiquette bâti.

GOTCHA Playwright (déjà consigné M52) : 1.62 sans build Darwin 22 arm64 → `executablePath` sur
`chromium_headless_shell-1228` du cache. API : `dbname=labuse` (rôle `labuse` absent), `LABUSE_DEV_MODE=1`
(sinon score_v2 premium/verbal absents). Le sélecteur ne s'affiche qu'en **mode verdict** (analyse allumée).

**Pas de merge** — commité + poussé, la main reste à Vic.
