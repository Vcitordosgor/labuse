# RAPPORT M55-C — Saint-Philippe/RNU · doublon de filtres · chevron

Branche `feat/m55-c-rnu-filtres` (base `main` 9dad8079, **M55-B mergé — précondition vérifiée**).
Points 1 & 2 = **MESURE + PROPOSITION, aucun code (STOP Vic)**. Point 3 = fix front (fait).
Captures `reports/m55-c-rnu-filtres/captures/`. **CC ne merge jamais.**

---

## 1. STOP — Saint-Philippe (RNU) : que deviennent ses 4 162 parcelles ?

Mesures sur le run servi `q_v8_calibre` (INSEE cadastral 97417, commune « Saint-Philippe »,
4 162 parcelles).

### Répartition par tier
| Tier | n | % |
|------|---|---|
| Écartée (étage 0) | 1 930 | 46,4 % |
| **À creuser (servable)** | 1 493 | 35,9 % |
| Déclassée — bâti saturé | 686 | 16,5 % |
| Déclassée — bâti révélé | 51 | 1,2 % |
| **Chaude (servable)** | 2 | 0,05 % |
| Brûlante | 0 | 0 % |

**Servables (brûlante + chaude + réserve + à creuser) = 1 495 (35,9 %)** — quasi tout « à creuser ».

### Motifs d'écartement (couches HARD_EXCLUDE, une parcelle peut en cumuler)
bâti 1 023 · **forêt publique 579** · **foncier public 418** · surface 207 · parc national 165 ·
emprises linéaire/routière 109 · risques PPR 33 · pente 15. → **motifs PHYSIQUES/domaniaux**,
aucun n'est « RNU » ni « hors-PLU ».

### Le RNU déclenche-t-il une exclusion ?
**Non.** Grep de la cascade + scoring : aucune couche/motif « RNU/hors-PLU » n'exclut.
Au contraire, une **branche RNU existe déjà** (validée Vic 26/07/2026, mandat RNU) :
- `scoring/p_v2/statuts.py` : « parcelle DANS la PAU estimée (critère centre) ∧ surface ≥ seuil » → **servable** (à creuser), même sans règlement.
- `faisabilite/constructibilite.py` : hors-PLU ⇒ « **signalé, pas déclassé** ».
- `faisabilite/residuel.py` : « Zone hors PLU outillé — capacité non calculable » (pas de SDP).
- `parcel_pau` couvre **2 373 parcelles** de Saint-Philippe (57 %) — l'enveloppe urbanisée estimée par `labuse rnu-pau`.

Donc : les écartées le sont pour raisons **physiques/domaniales** (bâti, forêt/foncier public,
parc, surface), pas parce que la commune est au RNU. Les servables passent par la branche PAU.

### Anormalement bas ? Comparaison à taille voisine (communes de relief)
| Commune | parcelles | % servable | % écartée |
|---------|-----------|-----------|-----------|
| **Saint-Philippe (RNU)** | 4 162 | **35,9 %** | 46,4 % |
| Sainte-Rose | 6 287 | 8,8 % | 80,6 % |
| Entre-Deux | 6 312 | 9,1 % | 81,4 % |
| La Plaine-des-Palmistes | 6 450 | 9,1 % | 87,3 % |
| Cilaos | 6 560 | 8,6 % | 87,5 % |
| Salazie | 7 035 | 5,5 % | 93,0 % |

**Saint-Philippe n'est PAS anormalement bas — il est PLUS servable** (36 %) que toutes les communes
de relief calibrées (5-9 %). Explication : sans PLU, aucune zone A/N n'écarte les parcelles ;
la branche PAU les classe « à creuser ». Mais **presque aucun haut-tier** (2 chaude, 0 brûlante) :
sans règlement, pas de SDP → LABUSE ne PROMEUT pas (honnête) — il ne les écarte pas non plus.

### L'écran dit-il pourquoi ?
- **Fiche d'une parcelle SP** : OUI, motif lisible — « **Constructibilité au cas par cas (RNU) —
  vérifier en mairie** », « Le RNU s'applique ; aucun zonage communal servi », « Enveloppe urbanisée
  ESTIMÉE par LABUSE ». (Vérifié sur `97417000BC1159`.)
- **Toast RNU (M55-A)** : « Saint-Philippe : commune au RNU — pas de zonage PLU » — mais il ne se
  déclenche qu'en **activant une couche de zonage**, pas au simple survol de la commune noire.

### Options (à trancher — RIEN implémenté)
1. **Statu quo** — le traitement « dégradé mais honnête » que le mandat envisage EXISTE DÉJÀ
   (branche PAU + fiche RNU lisible). Aucune parcelle n'est écartée « faute de PLU ». Rien à faire.
2. **Clarté écran** (petit fix, si Vic veut) : un **bandeau RNU au niveau commune** (visible sans
   ouvrir une fiche ni toggler le zonage) — « Commune au RNU : pas de PLU opposable ; classement au
   cas par cas (art. L.111-3 s.), enveloppe urbanisée estimée ». Rend le « pourquoi » immédiat.
3. **Ne PAS** tenter de promouvoir les parcelles RNU en chaude/brûlante : cela exigerait d'inventer
   une constructibilité que LABUSE ne peut pas sourcer. Le « à creuser » est le bon plafond honnête.

**Recommandation** : option 1 (rien) + éventuellement option 2 (bandeau commune) — décision Vic.

---

## 2. STOP — deux banques de filtres

### Inventaire
**Banque A — header « + Filtre »** (`Header.tsx`, `AddFilter`). Écrit dans `filters` (store `useApp`).
Verdict/Scoring **tiers** · Déclassées (motif) · POTENTIEL ≥/100 (**scoreMin**) · SURF. CONSTR. ≥
(**sdpMin**) · SURFACE ≥/≤ (**surfaceMin/Max**) · Avec événement BODACC (**evenement**) · Veille
succession (**veille**) · Masquer copropriétés (**horsCopro**) · **flags**.

**Banque B — panneau « FiltreLabuse »** (zone Résultats, analyse active). Écrit dans le **même** `filters`.
Constructibilité calibrée (**constructibilite**) · Surface parcelle (**surfaceMin/Max**) · SDP
résiduelle (**sdpMin/sdpMax**) · Capacité logements · État du sol (**etatSol**) · « Vous cherchez ? »
(presets) · interrupteur **analyseLabuse** · Mes vues · Famille de zonage (**zonagePlu**) · Zone PLU
exacte (**zonePlu**) · Contraintes de secteur (**flags**) · tiroirs « coûte/rapporte »
(prixAchatMax, chargeFonciere, prixDVF, bilanCA, marcheFiable, sousDensite, modeBRentable),
« se vendre » (probaN, tetesP, renouvellement, divisionOr), « à qui » (proprio), « risques »
(flags), « veille & niches » (npnru, adresseAbsente, veille).

### Doublons EXACTS (même champ éditable des deux côtés)
| Champ | Header (A) | Panneau (B) |
|-------|-----------|-------------|
| `surfaceMin`/`surfaceMax` | SURFACE ≥ / ≤ | Surface parcelle |
| `sdpMin` | SURF. CONSTR. ≥ | SDP résiduelle (min) |
| `flags` | Flags actifs | Contraintes de secteur + tiroir « risques » |
| `tiers` | Verdict/Scoring + Déclassées | via presets « Vous cherchez ? » |
| `veille` | Veille succession | tiroir « Veille & niches » |

**Exclusifs A** : `scoreMin`, `evenement`, `horsCopro`.
**Exclusifs B** : `constructibilite`, `etatSol`, `sdpMax`, `capacite`, `zonagePlu`, `zonePlu`,
`analyseLabuse`, presets, Mes vues, toute l'économie, toute la vente, proprio, `npnru`,
`adresseAbsente`, curseur mode B.

### Même état ? (question de Vic)
**Oui — un seul état.** Les deux banques lisent/écrivent le **même objet `filters`** du store
`useApp` (sérialisé dans l'URL `#f=`). **Prouvé** : SURFACE ≥ = 1500 posé dans le header → URL
`#f=1&smin=1500` → le champ « Surface parcelle » (min) du panneau affiche **1500**.
→ **Aucune valeur contradictoire n'est possible** (dernière écriture gagne, reflétée partout). Le
vrai défaut n'est pas l'incohérence de données mais la **redondance d'UI** : le même réglage se pose
à deux endroits, ce qui brouille.

### Proposition (à trancher — RIEN implémenté)
La banque B (panneau) est la banque EXPERTE complète ; la banque A (header) en est un sous-ensemble
+ 3 exclusifs (scoreMin, evenement, horsCopro).
- **Option 1 (répartition claire, recommandée)** : header = **accès rapide** qui ne garde QUE le
  geste le plus fréquent (tiers/verdict) et **déplie le panneau expert** pour le reste ; retirer du
  header les doublons `surface`/`sdp`/`flags` (déjà dans B) et y **rapatrier** les 3 exclusifs A
  (scoreMin, evenement, horsCopro) → un champ = un seul endroit.
- **Option 2 (fusion)** : supprimer la banque A ; un bouton « Filtres » du header ouvre/scrolle vers
  la banque B unique.

**Invariant à garantir** : un utilisateur ne doit jamais pouvoir poser deux fois le même filtre à
deux endroits. (Aujourd'hui l'état est partagé donc pas de conflit de valeur, mais la double saisie
existe et doit disparaître.)

---

## 3. FIX — chevron de la section Couches (fait)
Chevron « Couches » harmonisé avec la croix du panneau : **boîte centrée h/w 7** (même empreinte de
clic), poids `text-base`, **même survol** (`group-hover → txt-hi`), **rotation douce**
(`transition-[transform,color] duration-soft ease-cockpit`). **3bis** : le badge « N actives »
respire (`gap-2 → gap-3`, 12 px) — zone de clic non ambiguë. Même rendu appliqué au chevron
« Verdict » de la légende (même idiome, même panneau). *(Aucune autre section repliable ne porte de
badge.)* Captures `p3_chevron_before` / `after_open` / `after_closed`.

---

## Périmètre
Points 1 & 2 : mesure et rapport SEULS, aucun code. Point 3 : front seul (`LeftPanel.tsx`,
`Legend.tsx`). Rien touché au scoring ni aux données. CC ne merge jamais.
