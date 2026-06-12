# R1 « DÉJÀ BÂTI » — RAPPORT DE CORRECTION ET DE FIABILITÉ

> Correctif du défaut n°1 de l'audit (`AUDIT_COMPLET.md`) : LA BUSE classait des parcelles
> déjà construites en « opportunité », dont sa vitrine commerciale BP0571 (une résidence
> habitée vendue avec un CA indicatif de 23,5 M€). Mission exécutée de bout en bout :
> ingestion d'une couche bâtiment fiable → déclassement gradué → ré-évaluation complète →
> nouvelle vitrine → neutralisation des arguments commerciaux faux → QA.

## A. État initial (baseline reproduite avant correction)

- 197→184 tests verts (avant nouveaux tests), ruff clean, doctor ✅, healthcheck 13/13.
- **BP0571 : `opportunite`, score 77, AUCUN motif** — reproduit (snapshot JSON des 3 000
  verdicts conservé pour le diff).
- Répartition : **814 opportunités** / 1 778 à creuser / 323 faux positifs / 85 exclues.
- Bâti OSM (audit) : ≥10 % ≈ 77 % des opportunités · **≥30 % = 47 %** · ≥50 % = 16 % ;
  parcelles de démo bâties : BP0571 (résidence, prouvée à l'orthophoto), BS0009 (bâtiment
  464 m²) ; top 20 : majoritairement du bâti léger à significatif.

## B. Source bâtiment retenue

**BD TOPO IGN `BDTOPO_V3:batiment`** (Géoplateforme WFS — endpoint déjà validé au SPIKE,
même flux que la voirie). **Pourquoi pas OSM seul** : sous-cartographie mesurée à La
Réunion — BP0571 ressortait à 18 % de bâti OSM alors que l'orthophoto montre 4 immeubles ;
BD TOPO cartographie l'exhaustif IGN. OSM reste utilisé pour les ÉQUIPEMENTS
(parking/école/cimetière/sport), inchangé. Cadastre bâti Etalab : disponible en repli
(même hôte que les parcelles), non nécessaire. Orthophoto : **preuve visuelle uniquement**,
jamais moteur automatique. Confiance affichée : « haute » (BD TOPO) ; si la couche n'est
pas ingérée, la fiche dit « **occupation non vérifiée** » — jamais un faux « vacant ».

## C. Méthode de calcul

- Ingestion **paginée** (WFS 2.0 `count/startIndex` + tri stable `cleabs`) : **11 260
  bâtiments** sur l'emprise Saint-Paul en **10 s** ; `kind='batiment'` dans
  `spatial_layers` (trigger geom_2975 + GIST existants) ; job intégré à `ingest_layers`
  → **durable au rebuild-demo**.
- Par parcelle (batch SQL indexé, `labuse/bati.py::stats_batch`) : **ratio bâti**
  (Σ aires d'intersection / aire parcelle, borné à 1), **nombre de bâtiments**
  (intersection ≥ 10 m²), **surface du plus grand bâtiment**.
- La cascade est **protégée** : `kind='batiment'` exclu de la pré-computation
  (`EvalContext.prime`) — aucune couche cascade ne le lit ; le déclassement et la fiche
  font leurs requêtes ciblées. Ré-évaluation complète : **146 s** pour 3 000 parcelles
  (aucune dégradation).

## D. Règles de déclassement (graduées — mission §3 et §9)

| Ratio bâti | Code | Effet | Wording affiché |
|---|---|---|---|
| < 5 % | `vacant` | aucun | « Aucun bâti significatif détecté » |
| 5–15 % | `peu_bati` | **aucun** (vigilance résumé) | « Présence de bâti à vérifier » · « restructuration potentielle » si ≥ 5 000 m² |
| 15–30 % | `partiellement_bati` | → à creuser | « bâti significatif : X % — occupation à vérifier » |
| ≥ 30 % | `deja_bati_probable` | → faux positif | « déjà bâtie probable : X % … N bâtiment(s) (BD TOPO) » |
| ≥ 50 % | `deja_bati` | → faux positif | « déjà bâtie : N bâtiment(s) couvrant X % » |
| **≥ 3 bâtiments OU un bâtiment ≥ 400 m², dès 15 %** | `ensemble_bati` | → faux positif | « ensemble bâti : … (BD TOPO) » |

La règle **« ensemble bâti »** est la clé : les résidences gardent un ratio < 30 % à cause
des espaces communs — c'est exactement BP0571 (18 %, 4 bâtiments, max 418 m²). Le score
brut reste affiché, le motif est toujours visible, on ne remonte jamais un statut. La
fiche porte un bloc « **Occupation actuelle** » (ratio, nb, plus grand, source, confiance)
repris dans les **exports** md/html ; healthcheck : contrôle critique « Bâtiments (BD TOPO) ».

## E. Impact sur BP0571

`opportunite (77)` → **`faux_positif_probable`** · motif : **« ensemble bâti : 4 bâtiments
couvrant 18 % de la parcelle (BD TOPO) »** — cohérent avec l'orthophoto de l'audit
(`audit_shots/overlay_BP0571.jpg`). Elle n'est plus une parcelle commerciale vitrine ;
elle devient l'**exemple du correctif** dans la démo (« la résidence qui nous aurait
piégés — détectée et écartée, motif affiché »).

## F. Nouvelle parcelle vitrine : BK0023

**97415000BK0023** — opportunité 74 · **9 723 m² VACANTS (0 % bâti BD TOPO, confirmé
orthophoto : friche avec accès — `audit_shots/overlay_BK0023.jpg`)** · accès voirie < 6 m ·
prix DVF **fiable** ~5 310 €/m² (14 ventes) · CA indicatif ~32–35 M€ (médiane ~33,7 M€).
2ᵉ exemple : **BV0912** (opp 77, 3 948 m², bâti léger **7 % signalé sans déclasser** —
montre le palier anti-sur-correction). BS0009 retirée des exemples (bâtiment de 464 m²
à 14 % — limite de palier, mauvais support de démo).

## G. Impact sur le top 20

Ancien top 20 : **11/20 reclassées** (toutes avec motif bâti précis — dont BV0883 :
12 bâtiments, BS0008 : 9 bâtiments, BO0239 : 62 % bâti). **Nouveau top 20 : 0–14 % de
bâti, accès voirie < 6 m sur 20/20, aucune parcelle clairement déjà bâtie** — l'objectif
de la mission est atteint.

## H. Impact sur les 814 opportunités

**814 → 124 opportunités** (−85 %) · 940 à creuser · 1 770 faux positifs · 166 exclues.
Mouvements : 540 opp→faux positif, 150 opp→à creuser, 988 à creuser→faux positif,
81 faux positif→exclue (cumul micro+bâti). **2 068 parcelles** portent désormais un motif
bâti explicite. Ce chiffre paraît brutal mais il est **cohérent avec la réalité urbaine**
mesurée indépendamment à l'audit (47 % des opportunités ≥ 30 % de bâti OSM, OSM
sous-comptant) : l'ancien chiffre de 814 était le mensonge, pas le nouveau.

## I. Exemples avant/après (extraits du jeu de validation — 68 parcelles)

| Parcelle | Avant | Après | Motif |
|---|---|---|---|
| BP0571 | opportunité (77) | faux positif | ensemble bâti : 4 bâtiments, 18 % |
| BV0883 | opportunité (77) | faux positif | ensemble bâti : 12 bâtiments, 22 % |
| BP0194 | opportunité (75) | faux positif | déjà bâtie : 3 bâtiments, 52 % |
| BO0552 | opportunité (74) | faux positif | grand bâtiment de 641 m², 27 % |
| BK0023 | opportunité (74) | **opportunité** | — (0 % bâti) |
| BV0912 | opportunité (77) | **opportunité** | bâti léger 7 % signalé, non déclassé |
| BO0845 | faux positif (parking) | faux positif | inchangé |
| BN1351 / BH0283 | à creuser (PPR / SAR) | à creuser | inchangés |

20 ex-faux positifs : 6/20 durcis en « exclue » (micro **et** bâtie — cumul de signaux),
aucun remonté. 20 ex-à creuser : 9/20 → faux positif (bâti), 11 inchangées.

## J. Faux positifs corrigés

Le défaut R1 est corrigé **à la source de données près** : toute parcelle dont BD TOPO
couvre ≥ 30 % (ou ensemble/grand bâtiment ≥ 15 %) est écartée AVEC motif ; 15–30 % passe
en « à creuser » ; 5–15 % est signalé sans déclasser.

## K. Risques de sur-correction (assumés, mesurés)

- **124 opportunités restantes** : c'est peu — mais chaque conservée est défendable
  (0–14 % bâti, accès). Le promoteur préfère 124 vraies que 814 fausses.
- Frontière 15 % : BS0009 (14 %, bâtiment 464 m²) **échappe** à la règle ensemble-bâti à
  1 point près — elle reste opportunité avec bâti signalé. Cas limite documenté ; le
  seuil est volontairement prudent dans l'autre sens (ne pas tuer le restructurable).
- Le « renouvellement urbain » (démolition/reconstruction) n'est PAS scoré : une parcelle
  bâtie peut rester un deal pour un promoteur — le motif et le label « restructuration
  potentielle » (grande parcelle peu bâtie) préservent l'information ; un vrai mode
  « renouvellement » est une évolution produit, pas un réglage.
- Bâtiments légers (cases, annexes) BD TOPO comptés comme les autres : un terrain avec
  une case à démolir à 35 % de couverture sera « déjà bâtie probable » — c'est le prix
  de la priorité « éviter les énormes faux positifs » (mission §9, v1).

## L. Limites restantes

- BD TOPO a sa propre latence de mise à jour (constructions récentes absentes) ;
- pas de croisement avec les permis (SITADEL) pour « en cours de construction » ;
- le ratio ignore l'EMPRISE non bâtie mais imperméabilisée (cours, dalles) ;
- l'enclavement (finding O1 de l'audit) reste non corrigé — chantier suivant ;
- le bilan (coûts construction O2/O3) reste à recalibrer — chantier suivant.

## M. Tests lancés

**197 tests verts** (dont **13 nouveaux** `test_bati.py` : paliers, cas BP0571 verrouillé,
anti-sur-correction, motifs affichés, signaux batch DB, fiche honnête sans couche,
jamais-remonter) · ruff clean · doctor ✅ PRÊT · healthcheck **14/14** (nouveau contrôle
Bâtiments) · warm-demo **8/8 conformes** (nouveaux attendus : BP0571 = faux positif) ·
**16/16 exports** avec section « Occupation actuelle » et zéro vocabulaire interdit ·
ré-évaluation 3 000 parcelles en 146 s · ingestion 11 260 bâtiments en 10 s.

## N. Est-ce vendable après correction ?

**Plus crédible, oui — vendable en pilote encadré, oui.** Le défaut éliminatoire (vendre
une résidence habitée comme opportunité à 23,5 M€) est corrigé, détecté, affiché et même
retourné en argument (« l'outil détecte le déjà-bâti »). Le pack commercial ne contient
plus un seul chiffre faux (BK0023, vacante et vérifiée, partout). Restent les chantiers
2-5 de l'audit (enclavement, bilan prudent, Leaflet vendorisé, positionnement) avant de
viser plus qu'un pilote encadré. Note vendabilité : **3,5 → ~6/10** — le produit ne ment
plus sur sa promesse centrale ; il reste perfectible sur l'accès et le réalisme du bilan.

## O. Prochaine priorité recommandée

**Chantier 2 de l'audit : le signal « accès non identifié »** (O1 — 63 % des anciennes
opportunités sans voirie < 3 m ; à re-mesurer sur les 124 restantes), puis **bilan
prudent** (O2/O3 : coûts Réunion sur surface de plancher, médiane d'abord, bas borné à 0).
Ces deux-là, combinés à R1, donnent un top crédible de bout en bout : **vacant + accessible
+ chiffré prudemment**.

---
*Addendum (passe « 10/10 », même jour) : l'ajout du signal **accès non identifié**
(audit O1, seuil 6 m BD TOPO) a rétrogradé 16 opportunités enclavées supplémentaires →
**108 opportunités finales** (vacantes ET desservies), 710 parcelles portent le motif accès.
Les 8 parcelles de démo restent conformes (toutes à 0 m d'une voirie).*
