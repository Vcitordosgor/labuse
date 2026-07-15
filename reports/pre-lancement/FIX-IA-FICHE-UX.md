# FIX IA-FICHE UX — peaufinage Surface A

**Branche** : `feat/fix-ia-fiche-ux` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**3 commits séparés**. Front + petit backend (liste blanche `/ask` + `CONTEXT_VERSION`). Points 6, 18, 15.
Base : `main` (fix-cosmetique mergé). **Zéro touche scoring/cascade/étage 0/run.**

| # | Commit | Item | Fichiers |
|---|---|---|---|
| A | `aa16eb9` | Barre IA repliable (6) | `AskBar.tsx` |
| B | `038f208` | Retirer le vieux bouton « IA » (18) | `Fiche.tsx` |
| C | `374621e` | Exemples enrichis + aménités (15) | `AskBar.tsx`, `fiche_ask.py`, `core.py` |

---

## FIX A — Barre IA repliable (point 6)
**Problème** : la barre IA était **toujours dépliée** (champ + 5 chips) → elle mangeait la moitié de l'écran et repoussait adresse/tier/onglets tout en bas.
**Fix** (enveloppe UX, moteur `/ask` inchangé) :
- **REPLIÉE par défaut**, et à **chaque changement de fiche** (`useEffect` sur `idu` : `setOpen(false)` + `ask.reset()`) → il ne reste qu'un **bouton découvrable** « ✦ Demander à l'IA · PREMIUM · une question sur cette parcelle → ».
- Clic → **DÉPLIÉE** (champ + exemples + réponse). **« ✕ fermer »** (toujours présent en tête, y compris après réponse) → **repliée**, rend toute la fiche.
**Preuve — 3 états** :
- `fixIA-replie.png` : **la fiche est pleinement visible** (IDU, adresse, tier « Chaude v2 rang 1838 ×4.5 », onglets, score, cascade, boutons) — l'IA = une ligne.
- `fixIA-deplie.png` / `fixIA-apres-reponse.png` : champ + chips + réponse + « ✕ fermer ».

## FIX B — Retirer le vieux bouton « IA » (point 18)
**Problème** : bouton « IA » en bas de fiche (panneau `IAPanel` Synthèse / Pourquoi ce score) redondant avec la barre repliable.
**Fix** : retiré proprement — bouton + `IAPanel` + état `iaOpen` + imports `iaSynthese`/`iaPourquoi` devenus inutiles. Aucune fonction perdue (les questions passent par la barre ; « pourquoi ce score » reste dans l'onglet Synthèse / le bloc Score V).
**Preuve** : `fixIA-replie.png` — la barre d'actions montre PDF / Dossier / 1950 / Cadastre / Maps, **plus de bouton IA**.

## FIX C — Exemples enrichis + « équipements à proximité » (point 15)
**Backend** : `_ask_context` gagne le champ **`amenites`** (distances OSM au plus proche — école / santé / commerce / transports en commun, table `parcel_amenites`), étiqueté **SOURCE**. `CONTEXT_VERSION` **3→4** (le cache de fiche se régénère au format courant — évite de resservir l'ancien format). La réponse reste sourcée (ou « absent » si pas de donnée).
**Front** : chips **curés à 6**, tous groundés sur la liste blanche :
1. **Y a-t-il des équipements à proximité ?** (l'ajout — `amenites`)
2. Combien je peux construire ? (`faisabilite`)
3. C'est raccordé à l'assainissement ? (`viabilisation_*`)
4. Des ventes récentes dans le secteur ? (`dvf_*`)
5. Y a-t-il un risque inondation ? (`risques`)
6. Pourquoi ce statut ? (`statut_tier` / `motif_exclusion`)
`SRC_LABEL` gagne `amenites` (« équipements à proximité (OSM) ») + `dvf_derniere_mutation`.
> « Qui est le propriétaire ? » n'est **pas** ajouté : l'identité propriétaire (personne morale) n'est pas dans la liste blanche `/ask` — répondrait « absent » à tort. À faire dans un lot dédié si Vic le veut (avec la garde privacy).

**Preuve (live, EL0387)** : « Y a-t-il des équipements à proximité ? » →
> « L'école est à **919 m**, les services de santé à **1 070 m**, le commerce à **1 210 m**, et surtout les transports en commun à seulement **507 m**… »
avec l'étiquette **« Sourcé · équipements à proximité (OSM) »** (capture `fixIA-apres-reponse.png`). Tous les chiffres viennent du fait `amenites`.

---

## Non-régression Surface A (prouvée)
- « Combien je peux construire ? » → réponse sourcée (faisabilite / zone_plu / reglement_regles…), **provenance intacte** (SOURCE/ESTIME).
- « Amiante ? » → **rejeté / « absent »** honnête (« information non disponible de façon sourcée »).
- Grounding, validation des chiffres (couche 2), quota, cache, étiquettes de provenance : **inchangés** (seule la liste blanche gagne un champ + l'enveloppe UX change).
- `tsc --noEmit` vert. Périmètre : 4 fichiers (`git diff` = AskBar.tsx, Fiche.tsx, fiche_ask.py, core.py) — **aucun fichier scoring/cascade/étage 0/engine**.

*3 commits séparés sur `feat/fix-ia-fiche-ux`. Pas de merge.*
