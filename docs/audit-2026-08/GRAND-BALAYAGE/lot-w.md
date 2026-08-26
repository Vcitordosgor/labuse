# LOT W — EXPORTS DE MASSE (50 passes)

- **Seed** : 5003
- **Run servi** : q_v10_m129 · back localhost:8000 · psql -d labuse (peer)
- **Score** : **49 OK / 1 KO sur 50**
- CSV : `docs/audit-2026-08/GRAND-BALAYAGE/lot-w.csv` (50 lignes)

## Couverture

Types couverts (tirage seed 5003, périmètres petits / vides / énormes) : `parcels/export.csv` (×10 : petit, 2 vides, île entière, Saint-Paul, tiers reserve, accents, signaux, surface), `signalements/export.csv` (×3), `modules/prospection-solaire?fmt=csv` — Densifier/Solaire (×5), `modules/velocite?fmt=csv` (×2), `modules/patrimoine?fmt=csv` — Scan-patrimoine / **GB-017** (×3), `parcels/{idu}/export.pdf` — fiche (×4), `parcels/{idu}/export?format=md` — markdown fiche (×3), `projets/{pid}/export.pdf` + `.csv` (×7), `dossier.pdf` / `dossier-banquier.pdf` / `lettre-zonage.pdf` / `argumentaire.pdf` / `spf-letter` — courriers GET (×12), `courrier/pdf` POST (×1).

## Vérifications transverses — RAS majeur

- **GB-016 (cap explicite)** : RESPECTÉ. Tout export CSV tronqué porte une notice en 1re ligne (BOM inclus) : parcels.csv « Export limité aux N premières lignes (plafond d'export N atteint)… » ; solaire.csv « Export limité aux 500 premières lignes sur 51129 — affinez les filtres ». Les exports sous le cap et les exports vides (0 ligne) n'affichent **pas** de notice (correct). **Aucune troncature silencieuse observée.**
- **GB-017 (patrimoine CSV)** : NON régressé. `/modules/patrimoine?siren=X&fmt=csv` renvoie bien du **CSV** (`content-type: text/csv`, en-tête `idu;commune;tier_v2;rang_v2;surface_m2;sdp_residuelle_m2;siren;raison_sociale`), pas de JSON.
- **En-têtes** : présents et nommés sur tous les CSV. En-têtes solaire richement libellés (`Productible kWh/kWc/an [Sourcé — PVGIS/SARAH3]`, etc.).
- **Valeurs sales** : AUCUN `undefined`/`NaN`/`None`/`null` brut trouvé dans 50 fichiers (CSV scannés ligne à ligne, PDF via pdftotext). Cases vides = champs `;;` légitimes (adresse absente, piscine non détectée).
- **Exports vides** : jamais de 500. Commune inexistante / surface_min=99999999 / siren bidon → CSV header-seul 200. IDU/projet inconnu → **404 JSON honnête** (« Parcelle … inconnue de l'analyse en cours. »), pas de 500.
- **Dates** : ISO 8601 + timezone dans signalements (`2026-08-14T20:02:20+04:00`), format `JJ/MM` / `2026-08-26` dans PDF et en-tête projet.csv.

## FINDINGS

### 1. [RÉGRESSION GB-023 — MEDIUM] `courrier/pdf` (POST) flatten œ→oe dans le texte utilisateur
- **Fichier** : POST `/courrier/pdf` (texte libre saisi par l'utilisateur, `PdfIn.texte`).
- **Problème** : le `œ` du corps de lettre est transliteré en `oe`. Texte injecté « Cœur de mon œuvre » → rendu PDF « **Coeur** de mon **oeuvre** ». Les accents é/è/ç et « L'Étang-Salé » passent intacts ; seul le `œ` est cassé.
- **Portée** : c'est le **chemin texte-utilisateur** qui régresse, pas les gabarits. La fiche PDF (`/parcels/{idu}/export.pdf`) et les textes de gabarit conservent correctement le `œ` (« maître d'œuvre » rendu avec œ) — donc GB-023 tient sur les documents à texte figé, mais **pas sur le courrier à texte libre**.
- **Cause probable** : la police / l'encodage du bloc corps du courrier PDF (probable repli core-font ou Latin-1 sans glyphe œ) applique une translittération œ→oe sur la chaîne utilisateur, là où les gabarits utilisent une police portant le glyphe. Un utilisateur francophone tapant « cœur », « sœur », « vœux », « œuvre » obtient un courrier fautif.
- **Sévérité** : MEDIUM (le courrier est le document de démarche ; faute d'orthographe visible dans un envoi propriétaire).

### Notes mineures (non-KO, pas de finding bloquant)
- `modules/velocite?fmt=csv` utilise le **délimiteur virgule sans BOM**, alors que tous les autres CSV de l'app sont `;` avec BOM UTF-8. Incohérence de format entre exports (Excel FR ouvrira velocite différemment), pas une corruption. À aligner si l'on veut un format d'export unique.
- `projets/{pid}/export.csv` d'un projet non figé (projet 16) : l'en-tête commentaire lit « # cadrage figé le **non figé** · … ». Ce n'est **pas** un `null` brut : c'est un repli texte cohérent (le PDF du même projet confirme « Cadrage non figé »). Les projets figés affichent bien la date (« cadrage figé le 2026-07-09 »). RAS.

## Contrainte d'exécution notée
Le back applique un rate-limiter global 60 req/min (challenge anti-bot `/protection/defi`, HTTP 429 « Résolvez le défi »). La batterie a dû être espacée (~1 req/s + retries) ; aucun export n'a échoué pour cette raison une fois repassé au ralenti — le 429 est un garde-fou d'infra, pas un défaut d'export.
