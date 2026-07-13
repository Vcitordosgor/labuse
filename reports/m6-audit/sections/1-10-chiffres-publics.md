# M6 Phase 1 — §1.10 Cohérence des chiffres publics

> Audit LECTURE SEULE du 13/07/2026 — branche `audit/grand-check`.
> Quatre surfaces croisées : **app locale** (http://127.0.0.1:8010, endpoint `/stats`) · **site public labuse.immo** (WebFetch 13/07/2026) · **PDF Flash** (`src/labuse/flash/`) · **supports commerciaux** (`commercial/`, `DEMO_PACK*.md/html`, `DEMO_ONE_PAGER.html`, `SCRIPT_VENTE.md`).
> Valeurs réelles sourcées : base `labuse` (SELECT uniquement) + `/stats` de l'app.

## 1. Valeurs de référence (mesurées le 13/07/2026)

| Grandeur | Valeur réelle | Source de vérité |
|---|---|---|
| Parcelles évaluées | **431 663** | `SELECT count(*) FROM parcels` = `/stats total` = BILAN_ILE.md |
| Communes couvertes | **24 / 24** | `count(DISTINCT commune) FROM parcels` = 24 |
| Opportunités (île) | **6 021** | `/stats` (statut courant `opportunite`) |
| À creuser / exclues (île) | 84 908 / 117 680 | `/stats` |
| Saint-Paul : parcelles | **51 129** | `count(*) FROM parcels WHERE commune='Saint-Paul'` |
| Saint-Paul : opportunités | **737** | `/stats?commune=Saint-Paul` |
| Score opportunité max (île / Saint-Paul) | **89 / 81** | `/stats` (`opportunity_max`) |
| Détections piscines (brut / validées ok) | 19 899 / 815 (804 faux positifs jugés, 18 280 non revus) | `ortho_detections WHERE type='piscine'` |
| Preset UI « Parc piscines (entretien) » | 5 784 | `segment_preset_counts.parc-piscines-entretien` |
| Prix produit dans le code | **aucun prix d'abonnement** ; Flash `flash_price_eur = 79.0` (config, non commercialisé — Stripe bloqué) | `src/labuse/config.py:115` |
| Dernière ingestion | **11/07/2026** (37 runs tracés) | `max(started_at) FROM ingestion_runs` |

## 2. Tableau des divergences

| # | Chiffre | Où | Valeur affichée | Valeur réelle sourcée | Gravité | Recommandation |
|---|---|---|---|---|---|---|
| D1 | Parcelles notées | labuse.immo (hero) | « **500 000+** parcelles notées » | **431 663** (`parcels`, = /stats) | **HAUTE** — chiffre-vitrine principal surévalué de **+15,8 %** ; falsifiable par n'importe quel prospect qui ouvre l'app (le /stats et l'UI disent 431 663) | Remplacer par « 431 000+ » ou « plus de 430 000 » ; ne jamais publier un chiffre supérieur à ce que l'app affiche |
| D2 | Exemple Saint-Paul | labuse.immo (aperçu produit) | « **3 214 parcelles** totales ; **214 opportunités** détectées » | Saint-Paul réel : **51 129 parcelles, 737 opportunités** | **HAUTE** — l'exemple date du pilote historique (sous-ensemble ~3 000 parcelles) ; un prospect qui ouvre Saint-Paul dans l'app voit des chiffres ×16 différents | Mettre à jour l'aperçu avec les chiffres du run courant, ou étiqueter explicitement « extrait » |
| D3 | Score exemple | labuse.immo (aperçu produit) | « Score **87**/100 » | `opportunity_max` réel : **89** (île), **81** (Saint-Paul) | MOYENNE — un 87/100 « Saint-Paul » est impossible dans le run courant (max 81) | Reprendre un score réellement atteint dans la commune montrée |
| D4 | Opportunités Saint-Paul (docs commerciaux, incohérence interne) | `commercial/PROSPECTION.md:15` vs `commercial/PROSPECTS_20.md:26,81` | « ~**110** retenues opportunité » vs « ~**800** opportunités motivées » — sur le même périmètre « 3 000 parcelles » | **737** opportunités sur le Saint-Paul complet (51 129 parcelles) | **HAUTE** — deux documents de prospection se contredisent entre eux ET avec l'app ; risque direct en rendez-vous | Harmoniser tous les supports sur les chiffres du run courant (737 / 51 129), dater les chiffres |
| D5 | Prix | labuse.immo (#tarifs) : Indé **290 €**/mois, Pro **490 €**/mois, siège **150 €**/mois, Organisation sur devis · `commercial/OFFRE_PILOTE.md` : audit **790 €**, pilote 45 j **2 500 € TTC** (alt. 1 500 € + 490 €/mois) · `commercial/PROPOSITION_PILOTE.md` : **2 500 € TTC** | — | **Aucun « 149 € Essentiel » n'existe** : introuvable dans le repo, les supports et le site (hypothèse du mandat infirmée). Seul prix codé : Flash 79 € TTC (`flash_price_eur`, produit non lancé) | MOYENNE — pas de contradiction frontale (pilote ≠ abonnement), mais trois grilles coexistent sans document pivot ; le plan « Essentiel/Intégral » du code (`src/labuse/plans.py`) n'a aucun prix public alors que le site vend « Indé/Pro » | Créer une grille tarifaire unique de référence ; aligner les noms de plans code (Essentiel/Intégral) ↔ site (Indé/Pro) avant commercialisation |
| D6 | Fraîcheur des données | labuse.immo : « MAJ · juil. 2026 » + « sources publiques… **tenues à jour** » · app (page Sources) : « Les rafraîchissements sont aujourd'hui **manuels** » | — | Dernière ingestion réelle : **11/07/2026** — « MAJ · juil. 2026 » est vrai | BASSE — **aucune promesse « mise à jour quotidienne » trouvée** (hypothèse du mandat infirmée) ; la page Sources de l'app est même exemplairement honnête. Seul flou : « tenues à jour » sans fréquence | Sur le site, préciser le mode réel (« synchronisation par millésime / à chaque run ») pour verrouiller la cohérence avec la page Sources |
| D7 | Couches croisées | labuse.immo (#donnees) | « **22 couches** croisées » (liste nominative) | 32 `kind` distincts dans `spatial_layers`, **51 sources** dans `data_sources` | BASSE — sous-vente (favorable), mais la liste inclut « **Propriétaires** » et « Zones humides » : voir D8 et vigilance V3 | Recompter et aligner la liste sur la page Sources de l'app |
| D8 | Couche « Propriétaires » | labuse.immo (#donnees, item 20) | « Propriétaires » présenté comme couche de données | Seuls les propriétaires **personnes morales** sont en base (fichier DGFiP PM, LO v2) ; les particuliers ne sont PAS couverts (renvoi SPF, choix légal assumé dans le code) | **MOYENNE-HAUTE** — survente : un prospect comprendra « tous les propriétaires » ; enjeu aussi RGPD/licence (cf. §1.11) | Reformuler : « Propriétaires personnes morales (collectivités, SCI, bailleurs…) » |
| D9 | « 100 % du foncier passé au crible » | labuse.immo (hero) | 100 % | 24/24 communes, 431 663 parcelles évaluées, « aucune commune à 0 évaluation » (BILAN_ILE.md) | OK — cohérent avec l'interne | Rien (garder la preuve BILAN_ILE à jour après chaque run) |
| D10 | Chiffres démo BK0023 | `SCRIPT_VENTE.md`, `DEMO_PACK*.{md,html}`, `DEMO_ONE_PAGER.html` | « opportunité **74** », « ~**5 310 €/m²** », « CA indicatif ~**33 M€** », 9 723 m² vacants | Non recontrôlés dans cet audit ; or le scoring a changé depuis (v2 M5/M5.1, tri par rang) | MOYENNE — un chiffre de fiche périmé en pleine démo est le pire scénario | Re-vérifier BK0023/BP0571 dans l'app juste avant chaque démo (case déjà prévue dans `DEMO_PACK.md:119` — l'exécuter) |
| D11 | Piscines | Aucune surface publique ne publie de total piscines | — | 19 899 détections brutes dont **815 seulement validées « ok »** ; preset UI 5 784 ; mémoire projet : 8 299 livrées (wave-ortho, 90,7 % sur échantillon) | BASSE (préventif) | Si un chiffre piscines doit sortir publiquement : utiliser le périmètre livré (preset/couche produit), jamais le brut `ortho_detections` |

## 3. Constats transverses

1. **Le site public vit sa vie** : son code source n'est pas dans ce repo (hébergement Cloudflare, mentions légales EI Victor Lagane) ; aucun des chiffres D1-D3 n'existe côté repo, donc aucune CI ne peut les rattraper. Reco : versionner le site ou tenir un fichier pivot `chiffres-vitrine.md` regénéré après chaque run, seule source autorisée pour site + supports.
2. **Les surfaces internes sont cohérentes entre elles** : `/stats` = `parcels` = BILAN_ILE (431 663 / 24). Le PDF Flash n'embarque aucun chiffre-vitrine global (uniquement des données par parcelle + sources) : RAS.
3. **Les deux hypothèses du mandat** : « 500 000+ vs 431 663 » **confirmée** (D1) ; « 149 € Essentiel » et « mise à jour quotidienne » **infirmées** (aucune occurrence nulle part).
