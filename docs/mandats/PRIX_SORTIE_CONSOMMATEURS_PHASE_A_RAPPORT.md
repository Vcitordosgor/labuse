
---

# APPLICATION (phases B/C, 28/07/2026) — routage + démotion + bilan partagé

**Exécuté** sur `feat/prix-sortie-consommateurs` (base `origin/main` porteur de la phase C, vérifié).
GO Vic après mesure. **Golden 116/116, tiers au bit près avant/après ; 105 tests verts ; revue
visuelle des 2 PDF validée. Branche poussée sur origin pour merge Vic (jamais de merge par Fable).**

## 19 · Démotion des 4 (→ 5) overrides de bassin

Les 4 overrides « sourcés » (Saint-Gilles 5 800, La Saline 6 000, Plateau Caillou 3 500, La Plaine
3 400) + Le Guillaume → **`is_placeholder=true`, HORS préséance** : `bilan_calibration.py` (estimee) +
**migration boot ciblée** (`models.py`, provenance sourcee → estimee, un override re-saisi survit) +
DB. Motif : « observatoire de l'existant, non confirmé par DVF neuf — en attente de confirmation ».
`resolve_prix_neuf_marche` n'honorant que `sourcee`, ces bassins ne priment plus → parcelles sur le
DVF (secteur local / commune 4 730 / repli île). **Les 81 reverse flips disparaissent** (Plateau
Caillou → 4 730, mesuré). **RÈGLE DE PRÉSÉANCE GRAVÉE** (au code) : un override de bassin ne prime
sur la médiane communale DVF que s'il est fondé sur du DVF NEUF de marché ≥ N_MIN. Limite connue
écrite : 4 730 peut sur-évaluer les Hauts (~3 400-3 800) ; levée = confirmation DVF neuf.

## 20 · Un seul chemin : `resolve_prix_sortie_servi` + `compute_bilan_servi`

- **`resolve_prix_sortie_servi`** (bilan.py) : prix de sortie neuf par préséance, 4 niveaux d'étiquette.
- **`compute_bilan_servi`** (bilan.py) : LE bilan servi UNIQUE (même capacité, hypothèses résolues,
  prix neuf, contexte éco) → **charge cohérente à l'euro** entre fiche, Banquier, Argumentaire,
  Rapport de potentiel. Le cœur (db.py) est refactoré dessus (source unique, plus de dérive).
- **6 sites faux routés** (Copilote `moteurs:385`, Rapport `modules:815`, Explication `modules:943`,
  Banquier+Argumentaire `briques_pdf:244`, calculette `modules:875` + `app:2089`). `sector_price`
  conservé pour les **comparables / bloc marché** (usage légitime : valeur de l'existant).
- **4 étiquettes + non-filtrage** étendus : commune social-dominante → mention SERVIE (« non
  calculable — collectif majoritairement social ou aidé »), parcelle/dossier **jamais écarté**.

## 21 · Revue visuelle des 2 PDF (discipline O12/M26-B)

- **Commune couverte (Saint-Denis)** : bilan au prix neuf **4 275**, charge **cohérente à l'euro
  avec la fiche** (mesuré : fiche == Banquier sur 4 cas). Correction attrapée par la revue : la
  synthèse et le bloc marché étiquetaient le `sector_price` existant (2 922) « prix de sortie » →
  relabellisés **« comparables DVF (existant) »**, + fait explicite « prix de sortie neuf retenu ».
- **Commune non couverte (Le Port, social-dominant)** : **dossier généré (7 pages)**, section bilan
  ET synthèse servent la **mention** (« charge foncière de marché non calculable — le collectif y
  est majoritairement social ou aidé »), **aucun chiffre de charge**.

## 22 · Gates & contrôle de sortie

Golden 116/116 + tiers au bit près (120/1031/3587/72980/353945) avant/après. Consommateurs = lecture
seule sur `parcel_p_score_v2` (aucune écriture, tiers non affectés) ; score_e déjà sur le bon
instrument, non touché. 105 tests verts (3 verrous MAJ + mock resolve Copilote). **CONTRÔLE DE
SORTIE (leçon Vic)** : la démotion des bassins n'est ACQUISE que lorsque cette branche est mergée
sur `origin/main` — sinon le boot ré-injecte les bassins en `sourcee`. Branche **poussée** ; merge
Vic requis pour clore.

## Artefacts

`/tmp/banquier2_couverte.pdf`, `/tmp/bq_nc.pdf` (revue visuelle). Golden/tiers dans `/tmp`.
