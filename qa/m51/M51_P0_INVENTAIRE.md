# M51-P0 — Inventaire du corpus PLU (LECTURE SEULE · STOP arbitrage)

**Boussole** : l'annuaire SERT DU VERBATIM SOURCÉ (commune, document, article, page PDF, lien), jamais
une synthèse ; le doute est DIT. **Aucun code produit en P0** (inventaire only) — golden/SHA non touchés.

---

## 1. CE QU'ON A RÉELLEMENT — 6 PDF exploitables sur 24, 21 YAML de citations

| état | communes | # |
|---|---|---|
| **PDF règlement LOCAL** (natif, exploitable now) | Le Port 97407 · Saint-Denis 97411 · Saint-Paul 97415 · Saint-Pierre 97416 · Sainte-Marie 97418 · Sainte-Suzanne 97420 | **6** |
| **YAML calibration** (citations article+page, PAS le verbatim intégral) | 21 communes (toutes sauf 97409/97413/97417) | **21** |
| **RNU** (aucun PLU — réponse honnête) | Saint-Philippe 97417 | 1 |
| **opposabilité_en_attente** (révision en cours ; PLU ancien SERVI fait foi) | Saint-André 97409 (PLU 2019) · Saint-Leu 97413 (PLU 2007) | 2 |

**Le corpus PDF est mince et partiellement ÉPHÉMÈRE.** Les YAML citent chacun leur PDF source
(`97410_reglement.pdf` 162 p., `97404_reglement.pdf` 106 p., `97414_reglement.pdf` 139 p., …) mais
**15 de ces sources n'existent plus sur disque** — elles étaient en « cache session nuit B » / « cache
pré-vol nuit » (caches de run, purgés). Seuls **6 PDF** survivent, dans le **checkout frère**
`/Users/openclaw/Desktop/labuse/reports/m6-audit/reglements/` (+ `97407_jugement…pdf`).

**MAIS re-téléchargeables** : chaque YAML porte la provenance GPU (`archive GPU <idurba>`,
`Pieces_ecrites/3_Reglement`). L'**idurba opposable est ancré par M40** (`plu_millesimes.yaml`, 23/24
confrontés sur pièces). Donc les 15 manquants sont **récupérables depuis le Géoportail de l'Urbanisme
par idurba** (open-data) — c'est un GESTE DE FETCH à décider, pas une donnée perdue.

**Correspondance M40 (opposable servi)** : `plu_millesimes.yaml` fait foi (idurba + date_mairie +
statut). Les 6 PDF locaux portent le millésime dans leur nom (`97415_reglement_20251217.pdf` =
idurba `97415_PLU_20251217` ✓). Concordance nom↔idurba vérifiée sur les 6.

## 2. QUALITÉ D'EXTRACTION — 3 communes tests (pymupdf ; PAS d'OCR installé)

Outil : **pymupdf/fitz 1.28** (présent au venv frère). **Aucun OCR** (pdftotext/tesseract/ocrmypdf
absents) — sans effet ici, les 6 PDF sont **nativement textuels**.

| commune (difficulté) | pages | chars/page | en-têtes article/zone | verbatim |
|---|---|---|---|---|
| Sainte-Suzanne 97420 (**propre**) | 48 | ~3 900 | **73** (`Article U1`, `ZONE UE`, `Chapitre`) | propre |
| Sainte-Marie 97418 (**moyenne**) | 66 | ~3 500 | **60** | propre |
| Le Port 97407 (**difficile**, 32 Mo) | 319 | ~2 200 | **156** (`Article Ua 1…`) | propre, natif malgré le poids |

- **Articles détectables** : OUI, regex sur en-têtes (`(?im)^\s*(ARTICLE|Article)\s+[A-Za-z]{1,3}\s*\d+`
  + `ZONE …`). Les 3 formats (moderne mutualisé par famille, classique par zone) se détectent.
- **Numéros de page** : la **page PDF (index fitz) est fiable à 100 %**. Le n° IMPRIMÉ est souvent
  noyé dans une ligne d'en-tête (« PLU DE … REGLEMENT … 4 ») → parsing fragile (3/66 détectés en
  naïf) ; et il peut être **ambigu** (Saint-Benoît : double numérotation, 2 blocs). **→ citer la
  PAGE PDF** (décision déjà prise dans `plu_saint_benoit.yaml` : `pagination_citee: "pdf"`).
- **Verbatim** : propre, pas d'artefact OCR (natif). Ligatures/espaces insécables à normaliser à
  l'ingestion (léger).

## 3. SAINT-BENOÎT (97410) — PDF absent, citations riches, 19 fiches = les fiches AU

- **PDF `97410_reglement.pdf` (162 p.) ABSENT en local** (cache « nuit B » purgé). Idurba opposable
  `97410_PLU_20200206` (M40, servi). **À re-fetcher (GPU) ou récupérer chez Vic** pour servir le verbatim.
- **Les « 19 fiches annexes » = les fiches AU N°01-19** (régime d'urbanisation par zone AU : opération
  d'ensemble OU équipements internes — régime 1AU ; n° de fiche = n° du libellé GPU, confirmé Art. AU 1
  p.19). Elles sont dans le **2ᵉ bloc du PDF, pages PDF 49-162** (renuméroté « Page 1..114 » → **double
  pagination**, gotcha connu). Le YAML porte déjà des citations fines (ex. fiche N°02 p.55 : recul
  voirie 10 m ; annexe 3 p.73 : caducité STECAL loi Littoral 31/12/2021).
- **Modifs n°2 / n°3** : **incertitude M40 CONSIGNÉE, non fabriquée** — « ne seraient PAS intégrées au
  GPU, à confirmer en mairie (hors open-data) ». **Chez Vic.** L'annuaire dira l'incertitude, n'inventera rien.
- **Ce qui manque pour P2** : le PDF source (verbatim des 19 fiches). Sans lui, on ne peut que citer
  ce que le YAML a déjà extrait — insuffisant pour « passer les 19 fiches une à une ».

## 4. ARCHITECTURE PROPOSÉE

**Stockage** — une table indexée FTS, granularité **article** :
```
plu_reglement_extrait(
  id, insee, commune, idurba, millesime,          -- ancrage M40 (millesimes = vérité)
  document,                                        -- '97420_reglement.pdf'
  zone, article_ref,                               -- 'UE', 'Article U 4'
  page_pdf int,                                    -- page PDF (fiable) — JAMAIS la page imprimée seule
  texte_verbatim text,                             -- le verbatim brut, tel quel
  doute boolean, doute_motif text,                 -- OCR douteux / page illisible → DIT
  source_url text,                                 -- lien GPU / fichier
  tsv tsvector                                     -- GIN, config 'french'
)
```
- **Granularité = ARTICLE** : unité naturelle du règlement, regex-détectable, assez fine pour un extrait
  citable, assez grosse pour rester du verbatim (l'alinéa fragmenterait la citation ; la page serait trop
  grossière). Alinéa = sous-découpe optionnelle plus tard ; page = repli si un article n'est pas isolable.
- **Recherche = Postgres FTS** (`tsvector` french + index GIN), par commune OU île entière. **Suffisant** :
  la boussole demande du VERBATIM SOURCÉ, pas de la synthèse → un match de mots-clés qui **renvoie le
  verbatim + la référence complète + le lien** est exactement le besoin. **Pas d'embeddings / vector DB**
  (ce serait de la similarité sémantique = pente vers la synthèse, hors boussole).
- **Communes inexploitables** : DITES dans l'outil (RNU Saint-Philippe : « pas de règlement communal » ;
  révision en cours Saint-André/Saint-Leu : servir l'ANCIEN opposable + drapeau « révision non
  approuvée » ; PDF absent : « règlement non ingéré — à récupérer »).

## 5. ARBITRAGE DEMANDÉ (STOP)

1. **Périmètre exploitable immédiat = 6 communes** (PDF locaux natifs). Pour couvrir l'île, **re-fetch
   des 15 PDF manquants depuis le GPU par idurba** (geste réseau, open-data) — **je le fais en P1, ou tu
   préfères fournir les PDF ?** (Les caches « nuit B » sont perdus ; l'idurba M40 donne la cible exacte.)
2. **Saint-Benoît** : `97410_reglement.pdf` (162 p.) à **re-fetcher (GPU) OU récupérer chez toi** (+ les
   modifs n°2/n°3 chez toi, hors GPU). Sans le PDF, P2 « les 19 fiches une à une » n'est pas faisable —
   confirme la source.
3. **Architecture** : table `plu_reglement_extrait` + **Postgres FTS french** + granularité **article** +
   citation **page PDF** — OK pour toi ? (vs vecteurs = non, hors boussole verbatim.)
4. **OCR** : aucun PDF scanné parmi les 6 ; mais si un des 15 re-fetchés est scanné, il faudra **installer
   tesseract/ocrmypdf** (absent). J'installe au besoin (et le doute OCR sera DIT par extrait).
