# M14 — LOT G : re-vérification SUR `main` MERGÉE

**But** : la preuve qui compte se prend **sur `main` après merge**, pas sur les branches isolées (c'est là que les régressions M13 étaient passées). Merge local A→F effectué (aucun push), puis recapture des 8 points sur `main`.

**Merge** : `audit/m14-a` → `b-regressions` → `c-projet-multi` → `d-recherche` → `e-sources` → `f-vocab`, tous en `--no-ff`. **Aucun conflit** (les 6 branches touchent des zones distinctes ; contrairement à M13, aucune n'embarquait une autre). Build `tsc+vite` **0 erreur**. Golden `LABUSE_DEV_MODE=1` : **116/116 PASS**.

`main` local = HEAD des 6 merges. **Rien poussé** (à la demande de Vic).

## Checklist des 8 points — vérifiés SUR `main` (captures `qa/m14/G/`)

| # | Point | Assertion sur main | Capture |
|---|---|---|---|
| ✅ | **B1** bulle « i » entière | bulle non rognée (bord droit ≤ 1440), texte complet 175 car., rendue en portal | `g_b1_bulle_i.png` |
| ✅ | **B2** icônes équip. ×1,5 | couche Équipements active, rampe `icon-size` ×1,5 en place (seule définition) | `g_b2_equipements.png` |
| ✅ | **B3** Couches ouvert défaut | `[data-couches-drawer]` présent au premier chargement | `g_b3_couches_ouvert.png` |
| ✅ | **C1** bouton Projet multi + grisé | menu « Rattacher à un projet » : **3 projets grisés « ✓ dedans »**, **3 actifs** (ajout multi possible) | `g_c1_projet_menu.png` |
| ✅ | **D1** placeholder | « Rechercher : IDU, adresse exacte, commune… » | `g_d1d2_recherche.png` |
| ✅ | **D2** barre cliquable bord à bord | clic à l'extrême droite → focus sur l'input (`data-omnibox`) | `g_d1d2_recherche.png` |
| ✅ | **E1/E2** Sources deux régimes | « vérifié il y a X » (sondable, ex. BAN « il y a 2 jours »), « Cadence producteur » (non sondable), Filosofi « millésime 2021 », **aucun « — » nu** | `g_e1_sources.png` |
| ✅ | **F1** plus aucun « v2 » | verdicts « Brûlante/Chaude » sans v2 (panneau filtre + liste + compteurs) | `g_f1_filtre_sans_v2.png` |
| ✅ | **F2** « + Chercher plus » disparu | absent de la vue Projets | `g_f2_projets.png` |

**8/8 vérifiés sur `main` mergée.** Aucun point présent sur sa branche mais absent de `main` → **aucun conflit de merge mal résolu**. La régression M13 (LOT D non mergé) ne s'est pas reproduite.

## Verdict

« Corrigé » veut bien dire **« corrigé sur ce que voit l'utilisateur »**. Golden 116/116 (dev_mode). `main` non poussée — Vic valide sur ces captures puis pousse lui-même.

Reproduire : app sur `:8050/socle/`, `node qa/m14/cap_G.mjs`.
