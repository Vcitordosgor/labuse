# Audit — les 156 « petites opportunités » 251–500 m² (Saint-Paul)

> **Cadre.** Audit **lecture seule**, demandé avant démo promoteur. **Aucun verdict modifié**, aucune
> donnée touchée. Objectif : décider si ces parcelles doivent **rester « opportunité »**, **passer à
> « à creuser »**, ou être **taguées « micro-opportunité »**. Chiffres calculés sur les **156**
> (pas d'échantillon) au 2026-06-20, état post-LOT 2.

## 1. Pourquoi 251 m² comme plancher ?

Le déclassement métier (`scoring/declassement.py`) downgrade déjà toute parcelle **< 250 m²** en
« à creuser » (`SURFACE_MIN_M2 = 250`). **0 opportunité** existe sous 250 m². Les 156 forment donc la
**tranche la plus basse** des 524 opportunités de Saint-Paul (251–500 m²), soit **30 %** d'entre elles.

## 2. Profil des 156 (réparti)

| Dimension | Constat |
|---|---|
| **Surface** | médiane ~350 m² · 1 à 251 m² · 37 ≤ 300 m² · 119 entre 301 et 500 m² |
| **Score d'opportunité** | min 65 · **moyenne 67** · max 78 · **144/156 entre 65 et 69** (juste au-dessus du seuil 65), 12 ≥ 70 |
| **Complétude** | **92/100 pour les 156** (bande « forte ») — données **complètes**, ce ne sont PAS des cas « à creuser faute d'info |
| **Zonage** | **139 en U** + **17 en AUc** — **100 % en zone constructible**, aucune en A/N |
| **Bâti (BD TOPO)** | 121 vacantes (< 5 %) · 35 légères (5–15 %) · **0 ≥ 15 %** · ratio moyen **3 %** → **libre** |
| **Accès voirie** | **155/156 à ≤ 6 m** d'une voirie (moyenne 2 m) · 1 seule à 6 m → **desservies** |

➡️ **Sur le papier, elles sont « propres »** : bien zonées, documentées, libres, accessibles. C'est
pour ça que le score franchit 65. **Le problème n'est pas la qualité du terrain — c'est la taille.**

## 3. Ce que révèle la FAISABILITÉ (le point clé)

La surface est petite : après **reculs + emprise au sol**, la **surface de plancher constructible
(SDP) fond**, et l'économie devient souvent marginale.

| Indicateur (sur les 156) | Valeur |
|---|---|
| Constructibles | 140 (90 %) — 16 ne dégagent rien après reculs |
| **SDP de plancher** | médiane **150 m²** · **< 50 m² : 11 %** · **< 100 m² : 23 %** · ≥ 300 m² : 9 % |
| **Charge foncière médiane** | **≤ 0 € : 39 %** · 0–50 k€ : 4 % · ≥ 50 k€ : 58 % · médiane **100 k€** |

**Lecture :** distribution **bimodale**. Environ **58 %** sont de **vraies petites opérations**
(charge foncière médiane 100 k€, zone U, libre, desservie) ; environ **39 %** ont une **charge
foncière négative** standalone (l'opération détruit de la valeur) et **~1 sur 9** a une SDP < 50 m²
(pas d'opération du tout). **Le score d'opportunité voit le terrain ; il ne voit pas que le bilan ne
passe pas.**

### Exemples réels (4 parcelles représentatives)

| IDU | Surface | Zone | SDP | Charge foncière médiane | Score | Lecture |
|---|---|---|---|---|---|---|
| 97415000DE1325 | 346 m² | U2c | ~137 m² | **+182 k€** | 78 | vraie micro-opération |
| 97415000HI0126 | 251 m² | U2c | ~41 m² | +38 k€ | 66 | limite (SDP minime) |
| 97415000AW1723 | 500 m² | U4b | ~358 m² | **−7 k€** | 67 | ne pencil pas standalone |
| 97415000EP0871 | 350 m² | U5b | ~29 m² | **−14 k€** | 65 | reculs mangent la parcelle |

## 4. Doivent-elles rester « opportunité » ?

**Ni tout garder à l'identique, ni tout downgrader.**

- ❌ **Tout passer à « à creuser »** : injuste pour les ~58 % qui sont de vraies (petites) opérations
  bien notées — on cacherait des leads réels.
- ❌ **Monter `SURFACE_MIN_M2` à 400/500** : downgrade aveugle qui sacrifie les parcelles viables.
- ✅ **Distinguer par la taille (affichage) ET par l'économie (verdict).** Voir §5.

## 5. Recommandation (proposée — NON appliquée)

### Option A — immédiate, NON risquée (aucun changement de verdict) ⭐ recommandée pour la démo
**Taguer « micro-opportunité » les opportunités ≤ 500 m²** (badge d'affichage, basé sur la **surface**,
factuel). La parcelle **reste « opportunité »** ; le badge **pose l'attente** (« petit tènement —
souvent à assembler ») et **oriente vers l'assemblage** (LA BUSE détecte déjà les contiguës). Effet
démo : on assume la petite taille au lieu de la masquer → **crédibilité**. *Réalisable sans toucher au
scoring ; à valider car cela change la présentation de la liste « opportunités ».*

### Option B — exacte, à VALIDER (change des verdicts)
**Déclasser en « à creuser » les opportunités dont le bilan ne passe pas** : charge foncière médiane
**≤ 0** **ou** SDP **< 50 m²**. C'est le **vrai** discriminant (économie, pas surface) ; il viserait
les ~39 % non viables sans pénaliser les 58 % valables. **Coût technique** : le bilan est aujourd'hui
calculé **à la fiche**, pas dans la cascade → il faudrait remonter un indicateur de viabilité dans le
scoring. **Touche la logique de verdict → validation requise avant toute implémentation.**

### Dans tous les cas
- **Pousser l'assemblage** sur cette tranche : une parcelle de 300 m² seule passe rarement ; assemblée
  à 1–2 voisines, elle devient une opération viable. C'est le bon réflexe métier pour les 251–500 m².

## 6. Décision attendue de Vic

1. Applique-t-on **Option A** (badge « micro-opportunité » ≤ 500 m², sans changer les verdicts) ? 
2. Veut-on instruire **Option B** (déclassement économique, change des verdicts) — séparément, après validation ?

---

*Audit lecture seule. 0 verdict modifié, 0 donnée touchée, 0 autre commune. Chiffres reproductibles via
`scripts`/SQL sur la base Saint-Paul au 2026-06-20.*
