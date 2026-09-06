# AUDIT PRÉPARATOIRE M22 — 3 nouveaux exports PDF

*Lecture seule. Aucun code produit, aucune modification fonctionnelle. Base : `main` 8feea8b (26/07/2026).*

M22 vise à créer 3 nouveaux exports PDF :
- **Argumentaire de négociation** (promoteur) — contre-estimation d'un prix demandé
- **Rapport de potentiel** (agence) — divisibilité, SDP restante, risques avant compromis
- **Lettre de vérification de zonage** — document court, opposable, citant les articles

**Verdict d'ensemble.** Les 3 exports sont réalistes, mais chacun a un socle différent. La *Lettre de zonage* est quasi gratuite (données déjà là). Le *Rapport de potentiel* est solide (divisibilité + SDP résiduelle déjà calculées) mais bute sur un signal gardé fermé. L'*Argumentaire de négociation* est le plus lourd : il faut construire **une inversion de la calculette qui n'existe pas encore** et assumer que plusieurs décotes resteront qualitatives.

---

## 1. GÉNÉRATEUR — factorisable, mais deux moteurs coexistent

Il y a **deux moteurs PDF** dans l'app, pas un.

| Moteur | Fichiers | Exports servis |
|---|---|---|
| **FPDF2** (Python pur) | `api/pdf_premium.py`, `api/pdf_projet.py` | Fiche parcelle, Fiche projet |
| **WeasyPrint** (HTML/Jinja→PDF) | `flash/report.py`, `api/dossier.py`, `api/banquier.py`, `api/division_review.py` | Flash, Dossier, Banquier, Dossier de revue |

Le partage est déjà réel, pas du copier-coller :

- **Socle commun** `api/export_commun.py` : pied de page (`pied_de_page_pdf`), disclaimer CU, adresses BAN, attribution sources — vérité unique utilisée par tous.
- **Flash = Dossier** : le Dossier n'est **pas** du code dupliqué, il appelle le même `render_report_html()` en changeant deux paramètres (`produit`, `produit_sous_titre`). Parité prouvée dans `docs/mandats/M20_C_PARITE_DOSSIER.md`.
- Palette, fontes OFL, carte IGN (`flash/carte.build_situation_map`) : réutilisées partout.

**Pour les 3 nouveaux templates M22 → route WeasyPrint recommandée.** Coût estimé : ~300 lignes neuves par template (HTML+CSS), **zéro redondance** sur données/carte/pied/disclaimer. C'est le chemin qu'ont pris Flash→Dossier.

⚠️ **Point de vigilance.** Le Dossier Banquier (`banquier.py`, 543 l.) est le seul avec **CSS et sections HTML inline**, sans template externe. C'est justement l'export le plus proche de deux des trois M22 (Argumentaire promoteur, Rapport de potentiel : bilan, comparables, faisabilité, risques). Deux options :
- copier le pattern banquier (rapide mais on duplique 6 fonctions `_cover/_identite/_faisabilite/_bilan/_comparables/_risques`) ;
- ou d'abord **extraire ces sections en briques réutilisables** — investissement M22 qui paie sur 3 templates.

**Conclusion : factorisable, oui. Mais M22 devrait budgéter un petit refactoring des sections banquier en amont, sinon on triplique le HTML inline.**

---

## 2. DIVISIBILITÉ — signal géométrique solide, réglementaire absent

Le signal existe : **« Division en or » (O12)**, dans `src/labuse/ingestion/division_or.py`, table `division_or_candidates`.

Il repose sur une **détection 100 % géométrique** (requête SQL 1-passe, `division_or.py:46-79`), tous critères cumulatifs :

| Critère | Seuil | Source donnée |
|---|---|---|
| Surface parcelle | 1 000–6 000 m² | cadastre |
| Ratio bâti | 8–45 % | BD TOPO bâti |
| Lot détachable (résiduel) | 500 m² ≤ résiduel ≤ (surface − 400) | `ST_Difference` |
| Largeur du lot (cercle inscrit) | rayon ≥ 9 m (~18 m utiles, rejette les lanières) | `ST_MaximumInscribedCircle` |
| Façade voirie du lot | ≥ 12 m (accès indépendant) | BD TOPO voirie + `ST_DWithin` |

**Ce qu'on sait affirmer aujourd'hui** : divisibilité **géométrique** — parcelle assez grande, pas trop bâtie, lot détachable de bonne forme avec accès voirie. Robuste et performant.

**Ce qui MANQUE — important pour un « Rapport de potentiel » vendu à une agence :**

- ❌ **Surface minimale par zone : n'existe PAS.** Les PLU calibrés (`config/plu_*.yaml`) ne contiennent aucun champ « surface/lot minimum ». Ils codent reculs, hauteur, emprise %, stationnement, pleine terre — pas de seuil de surface. Le `assemblage_min_surface_m2: 1000` est un seuil d'assemblage (Lot C), **pas** une taille minimale de lot réglementaire. → *on ne peut pas dire « ce lot respecte la taille minimale de la zone », cette contrainte n'est pas modélisée.*
- ❌ **Constructibilité réglementaire du lot détaché** : reculs exacts, prospect, servitudes non cartographiées → confiés à revue humaine.
- ❌ **Accès voirie du lot BÂTI restant** : métrique automatique invalidée (artefacts de frontière découpée), jugée visuellement.
- ⚠️ **Statut actuel : `EXPOSE = False`** — signal masqué en attendant la validation visuelle de 20 cartes par Vic (dossier `docs/mandats/O12_DIVISION_OR_REVUE.pdf`). **M22 ne peut pas publier de « Rapport de potentiel » basé dessus tant que cette revue n'est pas faite** — ce serait exposer un signal explicitement gardé fermé.

**Façade/largeur** : oui, largeur de façade voirie disponible (BD TOPO, `faisabilite/db.py:134-172`, seuil desserte 25 m, fallback par classe de voie). **Accès voirie** : détecté (3 mécanismes : cascade, faisabilité, division). **Forme** : cercle inscrit uniquement (suffit à rejeter les lanières, pas d'indice de compacité).

---

## 3. CONTRE-ESTIMATION — comparables solides, décotes inégales

**DVF comparables : CHIFFRABLE, et bien fait.** `faisabilite/bilan.py:155-221` (`sector_price`) : rayons adaptatifs 500→1000→1500 m→commune, rejet d'aberrants (Tukey IQR), min 8 ventes, indice de fiabilité (fiable/fragile/insuffisant selon récence < 3 ans, dispersion Q3/Q1 < 2, type, rayon), éclatement neuf(VEFA)/ancien. Retour €/m² médian + quartiles. C'est le socle sain de l'argumentaire.

**Les décotes — vérité, séparée nette :**

| Décote | Statut | Détail |
|---|---|---|
| **Pente** | ✅ CHIFFRABLE | `engine.py:329-335` : ≥30 % → ×0,4 (−60 % capacité) ; 15-30 % → ×0,7 (−30 %) |
| **PPR (aléa)** | ✅ CHIFFRABLE | fort → ×0,0 (inconstructible) ; moyen → ×0,6 ; faible → ×0,85 |
| **Littoral / bande côtière** | ✅ CHIFFRABLE | ×0,0 |
| **Emplacement réservé** | ✅ CHIFFRABLE | surface déduite de l'emprise |
| **Pleine terre %** | ✅ CHIFFRABLE si connu | réduit la capacité |
| **Défiscalisation (revente)** | ✅ CHIFFRABLE | `defisc_fenetres.py` : médiane revente/achat neuf (ex. ~87 %), sourcé DVF, n≥10 |
| **Servitudes (hors PPR)** | ❌ QUALITATIF | signalé, pas chiffré |
| **Risques : mvt terrain, inondation, cavités, pollution** | ❌ QUALITATIF | « à étudier / coût dépollution à déterminer » |
| **Viabilisation / raccordement réseaux** | ❌ QUALITATIF (par doctrine) | `viabilisation.py` : indicateur 0-100 (confirmée/probable/incertaine/lourde) mais **jamais un coût en €** — un test (`test_viabilisation.py:76`) vérifie explicitement l'absence de « € ». Seul un coût VRD **forfaitaire** global existe (90 €/m² terrain), non modulé par le contexte. |

**Nuance capitale à assumer dans M22.** Ce que l'app chiffre, ce sont des **modulations de capacité constructible** (pente/PPR réduisent la SDP vendable donc la charge foncière supportable), **pas des « décotes au prix affiché du terrain »**. L'argument reste valide et robuste (« le foncier vaut moins car je peux vendre moins de m² »), mais c'est un raisonnement **par la charge foncière supportable**, pas une décote directe sur le prix demandé. L'Argumentaire de négociation doit être construit sur cette logique — pas sur une addition de pourcentages de décote.

**Il n'y a pas d'objet « décote » unifié** — mais une chaîne de réductions composables déjà en place, réutilisable à condition de l'assembler proprement.

---

## 4. CHARGE FONCIÈRE MAX ADMISSIBLE — l'inversion n'existe PAS

**Réponse nette : NON, pas au sens « prix de sortie → foncier max ».** C'est le manque n°1 de M22.

La calculette M15-C2 (`bilan.py:461-512` `compute_calculette`, exposée `POST /faisabilite/{idu}/charge`, réutilisée telle quelle par la fiche M19) tourne :

- **Sens forward (principal)** : coût construction + marge + SDP vendable + prix DVF → **charge foncière supportable** (fourchette bas/central/haut). Le bilan à rebours promoteur complet existe et est tracé ligne à ligne (`bilan.py:376-405`).
- **Sens « achat » (le seul reverse actuel)** : si on fournit `prix_demande_eur`, elle rend un **verdict booléen** (supportable oui/non) + l'écart € — elle **compare** un prix demandé à la charge calculée.

Ce qui **n'existe pas** : *« à quel prix MAX puis-je acheter ce terrain pour que l'opération tienne ? »*

Bonne nouvelle : **l'équation est déjà là**, il suffit d'isoler le terme foncier :

```
foncier_max = prix_sortie × shab_vendable × coef − construction − VRD
```

Tous les termes sont calculés. **Le travail M22 = exposer ce mode inverse** (endpoint + UI) — ajout ciblé, pas une reconstruction. Mais il faut le coder : ce n'est pas disponible aujourd'hui.

---

## 5. SDP RESTANTE — entièrement calculée, avec une incertitude documentée

**Réponse nette : OUI, ça existe et c'est complet.** Module dédié `src/labuse/faisabilite/residuel.py`.

- **SDP autorisée** : `engine.py:257` → `sdp = footprint × niveaux` (emprise constructible après reculs/emprise%/pleine terre × coef occupation × niveaux issus de la hauteur PLU).
- **Surface bâtie existante** : OUI, `bati.py:87-111` via BD TOPO — `bati_ratio` (emprise bâtie / surface), count, plus grand bâtiment. Classification en 6 catégories (vacant → déjà bâti).
- **SDP existante** : `residuel.py:70` → `emprise_batie × niveaux_existants`.
- **SDP RÉSIDUELLE** : `residuel.py:71` → `max(0, sdp_max − sdp_existante)`. Exposée (fiche, exports), **cachée en table `parcel_residuel`**, déjà branchée sur un filtre carte « sous-densité ».

**Seule limite, honnêtement documentée dans le code** : les **niveaux du bâti existant** ne sont pas toujours dans BD TOPO. Quand la hauteur manque, le module retombe sur une hypothèse (1 niveau par défaut) et le signale via les flags `estimation_sdp` et `niveaux_reels`. Donc la SDP résiduelle est parfois **estimée, pas mesurée** — mais l'app le dit. Pour un « Rapport de potentiel » avant compromis, ce caveat devra apparaître à l'écrit.

---

## Ce que M22 doit budgéter (synthèse)

| Export | Socle prêt | À construire |
|---|---|---|
| **Lettre de vérification zonage** | zonage/règles/articles déjà dans faisabilité + PLU calibrés | template court WeasyPrint + citation articles. **Le moins cher.** |
| **Rapport de potentiel (agence)** | SDP résiduelle, bâti existant, risques | divisibilité = signal **masqué** (revue Vic requise) + surface min/zone **inexistante** |
| **Argumentaire négociation (promoteur)** | DVF comparables, charge foncière, décotes chiffrables (pente/PPR/défisc) | **inversion calculette (foncier max) à coder** + assumer décotes qualitatives (viabilisation/risques jamais en €) |

**Trois manques réels à porter à l'arbitrage avant M22 :**
1. l'inversion de la calculette n'existe pas (foncier max à partir d'un prix de sortie) ;
2. la divisibilité est un signal gardé fermé (`EXPOSE = False`, revue Vic) ;
3. plusieurs décotes resteront qualitatives — doctrine assumée du code (viabilisation jamais chiffrée en €), pas un oubli.

---

## Références fichiers (chemins clés)

- Moteur PDF FPDF2 : `src/labuse/api/pdf_premium.py`, `src/labuse/api/pdf_projet.py`
- Moteur PDF WeasyPrint : `src/labuse/flash/report.py`, `src/labuse/api/dossier.py`, `src/labuse/api/banquier.py`
- Socle commun exports : `src/labuse/api/export_commun.py`
- Divisibilité : `src/labuse/ingestion/division_or.py`, `src/labuse/api/division_review.py`
- Faisabilité / SDP : `src/labuse/faisabilite/engine.py`, `src/labuse/faisabilite/residuel.py`, `src/labuse/bati.py`
- DVF / bilan / calculette : `src/labuse/faisabilite/bilan.py`, `src/labuse/api/modules.py` (`POST /faisabilite/{idu}/charge`)
- Décotes / risques : `src/labuse/faisabilite/engine.py`, `src/labuse/faisabilite/viabilisation.py`, `src/labuse/ingestion/defisc_fenetres.py`, `src/labuse/ingestion/score_e.py`
- Parité preuve : `docs/mandats/M20_C_PARITE_DOSSIER.md`
