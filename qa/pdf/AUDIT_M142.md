# AUDIT M142 — L'argumentaire de négociation (`audit/argumentaire`)

Lecture seule, **aucune correction**. Branché sur `origin/main` @ `2005bd1c` (l'avance depuis
M141 = uniquement mon M141, hors périmètre — signalé). Ce document se pose **face à un vendeur** :
chaque chiffre est un argument qu'on nous opposera. Gravité par constat : *faux positif (cardinal)*
· *faux négatif* · *décoratif* · *dette* · *cosmétique*. CC ne merge jamais.

## Verdict en une ligne

**Dans le cas nominal, le document est cohérent, sourcé, daté et honnête de ton. Mais il
produit et présente sans garde-fou un « prix d'achat max » NÉGATIF (−4,51 M€, −824 €/m² sur
une parcelle réelle) comme chiffre-héros — indéfendable devant un vendeur. C'est le constat
cardinal. S'y ajoutent : pas de date de millésime de donnée à la M139, une exposition
non authentifiée (cohérente avec la famille des PDF parcelle publique), et une tension de
doctrine à arbitrer (un bilan à rebours est un calcul, mais son cadrage est advocatoire).**

---

## Pièce à conviction — deux exemplaires réels (texte rendu, `_synthese`/`_bilan_rebours`)

Rendu obtenu en appelant les fonctions de section directement (weasyprint absent du venv local ;
le HTML des sections, lui, est exact). Hypothèses par défaut : coût 2500 €/m², marge 21 %.

**(a) NOMINAL — `97415000CX1395` (Saint-Paul, 608 m², zone U3c, 13 ventes DVF « fiable »)** :
> « la charge foncière supportable — ce que l'opération peut payer le terrain — **s'établit entre
> 35 k€ et 195 k€ (médiane 93 k€)** … Le prix demandé (139 k€) excède ce maximum de 46 k€ (+33 %) :
> l'écart constitue la base factuelle d'une contre-proposition. »
> Bilan : `Bas 35 k€ · Médiane 93 k€ · Haut 195 k€ · Par m² terrain 153 €/m²`. Cascade : CA 1,66 M€
> − Marge&frais 349 k€ − Construction 1,17 M€ − VRD 55 k€ = Terrain 93 k€. Vigilance : classement
> sonore, QPV. **Cohérent, défendable.**

**(b) PATHOLOGIQUE — `97415000CW1073` (Saint-Paul, 5469 m², zone AU3a, 49 ventes DVF « fiable »)** :
> « la charge foncière supportable … **s'établit à −4,51 M€ en médiane (haut de fourchette −1,05 M€)** ;
> dans le scénario bas, l'opération ne supporte aucune charge foncière. »
> Bilan : `Bas −6,37 M€ · Médiane −4,51 M€ · Haut −1,05 M€ · Par m² terrain −824 €/m²`. Cause :
> Construction 18,59 M€ **> CA 18,44 M€** (l'opération est sous l'eau à ces hypothèses).
> **Le chiffre-héros et le tableau affichent des euros négatifs. → constat cardinal F1.**

---

## A — Ce que le document dit, section par section

| # | Section | Fonction | Affirme | Source de chaque chiffre | Ce qu'un vendeur conteste |
|---|---|---|---|---|---|
| 1 | Synthèse | `_synthese` (`argumentaire.py:153`) | charge foncière supportable (bas/médiane/haut), écart vs prix demandé | `calc.prix_achat_max` (compute_calculette) ; surface `parcels` | « votre médiane est négative » (F1) ; « vos hypothèses de coût/marge » |
| 2 | Marché réel | `bq.comparables` (`briques_pdf.py:596`) + `_svg_bande_points` (`argumentaire.py:74`) | Q1/médiane/Q3, effectif, période, rayon, fiabilité | `marche_service.marche_dvf`/`comparables` (DVF, rayon config, fenêtre 3 ans) | « n ventes seulement » — mais le doc le DIT (effectif affiché) |
| 3 | Ce que le terrain permet | `bq.faisabilite` (`briques_pdf.py:449`) | SDP, surface vendable, articles PLU | faisabilité (`parcel_faisabilite`, `engine.py:462`) | hauteurs/zone (audit séparé, hors périmètre) |
| 4 | Ce qui réduit la capacité | `_reductions` (`argumentaire.py:217`) | modulations chiffrables (pente, PPR, littoral, SAR) en réduction de SDP | `faisabilite.modulation` | « pourquoi ma parcelle est pénalisée » — présenté en capacité, pas en décote (doctrine OK) |
| 5 | Bilan à rebours | `_bilan_rebours` (`argumentaire.py:242`) + `_svg_cascade` | CA → −marge&frais → −construction → −VRD = terrain max | `calc.steps` (compute_calculette) | **F1** (négatif) ; le coef, les hypothèses |
| 6 | Points de vigilance | `_vigilance` (`argumentaire.py:298`) | viabilisation, risques, servitudes — SANS euros | `viab`, `rapport.risques/patrimoine` | rien (qualitatif, honnête) |
| 7 | Sources & millésimes | `_sources` (`argumentaire.py:333`) | source + millésime par ligne | `rapport.sources` | « à quelle date ? » — millésimes présents, mais pas de run servi (F2) |

---

## B — Les chiffres

### B.1 — Le bilan à rebours, terme à terme
Moteur = `compute_calculette` (`faisabilite/bilan.py:657` → `compute_bilan`). Le calcul : `CA =
shab_vendable × prix_sortie` ; `coef_CA = 1 − (marge% + honoraires% + frais%)/100` (`bilan.py:523`) ;
`terrain = CA × coef_CA − construction − VRD`. Hypothèses **saisies** : `cout_construction_m2`,
`marge_frais_pct`, `prix_demande_eur`. Constantes et provenance :

| Terme | Provenance | Verdict |
|---|---|---|
| `coef_rendement` SDP↔vendable **0.80** (`bilan.py:491`) | **config YAML** (`hypotheses_ile.yaml:14`, par commune) | sourcé ✓ (pas un dur) |
| coût construction €/m² | `bilan_params` secteur / YAML / **saisi** | sourcé/saisi ✓ |
| VRD base €/m² | `bilan_params`/YAML `cout_vrd_base_m2` | sourcé ✓ |
| seuil pente majoration VRD **15 %** (`bilan.py:500`) | **en dur** | seuil physique, non arbitraire — **cosmétique** |
| honoraires / frais / marge % | `bilan_params`, défauts YAML | sourcé/saisi ✓ |
| TVA | **aucune constante** (avertissement texte seul) | ✓ |

Aucune constante €/m² fabriquée : tout vient de la config à source unique ou de la saisie. Le seul
« dur » est le seuil de pente 15 % (physique). **RAS majeur** ici.

### B.2 — La SDP consommée & les dates — **F2 (dette)**
`shab_vendable_m2` vient de la **faisabilité live** (`parcel_faisabilite` → `engine.py:462`), pas
d'une lecture datée de `parcel_residuel`. Le PDF **porte une date d'édition** (`date.today()`,
`briques_pdf.py:132`, dans la garde) + la **période DVF** (fenêtre 3 ans) + les **millésimes**
(section 7). Il n'est donc **pas « non daté »**. **Mais** il ne porte **pas** la seconde date façon
M139 lot 2 (« valeurs au JJ/MM, run N »). Généré à la demande et estampillé du jour, l'écart est
moindre que pour un projet figé — mais aligner sur M139 fermerait l'ambiguïté « ces chiffres
datent-ils de l'édition ou d'un run plus ancien ? ». **Gravité : dette.**

### B.3 — Le coefficient de circulation (M133) — **pas de divergence, la promesse tient**
`Fiche.tsx:851` affirme « l'argumentaire PDF reprend LES MÊMES hypothèses que la calculette ».
**Toujours vrai après M133.** Argumentaire (`argumentaire.py:57`) et calculette de la fiche
(`modules.py:1064`) appellent **le même `compute_calculette`** avec le **même `coef_rendement 0.80`**
(config) — égalité stricte attestée par `tests/test_bilan.py:232`. Le coefficient que M133 a rendu
éditable (`coef_circulation = 1.20`, `modules.py:1195/1209/1222`) est **utile→SDP** (le « besoin »
d'un programme, `POST /programme`) — **un autre coefficient, dans l'autre sens, jamais dans le
chemin argumentaire**. Donc rien à réparer sur cet axe.

**Constat CONNEXE (hors périmètre argumentaire, signalé) — dette** : deux coefficients utile→SDP
codés en dur et **non alignés** — `PROGRAMME_CIRCULATION_COEF = 1.20` (`modules.py:1195`, M133) vs
`M22_CIRCULATION = 1.15` (`projet_schema.py:34`, cadrage projet/copilote M120), le second portant un
commentaire (`projet_schema.py:32`) qui les dit **faussement alignés** (« +15 % comme
faisabilite_sens2 » — périmé). N'affecte pas l'argumentaire ; à traiter côté cadrage projet.

### B.4 — Les comparables de prix — **RAS**
`bq.comparables` (`briques_pdf.py:596-632`) affiche **Ventes (effectif), Période, Fiabilité,
rayon adaptatif** + `reserve_methode()` + `effectif_suffisant`. `_svg_bande_points` exige **≥ 5
points** (`argumentaire.py:78`) et écrit « (N ventes) — aucune vente n'est fabriquée ni lissée ».
Source unique `marche_service` (rayon config, fenêtre 3 ans, `nature ILIKE 'vente%'`, bâti ≥ 20 m²).
**Le document dit son effectif, son rayon, sa fenêtre.** Un nuage de 3 points ne s'affiche pas
(seuil 5). ✓

### B.5 — Sourcé / Estimé — **cosmétique (SVG cascade)**
Cartouches étiquetées (`· Estimé` / `· Sourcé` / `· saisi` / `· dérivé`) ; tableau bilan avec
colonne **Nature** (S/E). `_svg_bande_points` : sourcé DVF, dit dans la note. **`_svg_cascade` : les
valeurs (dérivées, Estimé) ne portent pas d'étiquette DANS le SVG** — la note renvoie au tableau
(« mêmes termes … aucun recalcul »), qui, lui, est étiqueté. Écart mineur. **Gravité : cosmétique.**

### B.6 — `_vigilance` : absence vs panne — **RAS (honnête)**
Le silence est **qualifié** : « Aucun élément dans les couches numérisées — ce constat ne vaut pas
absence de contrainte (seul l'ingéré est vérifié) » (`argumentaire.py:328`). Idem `_reductions`
(`:236`). La différence absence/non-testé est explicitement dite. ✓

---

## C — La doctrine et sa tension

### C.1 — Grep rang/score — **propre**
Aucun `rang_v2`/`q_score`/`a_score`/`opportunity_score`/probabilité-de-mutation dans
`argumentaire.py`, dans les deux SVG, ni dans le payload de la route. `bq.score_e_affiche`
(`briques_pdf.py:348`) est lu **uniquement** pour `prix_probable` (garde-fou 2×, `argumentaire.py:274`) ;
son `niveau_prix`/`marge` ne sont **pas** rendus. `garde_fou_signal` (`marche_service.py:117`) ne
sort qu'un **ratio factuel** (« ×N.N … Pas une opportunité chiffrée »), aucun rang. **Point à noter
(décoratif)** : `_vigilance` affiche « Indicateur de viabilisation **X/100** » (`argumentaire.py:309`) —
un score /100 dans l'export ; c'est un indicateur d'infrastructure sourcé, **pas** le rang de mutation
interdit, mais c'est la seule forme « scorée » du document. **Gravité : décoratif** (à connaître).

### C.2 — La tension, nommée (arbitrage Vic)
Le bilan à rebours est **techniquement un calcul** : charge foncière supportable = fonction
déterministe de (SDP faisabilité × prix DVF) − coûts − marge, tous saisis ou sourcés, étiquetée
**Estimé**. Ce **n'est pas** le rang/tier/score interne que la doctrine M133 B.6 interdit (il ne
classe pas la parcelle contre les autres ; il calcule une capacité financière absolue).
**Mais** son **cadrage est advocatoire** : la synthèse écrit « l'écart constitue la **base factuelle
d'une contre-proposition** » et sert le chiffre en **héros à 2 mètres**. Un calcul mis au service
d'une négociation produit, de fait, un nombre qui dit *ce terrain vaut au plus X*. Frontière
calcul/verdict : **le nombre est un calcul, sa mise en scène est un argument.** Le cas F1 (négatif)
durcit la tension : quand le calcul dérape (−4,51 M€), ce n'est ni un calcul défendable ni un
verdict — c'est un nombre cassé servi proprement. **Constat posé ; la décision revient à Vic.**

### C.3 — Libellés — **propre**
Le bandeau `LIBELLE` (`argumentaire.py:35`) est honnête : « estimation indicative, ni un prix ni une
promesse ; ne vaut pas conseil ». Le prix d'achat max est « · Estimé ». **Aucun « officiel »** ni
sur-promesse (contraste avec la faute M141). ✓

---

## D — L'exposition

### D.1 — Authentification & cloison — **non authentifiée, non cloisonnée (posture, pas outlier) — dette**
La route (`argumentaire.py:369`) n'appelle que `porte_export(request, db)` (quota) — **jamais**
`current_compte`. `porte_export` (`quota.py:62`) : **sans session → passe** (fail-open « pilote »,
`quota.py:69`) ; avec session, ne compte qu'un quota par compte appelant, **aucun contrôle de l'IDU**.
`idu: str` **non validé** (`argumentaire.py:370`), énumérable. `_charger_marque` : sans session →
PDF non marqué (pas de fuite inter-tenant). **Un anonyme obtient le PDF ; un compte A peut tirer la
parcelle « de » B** — mais c'est **cohérent avec toute la famille des PDF parcelle publique**
(`dossier.py:64`, `banquier.py:282`, `lettre_zonage.py:310`, `pre_dossier.py:752` — tous passent
anonymes, tous non scopés), doctrine `tenant.py:24` (« les données publiques ne sont jamais
scopées »). Seuls `/projets/{pid}/export.{pdf,csv}` sont cloisonnés (`_projet_or_404`, 404
inter-compte). **Ce n'est donc pas un IDOR-bug isolé mais une posture** ; le vrai point : le quota
(30/j) est **contournable en ne s'authentifiant pas**, et l'argumentaire est le plus sensible de la
famille (contenu économique, contre-offre). **Gravité : dette** (à arbitrer : cette porte-là
mérite-t-elle une session, vu son contenu ?).

### D.2 — Bornes des paramètres — **partiellement (lié à F1)**
Les trois Query sont **bornés** (FastAPI 422 hors bande) : `prix_demande_eur ∈ [0 ; 500 M]`,
`cout_construction_m2 ∈ [500 ; 8000]`, `marge_frais_pct ∈ [0 ; 60]`. Un coût 0 ou une marge
négative → **422** (rejetés). **Mais aucun contrôle inter-champ ni de cohérence du RÉSULTAT** : la
question du mandat — « le document sort-il quand même avec des chiffres absurdes présentés
proprement ? » — **est réalisée par F1** : des hypothèses valides (2500/21 % par défaut) sur une
parcelle réelle produisent un « prix d'achat max » de **−4,51 M€** rendu proprement. `idu` reste non
borné (surface d'énumération). **Gravité : voir F1 (cardinal).**

---

## E — Le câblage front (décision de visibilité — évidence, sans rien retirer)

**Deux chemins seulement** vers `/argumentaire/{idu}.pdf** (grep front exhaustif) :
1. **Bouton fiche** — `Fiche.tsx:853`, `<a href="/argumentaire/{idu}.pdf?cout…&marge…&prix…">
   Éditer l'argumentaire de négociation (PDF)</a>`, **conditionnel** (`mode==='achat_max' && calculable`).
2. **Copilote** — `ReponseInline.tsx:9-12` (`docUrl(kind,idu) → /${kind}/${idu}.pdf`) rendu quand le
   backend peuple `v2.document` (`ReponseInline.tsx:105`).

**Le Copilote sert-il l'argumentaire de lui-même ?** **Non — sur demande explicite.** Le backend
(`copilote_v2/answering.py:785`) mappe les phrases « argumentaire / argument de négociation … » →
document `argumentaire` ; il n'y a **pas de chip de suggestion proactive** (front : agent confirme
aucun `data-recap-suggestion` argumentaire ; back : l'intent « préparer un argumentaire »
`answering.py:558` prépare un **script**, distinct du document, `router.py:91`).

**Que casse chaque option de visibilité :**
- **Retirer le seul bouton fiche** (`Fiche.tsx:853`) : la route reste, le **Copilote continue de le
  servir** sur demande (chemin 2 intact). Invisibilité **partielle**.
- **Fermer la route** : le bouton fiche **et** le lien Copilote (`ReponseInline.tsx:106`, `docUrl`)
  deviennent des **404 au clic**. Pour éviter un lien mort côté Copilote, il faudrait aussi cesser de
  peupler `v2.document.kind='argumentaire'` (`answering.py:785`). Invisibilité **complète** mais
  touche deux endroits.

---

## F — Verdict franc

**Utilisable tel quel ?** Dans le cas nominal (majoritaire) : **oui** — cohérent, sourcé, daté
(édition), doctrine-propre à l'export, ton montrable au vendeur, écart de négociation factuel. C'est
un vrai livrable.

**Se retourne-t-il contre son porteur ?** **Oui, sur un cas réel non marginal** : dès que
construction + marge ≥ CA (grandes parcelles, zones AU, prix de sortie bas), le « prix d'achat max »
devient **négatif** et s'affiche en héros (**−4,51 M€, −824 €/m²** sur `97415000CW1073`). Posé sur la
table d'un vendeur, ce chiffre **détruit la crédibilité de tout le document**. Le garde-fou C3
(`argumentaire.py:173`, `cf['bas']<=0`) ne protège que la **prose du scénario bas** ; il laisse
passer la médiane et le haut négatifs dans le héros et le tableau.

**Améliorations, valeur/coût :**
- **(cardinal / faible) F1** — plancher à 0 sur TOUTE la fourchette quand `central<=0` : remplacer le
  chiffre négatif par « l'opération ne supporte aucune charge foncière à ces hypothèses », comme le
  fait déjà partiellement la prose. Ferme le seul défaut indéfendable. **Priorité 1.**
- **(fort / faible) F2** — porter la seconde date façon M139 (« valeurs au JJ/MM, run N ») en pied de
  synthèse ou section 7.
- **(moyen / faible)** — étiqueter Estimé les valeurs du SVG cascade (B.5).
- **(à arbitrer) D.1** — décider si cette porte (contenu économique) doit exiger une session, ou
  rester dans la posture pilote-ouverte de la famille.
- **(hors périmètre) B.3-connexe** — aligner `M22_CIRCULATION` (1.15) sur `PROGRAMME_CIRCULATION_COEF`
  (1.20) ou corriger le commentaire faussement « aligné ».

**Défauts (à réparer) vs manques (à construire) :** F1 est un **défaut** (le garde-fou existe, il est
incomplet) — réparable en une condition. F2 et l'étiquette SVG sont des **défauts** mineurs.
L'exposition D.1 est un **choix de posture**, pas un défaut. Aucun pan n'est un gadget : le moteur
(bilan à rebours = calculette, testé) est solide ; c'est sa **présentation aux bornes** (négatif) et
sa **datation de millésime** qui le fragilisent face à un vendeur.

---

## Tableau des constats

| # | Constat | `fichier:ligne` | Gravité |
|---|---|---|---|
| **F1** | « Prix d'achat max » NÉGATIF (médiane/haut) rendu en héros + tableau (−4,51 M€, −824 €/m² sur une parcelle réelle) ; garde-fou C3 ne couvre que la prose du bas | `argumentaire.py:173-179,186,260-266` | **faux positif (cardinal)** |
| F2 | Pas de « valeurs au JJ/MM (run N) » façon M139 (édition datée, mais pas le millésime de donnée) | `argumentaire.py:333` · `briques_pdf.py:132` | dette |
| F3 | Valeurs du SVG cascade non étiquetées Sourcé/Estimé dans le SVG (le tableau l'est) | `argumentaire.py:103-148` | cosmétique |
| F4 | Route non authentifiée + non cloisonnée, IDU énumérable, quota contournable sans session (mais cohérent avec la famille PDF parcelle publique) | `argumentaire.py:369-379` · `quota.py:62-78` · `tenant.py:24` | dette |
| F5 | Indicateur de viabilisation « X/100 » — seule forme scorée de l'export (indicateur factuel, pas rang de mutation) | `argumentaire.py:309` | décoratif |
| — | Tension calcul vs verdict : le nombre est un calcul, sa mise en scène est advocatoire — **arbitrage Vic** | `argumentaire.py:180-196` | (constat, pas un défaut) |
| — | Bonus hors périmètre : `M22_CIRCULATION 1.15` vs `PROGRAMME_CIRCULATION_COEF 1.20`, commentaire faussement aligné | `projet_schema.py:32-34` · `modules.py:1195` | dette |
| — | Argumentaire == calculette (coef 0.80, testé) — la promesse `Fiche.tsx:851` tient après M133 | `bilan.py:491` · `test_bilan.py:232` | ✓ conforme |
| — | Comparables : effectif/période/rayon/fiabilité dits ; SVG ≥ 5 pts | `briques_pdf.py:596-632` · `argumentaire.py:78` | ✓ conforme |
| — | Doctrine : 0 rang/score/proba servi ; libellés honnêtes, aucun « officiel » | grep `argumentaire.py` | ✓ conforme |

---

*Fin d'audit. Aucune ligne corrigée. Push `audit/argumentaire`. Vic arbitre le mandat de correction
(F1 en priorité) et la décision de visibilité (E). CC ne merge jamais.*
