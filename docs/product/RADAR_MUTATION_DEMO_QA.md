# Radar Mutation — QA « démo promoteur »

> QA produit/commerciale : Radar Mutation est-il **compréhensible, vendeur, prudent juridiquement,
> prêt à montrer à un promoteur** ? Simulation réelle sur Saint-Paul. **Docs-only**, aucune donnée
> touchée. Rédigé le 2026-06-27. Base `main = 6bf9378`.

## Verdict : ✅ **GO** (prêt pour démo promoteur)

Radar Mutation est **clair, différenciant et prudent**. Le parcours 5 minutes fonctionne de bout en
bout (sidebar → calque carte → fiches → coexistence verdict/mutation). Aucun **terme interdit**,
aucune **erreur console locale**, **0 régression**, **DB inchangée**. Quelques **points de vigilance
de discours** (à couvrir par le script), **aucun bloquant produit**.

---

## Réponses aux questions de discours

| Question | Réponse | Constat |
|---|---|---|
| Compréhensible en < 30 s ? | **Oui** | score /100 + niveau + « potentiel à étudier » + raisons chiffrées |
| Vraiment différenciant ? | **Oui** | **second axe** indépendant du verdict, deux lectures croisées |
| « Pourquoi cette parcelle remonte ? » | **Oui** | raisons **chiffrées** (+30 sous-exploitation, +25 presque-seuil…) + badges |
| Ne se confond pas avec le verdict ? | **Oui** | bloc séparé, **accent violet**, libellé « **score distinct du verdict** », coexistence montrée |
| Wording sans promesse risquée ? | **Oui** | 0 terme interdit ; « potentiel à étudier », « rien n'est garanti » |
| Valeur business immédiate ? | **Oui** | shortlist priorisée → gain de temps de prospection |

## Points forts

- **Deux axes croisés** (opportunité + mutation) = argument différenciant fort et lisible.
- **Explicabilité** : chaque point de score est justifié → défendable en comité.
- **Distinction visuelle** nette (violet vs vert/orange/gris/rouge) — pas de confusion de couleur.
- **Prudence intégrée** : l'exemple `AB0492` (10 ha EPF, signal 88) affiche « Vigilance contrainte
  forte » **et** le verdict crie « PPR inondation, non constructible » → l'outil **n'embellit pas**.
- **Cas « presque opportunité »** (`AB0690`, à creuser à 1 point du seuil) = démonstration parfaite
  de la complémentarité des deux axes.

## Risques de confusion (à couvrir par le discours, non bloquants)

1. **« À creuser » + « Prioritaire 100 »** : une parcelle au verdict tiède peut être prioritaire au
   radar. C'est **le but**, mais surprend au premier regard. → **Coaché** dans le script (« deux axes
   différents »). Le libellé « score distinct du verdict » est présent.
2. **Malus non itemisé** : sur `AB0492`, la contrainte forte est signalée par le **badge** « Vigilance
   contrainte forte » (et par le verdict), mais le **− 15** n'apparaît pas comme ligne explicite (les
   raisons n'affichent que les contributions positives). → Compréhensible, mais **améliorable**.
3. **Sidebar « à surveiller »** affiche **prioritaire / forte** (pas le niveau « surveiller »). Léger
   décalage sémantique titre/contenu. → Mineur.
4. **« Foncier acquérable / acquisition facilitée »** pourrait être sur-lu comme « facile à acheter ».
   → Atténué par « à étudier » + script d'objections.

## Points à améliorer (futurs, non bloquants — hors mission docs-only)

- Afficher le **malus explicitement** dans le bloc Radar (ex. ligne « − 15 contrainte forte »).
- Ajouter le niveau **« surveiller »** à la sidebar (nécessite un pool élargi — cf. plan perf).
- Éventuel **tooltip inline** « score distinct du verdict » sur le bloc fiche.

## Tests réalisés

| Test | Résultat |
|---|---|
| `healthz` / `readyz` | 200 / 200 |
| Fiche `/mutation/{idu}` | 200 (~12 ms) |
| Sidebar `/mutation` (prioritaire) | 200 (~3 ms, caché) |
| Calque `/map/mutation.geojson` | 200 (~3,7 s froid / ~8 ms caché) |
| Calque carte : toggle, légende, clic → fiche | ✅ (cf. Phase 2E) |
| 5 fiches exemples ouvrables + bloc mutation | ✅ |
| Coexistence verdict + mutation (`CP0024`) | ✅ |
| Wording interdit (DOM rendu) | **AUCUN** |
| Erreurs console locales | **0** (tuiles CartoDB = bruit env.) |
| DB inchangée | ✅ 431 663 / 1 132 371 / 9 103 / 0 / 8 997 413 |

## Screenshots (livrés, non versionnés)

- `demo_sidebar.png` — sidebar Radar Mutation.
- `demo_ab0690_acreuser.png` — prioritaire 100 + verdict à creuser (presque-seuil).
- `demo_cp0024_coexist.png` — coexistence verdict Opportunité + Radar Prioritaire.
- `demo_dm0031_public.png` / `demo_dm0890_grande.png` — public stratégique / grande sous-exploitée.
- `demo_ab0492_contrainte.png` — signal fort **+ Vigilance contrainte forte** (PPR).
- `qa2e_map_layer.png` — calque carte violet + deux légendes distinctes.

## Recommandations avant présentation réelle

1. **Précharger** le calque carte et la sidebar **avant** la démo (1ᵉʳ calcul ~quelques secondes).
2. **Coacher** les 2 points de confusion (axes distincts ; « acquérable » ≠ « à vendre »).
3. **Ouvrir avec `AB0690`** (presque-seuil) et **finir avec `AB0492`** (prudence) — l'arc « signal
   fort mais honnête » est le plus convaincant.
4. Garder le **réseau** (fonds de carte) ; sinon basculer en fond « Plan » sobre.
5. Rappeler systématiquement : **lecture seule, données publiques, due diligence à vous**.

## Décision

> **PRÊT pour une démo promoteur.** Le produit est compréhensible, différenciant et juridiquement
> prudent. Les rares risques de confusion sont **de discours** (couverts par le pack démo) et non des
> défauts produit. Les améliorations identifiées (malus explicite, niveau « surveiller ») sont
> **mineures et futures**. **GO.**
