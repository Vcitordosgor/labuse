# M130-7 — Purge du verdict, keep-together complet, cohérence étage 0 ↔ multi-zones

Branche `feat/m130-pdf-projet`. Ne pas merger.
`git branch` = `feat/m130-pdf-projet` · `git log -1` (départ) = `c70f47ab` ·
`lsof -ti:8000 | xargs kill -9` = serveur dev tué (rendu régénéré via le script D).
PDF régénérés **par `qa/m130/generer_pdf_qa.py`** : `M130-7-projet-{P1..P4}.pdf`
(pids 73–76).

---

## A — La phrase étage 0 ne porte plus de verdict

Plus aucun statut interne, ni « probable », ni « avant évaluation » (faux : le
statut est *dans* `dryrun_parcel_evaluations`, donc après évaluation). Contrôle :
0 occurrence de « faux positif / probable / exclue / avant évaluation / run de
scoring » dans P3.

**Phrase étage 0 rendue, mot pour mot** (P3) :

> Cette sélection est intégralement composée de parcelles que le moteur a écartées
> de son vivier exploitable. Elles n'ont pas vocation à être instruites en l'état
> — voir toutefois les parcelles multi-zones ci-dessous.

L'incise « — voir toutefois … » n'apparaît que si au moins une parcelle écartée
garde une part constructible (cf. §C).

---

## B — Keep-together : la ligne multi-zones fait partie du bloc

La hauteur du bloc est mesurée ligne par ligne avec les retours à la ligne réels
(`multi_cell(dry_run=True, output="HEIGHT")`), y compris la ligne multi-zones (2–3
lignes). Saut de page AVANT le bloc s'il déborde → aucune veuve.

- **P1 `97415000DK1044` tient sur une seule page : OUI** (bloc entier en page 7,
  ligne multi-zones « AU3c ~ 94 % · A ~ 6 % — SDP calculée … » comprise).
- Lignes multi-zones à 3 parts (les plus longues) vérifiées entières :
  `97422000BT0467` (Ua 45 · Nco 35 · Uav 20) et `97422000DH0771` (1AUb 91 · 2AUb 6
  · autres 3). Contrôle automatique : aucune page de P1/P2 ne commence par une
  veuve (« instruire », « séparément », « constructible »…).

---

## C — Étage 0 et multi-zones ne se contredisent plus

1. L'en-tête reconnaît l'exception (incise §A).
2. Une parcelle écartée qui garde une part constructible le dit sur sa ligne
   multi-zones, comme exception au constat d'ensemble.

**`97416000CX1483` rendu :**

> Parcelle multi-zones : A (agricole) ~ 58 % · Uf (urbaine) ~ 42 % — **écartée du
> vivier, mais une part Uf (~ 42 %) est constructible : à instruire séparément.**

Idem pour `HY0897` (Ug ~ 72 %) et `HY0902` (Ug ~ 89 %), qui portaient auparavant le
texte contradictoire « la SDP n'est pas chiffrée ».

**P3 — parcelles étage 0 à part constructible ≥ 5 % : 51.**

---

## D — Le sélecteur de variante teste l'ÉTAT du résiduel, jamais la famille

`_sdp_calcul_nul(it)` remplace l'ancien test `cause ∈ CASE3 ET zone dominante
non-A/N`. Il capte désormais aussi le **résiduel nul SANS cause** (cas de
`HY0897`/`HY0902` : Ug urbaine, `sdp = 0`, `cause = NULL`) — que la ligne SDP
affiche déjà « résiduel nul après reculs et emprises ».

**Bascules cas 2 → cas 3 après correctif, par projet : P1 = 0 · P2 = 0 · P3 = 0.**

Explication : les seuls blocs nouvellement détectés « résiduel calculé nul »
(`HY0897`/`HY0902`) sont à l'**étage 0** → interceptés en amont par l'exception
§C (transition cas 2 → **exception**, plus juste que cas 3). Aucune parcelle
**hors étage 0** de ces trois shortlists n'est un « résiduel nul sans cause »
multi-zones. Le sélecteur est néanmoins désormais correct (fondé sur l'état du
résiduel), et se déclenchera pour de tels blocs s'il en apparaît.

---

## E — Finitions

- **E.1** `97422000AE0619` : « aucune (**capacité annulée par les modulations :
  risque / pente / servitude**) » — plus de parenthèse imbriquée.
- **E.2** `97422000AD1237` : **1 zone intersectée** (mono-zone) → la ligne
  multi-zones est légitimement absente, ce n'est pas une omission.

---

## F — Consigné (non traité)

- **F.3** `97422000AD1237` : `status = a_creuser` alors qu'elle est en **2AUd**
  fermée à l'urbanisation → divergence cascade / zonage, ajoutée à
  `qa/m130/DETTE_CADRAGE_ETAGE_0.md` (mandat app).

ruff : 0 erreur nouvelle (I001 restantes = imports pré-existants décalés ; script
QA : `All checks passed`).
