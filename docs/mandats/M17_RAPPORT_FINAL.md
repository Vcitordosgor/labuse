# M17 — RAPPORT DE VAGUE : millésimes sources & veilles en langage naturel

Autonome. **CC ne merge pas.** Une branche par lot, poussée. Filet `avant-m17` (sur `main` af82da7).
Golden **116/116** (`LABUSE_DEV_MODE=1`) par lot. Modèle P **gelé**. Règle : **jamais inventer une donnée
absente** — millésime « non tracé » honnête, veille non déclenchable refusée.

---

## 1. TABLEAU DES MILLÉSIMES (LOT A)

Étend la map `MILLESIME_VERIFIE` (modèle existant DVF/Filosofi) avec les millésimes RÉELS retrouvés dans
`seed_sources.py`. Rapport détaillé : `docs/mandats/M17_LOT_A.md`.

| Source | Trouvé ? | Où | Valeur affichée |
|---|---|---|---|
| Parc National de La Réunion (INPN) | ✅ | `seed_sources.py:94-95` jeu `pnrun_2021` | **millésime 2021** |
| QPV 2024 (ANCT) | ✅ | `:217` décret 2023-1314, en vigueur 01/01/2024 | **génération 2024** |
| Classement sonore ITT (Cerema) | ✅ | `:199` arrêtés préfectoraux 14-15/12/2023 | **arrêtés déc. 2023** |
| 50 pas géométriques (DEAL) | ✅ (lignée) | `:193` cadastre 1877, géoréf. 2012/1950 | **cadastre 1877 (géoréf. 2012/1950)** |
| DEAL — trait de côte | ✅ | `:272` fichier `…_062018_shape.zip` | **millésime 2018** |
| **BPE INSEE** | ❌ introuvable | `:164` A_FAIRE, « import millésime » sans année | *laissé « non tracé »* |
| **Zonage SAFER (DAAF)** | ❌ introuvable | `:108` proxy `RPG.LATEST` non daté | *laissé « non tracé »* |

Déjà propres : DVF, Filosofi 2021, + toutes les sources à `derniere_donnee` (BD ORTHO/LiDAR/SITADEL/BODACC/DPE…
affichent « données jusqu'au … ») et à année-dans-le-nom (repli regex existant). Écartés volontairement :
BAN 2020 / IGN 2021 / INPI 2024 (dates de **licence**, pas de donnée) ; RP Logement 2023 vs `RP2022_logemt.zip`
(**doute → non modifié**).

---

## 2. PREUVES PAR POINT

| Lot | Point | Preuve |
|---|---|---|
| **A** | 5 millésimes affichés, 19 « non tracé » honnêtes, aucun « — » nu, zéro année inventée | `qa/m17/A/sources_millesimes.png` |
| **B1/B2** | « parcelles à Saint-Paul qui deviennent chaudes » → résumé + chips visibles (Chaude + commune) + nom pré-rempli | `qa/m17/B/b1_nl_traduit.png` |
| **B4** | « + Veille » → enregistrée (0→1) ; hash `tv=chaude&cs=Saint-Paul` honoré par le matcher | `qa/m17/B/b2_veille_enregistree.png` |
| **B3** | « préviens-moi si le PLU change » → refus honnête, rien enregistré | `qa/m17/B/b3_refus_honnete.png` |

Golden 116/116 sur A et B.

---

## 3. TEXTES PRODUITS (relecture Vic)

**Millésimes ajoutés** — voir tableau §1 (chacun sourcé au fichier:ligne).

**Résumé de veille NL (exemple)** — « ✓ Alerte quand une parcelle devient chaude, à Saint-Paul. —
vérifiez/ajustez les filtres, puis « + Veille ». »

**Refus — changement de PLU/zonage** — « Cette veille n'est pas encore possible : on ne sait pas détecter
un changement de PLU / de zonage. Aujourd'hui, une veille vous alerte quand une parcelle bascule (devient
plus chaude), éventuellement filtrée par commune, surface, score, SDP ou procédure BODACC. Reformulez vers
l'un de ces déclencheurs — ex. « les grandes parcelles à Saint-Paul qui deviennent chaudes ». »

**Refus — permis abandonné** — « … on ne sait pas détecter l'abandon ou l'annulation d'un permis (on ne
détecte que l'APPARITION d'un permis). … »

**Refus — hors sujet** — « Je n'ai pas su en tirer une veille déclenchable. … »

**Placeholder du champ NL** — « Décrivez : « les grandes parcelles à Saint-Paul qui deviennent chaudes » ».

---

## 4. DÉCISIONS OUVERTES / À FAIRE CÔTÉ VIC

- **BPE INSEE** : retrouver le nom du fichier BPE ingéré d'origine (INSEE nomme `bpe23…`/`bpe21…` avec
  l'année de campagne) — introuvable dans le code. À vérifier dans les fichiers sources.
- **SAFER** : accès conventionné/manuel jamais daté proprement → restera « non tracé » sans date fiable.
- **INSEE RP Logement 2023 vs RP2022** : lever l'ambiguïté nom (2023) / fichier (`RP2022_logemt.zip`).
- **Veille NL en stub** (dev sans clé IA) : extraction basique ; la brique réelle enrichit sans changer le
  contrat (le garde-fou déclenchable est **côté serveur**, identique dans les deux modes).

---

## 5. NON FAIT / BLOQUÉ

- **Radar 48 h** : hors périmètre (infra VPS, cron serveur) — non touché, comme demandé.
- **Millésimes réellement introuvables** (BPE, SAFER, RP2022/2023) : laissés « non tracé » — jamais
  devinés (boussole).
- **Déclencheurs non détectables** (changement de PLU, permis abandonné, prix, DPE) : refusés proprement
  côté veille NL, jamais enregistrés en silence.

---

## 6. BRANCHES ET ORDRE DE MERGE

Toutes **poussées, non mergées**. A et B **indépendants** (ordre libre).

```
fix/m17-a-millesimes      (frontend : map millésimes)
feat/m17-b-veilles-nl     (back : /events/veille-nl + matcher tv/cs ; front : champ NL)
docs/m17-rapport          (ce rapport)
```

Aucun conflit croisé attendu (A = `SourcesPage.tsx` ; B = `events.py` + `Header.tsx` + `api.ts`).

**LOT C** (re-vérification sur `main` mergée) : à exécuter **après** le merge Vic — reboot, recapture
Sources (millésimes / non-tracé), veille NL (phrase → filtres + enregistrement · refus honnête), chips M16
toujours OK, golden 116/116.
