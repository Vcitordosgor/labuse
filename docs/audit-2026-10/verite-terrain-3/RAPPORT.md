# VERITE-TERRAIN-3 — RAPPORT

**16 octobre 2026 · LECTURE SEULE** (aucune écriture en base, aucune correction, aucun accès VPS, pas de merge).
Branche `audit/verite-terrain-3`, worktree `~/Desktop/labuse-verite3`. Livrables : `FRAICHEUR.md` (Volet A), `AFFIRMATIONS.csv` + `AFFIRMATIONS_NOTES.md` (Volet B), `ECARTS.md`, ce rapport, et 127 preuves en `cache/`.

## Verdict en 5 lignes

1. **Le cœur — les PLU des 24 communes — est à jour** : les 21 communes dotées d'un règlement ingéré servent **exactement** le document en vigueur au GPU (`idurba` servi = document GPU, octet pour octet) ; les 3 autres (Saint‑André, Saint‑Leu, Saint‑Philippe) n'ont **aucun document publié au GPU**, état attendu.
2. **Une procédure à suivre** (pas un retard) : Saint‑Leu, révision générale, enquête publique close le 09/10/2026 ; et **PPR Saint‑André approuvé le 16/04/2026** à confirmer dans la couche servie.
3. **5 sources de données en retard**, toutes secondaires : GéoLittoral érosion (~8 ans), classement sonore (~12 mois), ZNIEFF (~1 cycle), DPE (~4 sem.), BAN (~2 mois) — aucune ne touche le calcul du run.
4. **4 affirmations fausses** visibles par l'utilisateur : le nombre « 431 663 parcelles » figé (app), la fenêtre d'apprentissage du classement mal décrite (app), et sur le site vitrine « 3 000+ parcelles » et « Saint‑Paul commune pilote » (photos périmées de la phase pilote).
5. **Rien ne bloque le run de ce soir** : les faux sont du texte (front/site), indépendants du run ; les retards sont des données secondaires. Le seul contrôle utile avant le run est de **confirmer le PPR Saint‑André 2026** dans la couche risque servie.

## Volet A — Sommes‑nous à jour ? (synthèse)

| Bloc | À jour | En retard | Procédure en cours | Non vérifiable | Non traité (faute de temps) |
|---|---|---|---|---|---|
| **PLU 24 communes** | **21** | 0 | 1 (Saint‑Leu) | 2 (Saint‑André, Saint‑Philippe : GPU vide) | 0 |
| **PPR / PPRN 24 communes** | 22 | 0 | 1 (Saint‑Philippe) | 0 | 1 à confirmer (Saint‑André 2026) |
| **Autres sources servies** | ~33 | 5 | 1 (OCS GE 3e millésime) | 8 | ~40 (cf. FRAICHEUR § Non traité) |

Les 5 retards : **GéoLittoral érosion 2018 · classement sonore ITT 2023 · ZNIEFF 08/2025 · DPE ADEME · BAN** (les 2 derniers mineurs, cadence normale). Détail et preuves : `FRAICHEUR.md`.

> ⚠️ **Caveat** : base **locale** (worktree dev). La table `source_veille` date du 24/09 et marque 83 sources « injoignable » — artefact réseau du poste, **pas** la réalité prod ; donc **chaque verdict amont a été re‑sondé en direct le 16/10/2026** (ou marqué NON VÉRIFIABLE). ~40 sources n'ont pas été re‑sondées faute de temps et ne sont **pas** présumées « à jour » (listées dans FRAICHEUR § Non traité).

## Volet B — Les phrases disent‑elles vrai ? (synthèse)

39 affirmations factuelles relevées et confrontées au code / registre / jobs / base.

| Surface | Relevées | CONFORME | LABUSE_FAUX | NON_VERIFIABLE |
|---|---|---|---|---|
| app (`frontend/src`) | 26 | 18 | 5 | 3 |
| site (Astro, `~/labuse.immo`) | 9 | 1 | 4 | 4 |
| mail | 2 | 2 | 0 | 0 |
| copilote | 2 | 2 | 0 | 0 |
| **Total** | **39** | **23** | **9** | **7** |

Les 9 `LABUSE_FAUX` = **4 défauts** (B1 « 431 663 » ×3 · B2 fenêtre d'apprentissage ×2 · B3 « 3 000+ » ×2 · B4 « Saint‑Paul pilote » ×2). Tous revérifiés à la main — détail et corrections dans `ECARTS.md`.
Pièges évités (classés CONFORME après contrôle base) : aléa mvt 23 communes, VEFA neuf 60 mois/8 ventes, NPNRU 8/6, QPV 57/13, solaire 400 m, SIRENE mensuel, digest 7 h, sources « vérifiées chaque jour » (job `sonde-sources` quotidien).

## À corriger AVANT le run de ce soir

- **Contrôle unique (si une couche risque alimente le scoring/l'assiette) :** vérifier que le **PPR Saint‑André approuvé le 16/04/2026** est bien dans la couche DEAL servie. Si déjà capté par la veille 07/09 → rien à faire. *(À confirmer par l'équipe ; le worktree dev ne permet pas de recalculer le score.)*
- **Sinon : RIEN.** Aucun autre écart ne doit être « embarqué » dans le run : les 4 phrases fausses sont du texte front/site (déploiement indépendant du run), et les 5 retards de données sont des couches secondaires qui ne modifient pas le calcul servi.

## Ce qui peut attendre (après le run)

- **B1 « 431 663 »** — à faire **rapidement** après le run : le littéral **dérive encore** à chaque nouveau run scoré. Le dé‑coder‑en‑dur comme l'équipe l'a déjà fait dans `FiltreLabuse.tsx` (lire `n_parcelles_ile`).
- **B2 / B3 / B4** — corrections de texte, calmes : aligner le texte du classement sur le FREEZE ; passer le site de « 3 000+ / Saint‑Paul pilote » à « 430 000+ / 24 communes ».
- **A1–A5** — re‑ingestions de données au fil de l'eau (érosion, sonore, ZNIEFF, DPE, BAN).
- **Hors mandat** — libellé interne `sentinelle.py` « Saint‑Pierre (97410) » = en réalité Saint‑Benoît (Saint‑Pierre = 97416) ; pages mentions/CGU du site absentes (liens `#`) ; ~40 sources non re‑sondées à finir de vérifier ; slugs de veille Filosofi/IRIS/INSEE‑RP à fiabiliser.

## Portée non couverte (honnêteté)

- ~40 sources secondaires non re‑sondées en direct (listées dans FRAICHEUR), DEAL Lizmap / SUP‑PEB / Géorisques détail notamment.
- Tables de run scoré **vides** sur ce worktree dev → « 9,93 % parcelles à cheval » et le volume exact du run non recalculables ici (NON VÉRIFIABLE, pas « faux »).
- Site vitrine = one‑pager ; pas de pages légales à auditer (elles n'existent pas).
