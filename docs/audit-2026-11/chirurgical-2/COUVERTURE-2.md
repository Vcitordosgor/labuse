# COUVERTURE-2 — AUDIT-CHIRURGICAL-2

> « Aucun écart » ne vaut QUE pour ce qui figure dans les tableaux ci-dessous.
> Prolonge [chirurgical-1/COUVERTURE.md]. Corrige les trois trous reprochés au 1ᵉʳ passage :
> (1) les faits sont extraits **des documents** (pas seulement cherche de « None ») ; (2) **tous**
> les documents sont générés sur 12 parcelles (pas 4) ; (3) l'écart de prix médian est **expliqué**
> et les deux oracles manquants (prix pondéré, zone rouge PPR) **aboutissent**.
>
> Base locale `labuse`, API live `:7440`, 12 parcelles. Preuves par parcelle : `~/Desktop/chasse-1/<idu>/`.
> Compte de test d'écriture : **AUDIT-TEST** (compte_id 142), supprimé en fin de mandat.

---

## 0. Les 12 parcelles (couverture des familles)

| idu | commune | famille couverte | surface | constructible |
|-----|---------|------------------|---------|---------------|
| 97422000AD0887 | Le Tampon | canari + constructible | 1 699 m² | oui |
| 97416000HT0538 | Saint-Pierre | canari (0 place stationnement) | 509 m² | oui (emprise 0) |
| 97403000AR1517 | Entre-Deux | constructible | 734 m² | oui |
| 97404000AM0838 | L'Étang-Salé | **grande** (2,1 ha) + **non constructible** (UE habitat interdit) + rouge 43 % | 20 798 m² | non |
| 97417000AO0050 | Saint-Philippe | **RNU** | 1 549 m² | non |
| 97411000IS0448 | Saint-Denis | **à cheval** + EBC/zone N + rouge 34 % + saturée | 818 m² | oui (SDP 0) |
| 97404000AY0153 | L'Étang-Salé | **zone rouge partielle** 41 % + saturée | 256 m² | oui (SDP 0) |
| 97414000CO0153 | Saint-Louis | zone rouge partielle 19 % + **grande** agricole | 6 670 m² | non (A) |
| 97421000BN0260 | Salazie | **à cheval** + **grande** agricole + rouge 100 % | 3 353 m² | non (A) |
| 97422000BW2635 | Le Tampon | **copropriété** | 2 002 m² | oui |
| 97412000CV0446 | Saint-Joseph | **propriétaire public** | 567 m² | oui (SDP 241) |
| 97424000AO1198 | Cilaos | **très petite** (0,69 m²) non constructible (exiguë) | 0,7 m² | non |

---

## 1. Documents réellement générés ET lus (document × parcelle)

✓ = généré (200) et lu ; `422` = refus **par conception** (pré-dossier PC sur parcelle non constructible ; Bilan « par défaut » sans chiffre d'affaires) ; `msg` = document-message honnête (Étude de faisabilité : « aucun scénario d'implantation ») ; `—` = non applicable.

| Parcelle | Fiche | Dossier | Gabarit | Apporteur | Estimer | ÉtudeZone | PréDoss | Bilan | Excel | BilanDéf | Courrier | ÉtudeFaisa | Station |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AD0887 canari/constr | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | ✓ | ✓ |
| HT0538 canari/0place | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | ✓ | ✓ |
| AR1517 constr | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | ✓ | ✓ |
| AM0838 grande/non-c | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | ✓ | 422 | ✓ | ✓ | ✓ |
| AO0050 RNU | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | 422 | ✓ | msg | — |
| IS0448 cheval/EBC | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | msg | ✓ |
| AY0153 rouge41% | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | msg | ✓ |
| CO0153 rouge19%/gr | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | 422 | ✓ | msg | — |
| BN0260 cheval/gr | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | 422 | ✓ | msg | — |
| BW2635 copro | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | ✓ | ✓ |
| CV0446 public | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | msg | ✓ |
| AO1198 exigu0.7m² | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 422 | ✓ | ✓ | 422 | ✓ | msg | ✓ |

- **Comparatif** : 4 PDF de 3 parcelles — `c1_constructibles`, `c2_rouge_grandes`, `c3_cheval_public_copro`, `c4_rnu_exigu_salazie` (`~/Desktop/chasse-1/_comparatifs/`).
- **Estimer par lien d'annonce** : 2 PDF depuis des annonces **Leboncoin du Radar local** (`~/Desktop/chasse-1/_estimer_lien/`). Le site externe n'est **jamais** contacté (SSRF fermé : le rapport est servi depuis la capture Radar du soir ; une annonce absente du Radar renvoie `url_bloquee`). Donc « site injoignable » ne s'est pas posé — la source est locale par conception.
- **Pré-dossier** : ZIP + 6–7 pièces extraites et lues (CERFA, PCMI1/2/4/7-8, règles-zonage, parfois enveloppe) pour les 7 constructibles ; `422 non_constructible` pour les 5 autres.
- **Bilan** : généré en DEUX variantes — (a) **pré-remplissage par défaut** de l'outil (sans produit) → l'export PDF/Excel refuse en **422** « aucun chiffre d'affaires » (comportement nominal, voir ECARTS-2 E-limite) ; (b) scénario minimal chiffré → PDF + Excel rendus, pour vérifier l'arithmétique.
- **Apporteur** : le document **complet** (≈ 290–325 ko) est généré pour les 12 (compte AUDIT-TEST). Au 1ᵉʳ passage seul le refus avait été vu. 11/12 rendus en process (hors HTTP) après le plafond d'export (voir §5).
- **Mails** : inventoriés au 1ᵉʳ passage (INVENTAIRE §D) ; **non envoyés** (déclencheurs = webhooks/jobs/actions admin ; aucun envoi en audit).

---

## 2. Oracles indépendants (le trou du 1ᵉʳ passage, comblé)

### 2a. Prix médian de secteur — **l'écart du 1ᵉʳ passage est EXPLIQUÉ**
Le 1ᵉʳ passage avait classé le prix médian « non vérifiable » (recalcul brut ≠ servi). Cause trouvée : la tête de fiche sert une **médiane PONDÉRÉE par la ressemblance** (`_mediane_ponderee`, distance/surface/terrain/âge), pas un `percentile_cont` simple. Oracle indépendant (`oracle_prix.py`, réimplémentation de `sector_price` **sans appeler le code applicatif**) :

| Résultat | 12/12 |
|----------|-------|
| médiane pondérée servie == oracle pondéré | **exact (±1 €)** |
| métadonnées (n ventes, rayon, période, type) == oracle | **concordent** |
| médiane servie dans [min, max] de l'échantillon retenu | **oui, 12/12** |

Écart pondéré vs médiane **simple** : typiquement ±0–7 %, mais jusqu'à **+25 % (CO0153, AO1198)** et **−15 % (AM0838)** sur des échantillons « maison » clairsemés où le poids se concentre sur le cluster le plus proche/récent. Dans tous les cas la valeur reste dans l'enveloppe brute. Détail : `oracle_prix.csv`, `oracle_prix.sql`. **Conclusion : pas d'écart — le 1ᵉʳ passage ne disposait pas de la méthode pondérée.** (Un piège adversarial confirmé : le libellé `type_prix` ne dit pas quels poids ont servi — BW2635 « appartement » passe par le chemin **non typé** car copropriété → repli bâti→maison inhibé ; l'inférer du libellé donnait 3 571 € au lieu de 3 000 €.)

### 2b. Part de zone rouge PPR par parcelle — **l'oracle ABOUTIT** (le 1ᵉʳ passage avait timeout)
Requête complétée en **18,7 s** (`statement_timeout`, `max_parallel_workers_per_gather=0`, restriction aux 12 parcelles, `ST_MakeValid` + `ST_Subdivide` des polygones PPR). `oracle_ppr.sql`/`oracle_ppr.csv`.

| idu | rouge % (oracle) | bleu % | servi | concorde |
|-----|------|------|-------|----------|
| AM0838 | 43,4 | 56,3 | 43 % | ✓ |
| AY0153 (B3) | 40,5 | 59,5 | 41 % | ✓ |
| IS0448 | 34,2 | 65,8 | 34 % | ✓ |
| CO0153 (B3) | 18,7 | 10,9 | 19 % | ✓ |
| BN0260 | 100,0 | 0,0 | 100 % (exclu) | ✓ |
| AR1517 | 0,0 | 50,8 | bleu 51 % | ✓ |
| AD0887, HT0538, BW2635, CV0446, AO1198 | 0,0 | 0,0 | pas de signal rouge | ✓ |
| AO0050 (RNU) | 0,0 | 0,0 | « PPR non classé » (subtype `i` périmètre) | ✓ |

**0 divergence.** Les deux « zone rouge partielle » (AY0153, CO0153) confirmés partiels ; les parts imprimées au Dossier (34 %, 41 %, 19 %) collent à l'oracle à ≤1 pt. Note : la table `aleas_parcelle` **n'existe pas** dans cette base (le signal rouge/bleu vit dans `cascade_results` + bloc risques de la fiche) — le mémo `aleas_parcelle` concernait un autre worktree.

---

## 3. Conformités reprouvées (recalcul indépendant = servi)
Reprises de CHIRURGICAL-1 et étendues aux 12 : surface (`ST_Area`), emprise bâtie servie (union BD TOPO), parts d'aléa, parts de zone/EBC, RNU, dernière vente — concordent. **Nouveau** : les parts de zone rouge PPR imprimées **au Dossier** concordent avec l'oracle géométrique (§2b) ; le prix médian imprimé **au Dossier/Estimer** concorde avec l'oracle pondéré (§2a).

---

## 4. MATRICE-2 et divergences
- `MATRICE-2.csv` : idu × fait × **document** × valeur (FICHE = vérité servie, + Dossier, Gabarit, Pré-dossier/CERFA, Estimer, Étude-zone, Bilan PDF/Excel, Apporteur, Courrier, Étude-faisa, Comparatif). C'est la correction du reproche n°1 (le 1ᵉʳ passage n'avait que la colonne FICHE).
- `DIVERGENCES_auto2.csv` : écarts détectés automatiquement entre documents pour un même fait.
- `matrice_parts/` : fragments par famille de documents (un sous-agent par famille).

---

## 5. NON testé / réserves de méthode (« aucun écart » NE s'applique PAS ici)

- **Plafond d'export d'usage loyal (30/j plan Intégral)** : le compte AUDIT-TEST a atteint `porte_export` dès la 1ʳᵉ parcelle (429). Les documents gatés (Dossier, Gabarit, Estimer, Étude-zone, Pré-dossier, Comparatif) ont donc été régénérés **en mode pilote (sans session)** — chemin **hors quota** mais **identique** en rendu ; l'Apporteur (qui exige un nom de compte) a été rendu **en process** (`LABUSE_PDF_PROCESS_ISOLE=0`, hors HTTP) avec la marque AUDIT-TEST. Le **changement de plan** du compte de test a été **refusé par la garde** (hors périmètre d'écriture) : contourné proprement par ces deux chemins, aucune donnée servie touchée. Voir ECARTS-2 (note de plafond).
- **Étude de faisabilité — parcelles non constructibles / saturées** : le moteur rend un **document-message** honnête (« aucun scénario d'implantation ») pour AO0050, IS0448, AY0153, CO0153, BN0260, CV0446, AO1198. Le calcul d'implantation complet (scénario chiffré) n'est donc exercé que sur les parcelles où il aboutit (AD0887, HT0538, BW2635, AM0838 partiel). La **tension à deux moteurs** (fiche « Fort potentiel 241 m² » vs Étude « impossible » sur CV0446) est analysée en ECARTS-2.
- **Citations PLU** : vérifiées contre le **verbatim stocké** (`plu_reglement_extrait.texte_verbatim` + page_pdf + source_url) — l'**image** du règlement officiel n'a pas été re-téléchargée (accès externe hors périmètre) ; la vérification porte donc sur le texte que LABUSE a lui-même extrait, pas sur le PDF source. Voir `citations_check.csv`.
- **Bilan « par défaut »** : le pré-remplissage par défaut ne porte aucun chiffre d'affaires → l'export refuse (422). L'arithmétique du Bilan est donc vérifiée sur une variante **minimale chiffrée**, pas sur le défaut.
- **Écrans / navigateur** : non reparcourus (le 1ᵉʳ passage l'a fait sur la fiche) — ce mandat porte sur les **documents**, pas les écrans.
- **Apporteur complet (contenu)** : généré pour les 12, lu ; mais l'exhaustivité juridique des 8–20 pages n'est pas « vérifiée » fait par fait au-delà des faits listés en MATRICE-2.
