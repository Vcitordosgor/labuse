# RAPPORT DE RECETTE — RADAR P4/P5/P6 (veille, cycle de vie, marché)

Branche `feat/radar-p456` (depuis main incluant P0+P2+P1+P3). Commits par lot D1→D4. **Dernier mandat du
Radar.** Doctrines §2 tenues : collecte 100 % humaine · zéro republication · Sourcé/Estimé/Absent ·
Radar hors scoring. Réutilise l'existant (veille, envoyer_mail, event_log, DVF, registre) sans le réécrire.

---

## D1 — Veille Radar + les deux digests (P4) — **FAIT**

**Veille branchée sur le mécanisme existant** : type `radar` dans la table `veilles` (colonne `criteria`
jsonb ajoutée, type épargné du désactivage), **hors `evaluer_toutes`** (c'est le digest Radar qui
l'évalue → aucun double-envoi). `pige/veille.py` (creer/lister/supprimer + `matche`) + endpoints
`/radar/veille`. Le client crée ses critères (commune, type, surface min, particulier only) — bouton
« Être alerté sur ces critères » dans l'écran client.

**Les DEUX envois distincts, fin de journée (heure Réunion)** — `pige/digests.py`, CLI `radar-digests` :
(a) **digest quotidien** à tous les clients actifs (nouveautés du jour) · (b) **alerte veille** aux
critères correspondants. Un client concerné reçoit **LES DEUX**. **Jamais un mail vide** (pas de
nouveautés → pas d'envoi ; pas de match → pas d'alerte). Contenu = **faits + lien FICHE LABUSE**
(`/socle/#idu=…` ou `#m=radar`), **jamais un lien portail** (le clic passe par la fiche, mesurable).
**Échec BRUYANT** : un envoi raté (template Brevo 12 non monté) est logué + posé en **cloche système**
visible au dashboard (souvenir RV-013), jamais silencieux. `pige.digest_envoye` en miroir.
Template Brevo `radar` (clé `LABUSE_BREVO_TPL_RADAR` = ID 12), variables du rapport P1. Verrou 4/4.

## D2 — Cycle de vie automatisé (P5) — **FAIT**

`pige/cycle.py`, jobs heure Réunion, CLI `radar-cycle-{quotidien,dvf,mensuel}` :
- **quotidien** : `en_vente_longue` (> 90 j publication) · `a_reverifier` (> 60 j sans confirmation).
- **à chaque ingestion DVF** : `vendue` — **rattachement SOURCÉ uniquement** + mutation DVF « Vente »
  dans [3 ; 18] mois après publication → enregistre **délai** + **écart prix affiché/acté** (servi
  seulement sur Sourcé, garanti par le WHERE ; un Estimé n'est JAMAIS rapproché).
- **mensuel** : `retiree_sans_vente` — la cible Courrier.
**GARDE CRITIQUE gravée** : `retiree_sans_vente` ne se déduit JAMAIS d'un lien mort (un lien mort =
`retiree`). Seule l'absence de mutation DVF sous 12 mois, sur un bien RATTACHÉ, qualifie — testé (un
Estimé/non-rattaché ou une parcelle avec vente DVF n'est pas qualifié). Chaque bascule → `pige.statut_change`
(+ `pige.vendue_dvf`). Rien ne se supprime. Jobs déclarés dans `EXPLOITATION-CRON.md`. Verrou 4/4.

## D3 — Onglet « Marché » (P6) — **FAIT**

`pige/marche.py` + endpoint `/radar/marche` : 24 communes + **total île recalculé** (pas une somme de
médianes) — annonces actives · nouvelles/30 j · retirées/30 j · vendues DVF/90 j · **prix médian €/m²
terrain & bâti** · délai médian · taux d'échec · part particuliers. **HONNÊTETÉ STATISTIQUE gravée** :
chaque MESURE porte son `n` ; **`n < 5` → « échantillon insuffisant »** (valeur `null`, aucun chiffre) ;
les COMPTES restent des faits bruts. React `RadarMarche.tsx` (onglet Marché dans l'outil Radar) : tableau
+ mini-heatmap (intensité mint par activité) + **état de démarrage DIGNE** (« le corpus se constitue »,
pas un tableau de tirets). Couleurs source unique, **zéro mauve**. Verrou 3/3.

## D4 — Exploitation et recette — **FAIT**

**Radar au registre des sources** (`seed_sources.py`, `Radar (pige d'annonces)`, manuel, cadence
quotidien) — **fraîcheur = dernière COLLECTE** (`max(date_saisie)` de `pige_annonces`, `pige.enregistrer_fraicheur()`,
posée à chaque dépôt), **jamais une date de run**. Verrou 2/2.
**Note d'exploitation** : le rituel Radar quotidien (≤ 15 min) en ~10 gestes dans `docs/EXPLOITATION.md`.

**Recette** : corpus [RADAR-TEST] représentatif (tous statuts, avec/sans baisse, Sourcé/Estimé/non
rattachés, plusieurs communes/dates) → jobs éprouvés + cellules Marché remplies. **Purge vérifiée SQL**
(`pige_biens`=0, `pige_annonces`=0, `pige_clics`=0).
**Cas prouvés** (tests + captures) : bascule en vente longue · bascule à re-vérifier · rapprochement DVF
avec écart (Sourcé) · absence de rapprochement sur un Estimé · qualification `retiree_sans_vente` (+ garde
lien mort) · digest quotidien · alerte veille séparée · **aucun mail quand il n'y a rien** · cellule
Marché `n < 5` insuffisante · onglet Marché quasi vide (démarrage).

**Captures livrées : 6** (`docs/PIGE/captures/`) — onglet Marché **rempli** (`radar-marche-plein-{d,m}.png`)
ET **démarrage** (`radar-marche-demarrage-{d,m}.png`), et le **mail rendu** (`radar-mail-{d,m}.png`,
aperçu fidèle du contenu du template Brevo 12 : faits + « Voir sur LABUSE » vers la fiche, jamais le
portail), en **1440 et 390**.

---

## RECETTE (FIN)
- Veille branchée sur le mécanisme existant · **deux envois distincts, jamais de mail vide, échec
  bruyant** · **aucun lien portail dans les mails** ✓.
- `retiree_sans_vente` **jamais déduit d'un lien mort** · écart de prix affiché **seulement sur Sourcé** ✓.
- **n affiché partout, « échantillon insuffisant » sous 5** ✓ · jobs déclarés et testés ✓ · **Radar au
  registre des sources** (fraîcheur = dernière collecte) ✓ · Radar hors scoring ✓.
- **Le test anti-requêtes-portails de P0 reste VERT** (`test_pige_socle.py` 5/5) ✓ · couleurs source
  unique, zéro mauve ✓.
- **tsc 0 · build ✓** · **suite au niveau base (worktree `bcd74e81`)** : base 1902 / branche 1916,
  **0 fail** ✓ · **[RADAR-TEST] purgés (vérifié SQL)** ✓.

Findings : —
