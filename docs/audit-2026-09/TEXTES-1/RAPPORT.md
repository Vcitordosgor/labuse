# TEXTES-AUDIT-1 — les phrases qui engagent

**Branche** `audit/textes-1` · worktree `~/Desktop/labuse-textes` · API 8675 / front 5875 · 2026-09-29.

Audit des textes client-facing de LABUSE appartenant à **deux familles seulement** : **JURIDIQUE**
(affirme ou résume une règle de droit) et **CHIFFRÉE** (contient un nombre écrit en dur qui engage).
Tout le reste (style, clarté, libellés, aide) est hors périmètre.

---

## 1. Chiffres clés

- **536 textes retenus** (dans le périmètre), collectés sur 7 zones. Après relecture, **48**
  requalifiés hors périmètre → **488 réellement dans le champ**.
- **~625 textes vus puis écartés** à la collecte (hors périmètre : unités seules, formats hérités,
  explications sans droit ni chiffre, boutons, CSS, commentaires de code).
- **Familles** : 393 JURIDIQUE · 182 CHIFFRÉE (39 mixtes comptés dans les deux).
- **11 corrections appliquées** (Lot C) · **1 FAUX documenté sans correction client** (PY-013).
- **3 chiffres orphelins** renvoyés à FRONT-CHIFFRES-2 · **0 chiffre divergent**.
- Livrable principal : **`JURIDIQUE-A-RELIRE.md`** — 345 affirmations, dont **49 à vrai regard juridique**.
- `tsc` 0 · `vitest` **225** vert · **V6b** vert · banc `--echantillon` **sans écart nouveau**.

## 2. Collecte (Lot A) — `TEXTES.csv`

| Zone | Fichiers | Retenus | JURIDIQUE | CHIFFRÉE |
|------|----------|--------:|----------:|---------:|
| Déclarations (fiche/commune/couches/`i`) | `declarations/**/*.yaml` | 153 | 105 | 64 |
| Documents PDF (Dossier/Flash) | `src/labuse/exports`, `flash` | 150 | 104 | 64 |
| Documents PDF (pré-dossier/blocs) | `src/labuse/api/*document*`, `pre_dossier.py` | 60 | 45 | 13 |
| Verdicts / textes réglementaires | `src/labuse/*.py` (taxe, fiscal, RNU…) | 90 | 72 | 18 |
| Front (fiche/outils/couches/contexte) | `frontend/src/components` | 41 | 29 | 12 |
| Copilote (chemin fiche) | `src/labuse/copilote_v2`, `ai` | 22 | 16 | 6 |
| Mails / courrier | `emails.py`, `courrier_compose.py`… | 20 | 16 | 4 |
| **Total** | | **536** | **393** | **182** |

Zones à contenu **hébergé hors code** (non vérifiables ici, signalées) : les 16 gabarits Brevo
(cycle de vie) vivent chez Brevo (`brevo.py` ne porte qu'IDs/params) ; la lettre au propriétaire et
les mails SMTP bruts sont, eux, dans le code.

## 3. Vérification (Lot B)

### 3.1 CHIFFRÉE — 182 textes, confrontés à la valeur servie par le back
- **44 JUSTE** (le nombre en dur = valeur servie).
- **91 LEGAL-FIXE** (constante légale/réglementaire codée à l'identique côté back et texte : TVA DOM
  8,5 %/2,1 %, seuil TCSP 800 m, CDAC 1 000 m², valeurs forfaitaires taxe d'aménagement, etc.).
- **44 NON APPLICABLE** (valeur injectée depuis une variable — pas un littéral engageant ; la
  constante back sous-jacente a tout de même été vérifiée et concorde).
- **3 ORPHELIN** → renvoyés à FRONT-CHIFFRES-2 (cf. §5).
- **0 DIVERGENT.** Aucun chiffre en dur ne contredit le back.

### 3.2 JURIDIQUE avec référence citée — 54 affirmations, 28 articles/textes, vérifiés sur Légifrance
- **44 JUSTE** · **6 FAUX** · **2 PROMESSE** · **2 NON VÉRIFIABLE**.
- Chaque référence a été lue dans sa **version en vigueur au 2026-09-29** (liens dans les CSV de vérif
  et dans `JURIDIQUE-A-RELIRE.md`).

**Les 6 FAUX :**
1. **RAP « 0,40 % de l'assiette de la taxe d'aménagement » citée sous « code du patrimoine L524-7 »**
   (`taxe_amenagement.py`). Le taux 0,40 % est en vigueur, mais depuis l'ordonnance 2022-883
   (01/09/2022) cette part est recodifiée au **CGI** (fait générateur art. 1635 quater F, gestion
   DGFiP) ; L524-7 ne porte plus que le **régime au m²** (0,69 €/m² 2026), réservé aux travaux sans
   permis. → **corrigé**. *(Les deux agents de vérif divergeaient ; tranché par lecture directe de
   L524-7 v. 01/09/2022 + note du ministère de la Culture.)*
2. **RAP au pré-dossier PC en « 0,68 €/m² »** (`pre_dossier.py`) — mauvais régime pour un permis
   (c'est le 0,40 %) et millésime 2024. → **corrigé**.
3. **Isolement acoustique attribué à R.571-32** (`pre_dossier.py`) — c'est R.571-43 + arrêté du
   30/05/1996 ; « catégorie élevée » surqualifiait. → **corrigé**.
4. **SIS « servitude OPPOSABLE aux autorisations d'urbanisme » (L125-6)** (`risques.yaml`) — L125-6
   déclenche l'obligation d'étude de sols (L556-2), il n'est pas un motif de refus. → **corrigé**.
5-6. **PEB zones C et D (L112-10)** (`constructibilite.tsx`) — libellés inversés/inexacts :
   l'isolation acoustique relève de L112-12 ; la zone C limite l'urbanisation, la zone D n'est pas une
   « zone d'information ». → **corrigés**.

**FAUX documenté sans correction client** : **PY-013** — le code cite « CGI 1635 quater E/F » pour le
secteur à taux majoré (la bonne référence est **1635 quater L/M**), mais **uniquement en commentaire
de code** ; le libellé montré au client (« Secteur à taux majoré en vigueur depuis le … ») ne cite
aucun article. Hors périmètre « texte client » — signalé pour un nettoyage de commentaire ultérieur.

**Les 2 PROMESSE :**
- **Carence SRU « programmes souvent facilités » (L302-9-1)** (`ContextePanel.tsx`) — l'article
  institue une **sanction** (prélèvement majoré, reprise préfectorale), pas une facilitation. → **reformulé**.
- **ZFANG renforcé (décret 2026-421)** (`territoire_fiscal.py`) — taux 80/100 % et échéance 2030
  attribués au décret alors qu'ils relèvent du CGI art. 44 quaterdecies (le décret ne fixe que la
  liste des communes) ; « commune de l'Est » trop large, avantage affirmé sans condition
  d'éligibilité. → **reformulé** (fait conditionné + renvoi fiscaliste).

**Les 2 NON VÉRIFIABLE :** APIDOC-011 (gabarit à variables `{zone}/{effet}` du PEB — **résolu** une
fois FRT-005/006 corrigés) ; PY-017 (décret 78-690 ZSAR + classement FRR 01/07/2024 — les deux faits
sont exacts séparément, leur combinaison au grain commune reste à confirmer — laissé, §2 du livrable).

### 3.3 JURIDIQUE sans référence citée — 347 affirmations classées
- **230 GÉNÉRIQUE-OK** (explication juridique générale correcte) · **66 FACTUEL-SERVI** (constat tiré
  des données, pas une promesse) · **48 HORS** (n'affirment finalement ni droit ni règle) · **3 DOUTEUX**.
- **0 PROMESSE inconditionnelle.** LABUSE est systématiquement prudent : réserves explicites
  (« la commune PEUT préempter », « à confirmer auprès de la commune », « ne remplace pas un
  certificat d'urbanisme »), gardes fiscales renvoyant à l'expert-comptable.
- **3 DOUTEUX** : PY-016 (ZFANG standard « de plein droit » sans réserve in-line → **reformulé**) ;
  FRT-026 (traité en PROMESSE ci-dessus) ; COP-015 (exemple de prompt imposant un nom d'élu daté) et
  MAIL-002 (« il suffit de la demander » — engagement **commercial** de gratuité) → laissés à
  l'arbitrage humain (§3 du livrable) car hors des deux familles au sens strict / texte fixe non
  reformulable sans le propriétaire du texte.

## 4. Corrections (Lot C) — 11 textes, 2 familles

**Commit 1 — FAUX / PÉRIMÉ (références)** : RAP moteur + pré-dossier (2), R.571-43 (1), SIS/L556-2
(1), PEB C/D (2), EBC L113-1+L113-2 fiche + pré-dossier (2). 
**Commit 2 — PROMESSE (reformulations conditionnées)** : ZFANG renforcé + standard (2), carence SRU (1).

Aucun calcul touché (`_RAP_PCT` reste 0.40 — c'est la **référence** qui était périmée, pas le taux).
Détail avant/après : `AVANT-APRES.md`.

## 5. Chiffres orphelins → FRONT-CHIFFRES-2

Trois littéraux sans contrepartie au registre back :
- **COP-011** — « Au moins 1 000 m² » (`copilote_v2/recap.py:52`, seuil de suggestion UI).
- **MAIL-019 / MAIL-020** — « sous 24 h ouvrées » (`ModulePanel.tsx:1534` et `:1550`, engagement de
  délai en dur, doublon).

## 6. Livrables

- **`JURIDIQUE-A-RELIRE.md`** — livrable principal, imprimable, pour urbaniste/notaire (345 lignes,
  cases à cocher, liens Légifrance ; sections 1-4 = 49 lignes de vrai travail juridique).
- `TEXTES.csv` — collecte (536 lignes, 7 colonnes).
- `AVANT-APRES.md` — captures avant/après des 11 corrections (témoins = chaînes servies).
- `fragments/` — CSV de collecte par zone + CSV de vérification (juridique référencé, sans-ref,
  chiffré) et worklists intermédiaires (traçabilité).

## 7. Limites

- Textes Brevo (16 gabarits cycle de vie) hébergés hors dépôt : non audités.
- La combinaison ZSAR/FRR au grain commune (PY-017) reste à confirmer par la source DGFiP.
- Les captures sont documentées en avant/après verbatim (tooltips générés par parcelle/commune, non
  capturables sans données porteuses de l'attribut).
