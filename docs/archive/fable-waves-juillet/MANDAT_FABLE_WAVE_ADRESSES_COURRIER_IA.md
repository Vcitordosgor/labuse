# MANDAT FABLE — Wave Adresses, Courrier, Protection & Recherche IA

**Repo** : `~/Desktop/labuse` · **Branche** : `feat/wave-adresses-courrier-ia` · **Merge** : Vic uniquement (`git merge --no-ff`) · Commits atomiques par lot.

**Dépendance souple** : les Lots 4 et 6 s'appuient sur le moteur de segments et le générateur Flash s'ils existent ; sinon, livrer les fondations et noter. Aucun lot bloquant.

---

## Lot 1 — Liaison adresses ↔ parcelles (BAN) — fondation des lots 2 et 4

1. **Source** : Base Adresse Nationale, export département 974 (adresse.data.gouv.fr, Licence Ouverte). Ingestion complète → table `adresses(id_ban PK, numero, voie, code_postal, commune, insee, geom point, idu text)`.
2. Rattachement : jointure spatiale point-dans-parcelle → `idu`. Adresses hors parcelle (rare) : plus proche parcelle < 20 m, sinon NULL.
3. Index inverses : parcelle → adresses (une parcelle peut en porter plusieurs), adresse → parcelle.
4. Refresh : intégré au job mensuel (la BAN bouge).
5. Effet immédiat : les exports "à l'occupant" de tous les presets utilisent l'adresse BAN normalisée (numéro, voie, CP, commune) au lieu d'approximations.

**Acceptation** : ≥ 90% des parcelles bâties résidentielles ont ≥ 1 adresse rattachée ; échantillon de 30 vérifié visuellement par Vic.

## Lot 2 — Envoi de courrier postal

**Phase A — Export publipostage (obligatoire)** :
1. Sur tout export de preset : format "publipostage" = CSV normalisé (Adresse ligne 1/2, CP, Ville, destinataire "À l'occupant" — jamais de nom de personne physique) + PDF planches d'étiquettes (format standard 63,5×38,1 configurable).
2. Gabarit de courrier : page d'aide avec modèle de lettre par famille de métier (texte éditable, hors scope juridique).

**Phase B — Envoi intégré via API (après A)** :
1. Étudier les prestataires courrier API avec **couverture DOM confirmée** (Merci Facteur, Maileva/La Poste, Seeuletter... vérifier DOM + tarifs). Si aucun ne couvre le 974 correctement : stub + note au rapport, ne pas forcer.
2. Si viable : bouton "Envoyer un courrier" sur une sélection de leads → upload/choix du modèle PDF → envoi via API → suivi statut. Prix affiché au client = coût prestataire × marge (config, défaut ×1,5). Facturation à l'usage via Stripe (metered ou facture séparée — proposer le plus simple, documenter).
3. Plafonds anti-abus : max envois/jour par compte (config), validation du contenu par case à cocher "j'assume le contenu de ce courrier" (responsabilité émetteur).

## Lot 3 — Protection anti-scraping

1. **Quotas de consultation** par siège et par jour (config, défaut 300 fiches parcelle/jour) — en plus des quotas d'export existants. Dépassement → message + gel des consultations jusqu'à minuit.
2. **Rate limiting** applicatif : max N requêtes/minute par session (config, défaut 60) ; burst → captcha léger ; récidive → gel compte + alerte admin.
3. **Détection de patterns** : job quotidien qui score les comptes (séquences d'IDU consécutifs, régularité machinale des intervalles, volume nocturne, ratio consultations/exports aberrant) → table `abuse_scores`, alerte admin au-delà du seuil. Pas de blocage auto sur le score seul (faux positifs) : gel manuel par Vic.
4. **Watermarking des exports** : chaque CSV/PDF exporté contient (a) une colonne/mention discrète `ref` encodant compte+date, (b) 2-3 enregistrements canari uniques par compte (adresses réelles, micro-variations de formatage traçables). Table `export_fingerprints` pour retrouver la source d'une fuite.
5. **Front sobre** : vérifier qu'aucun endpoint ne sert de données hors zone visible/pagination ; pas de dump JSON massif côté client.
6. CGV : noter au rapport les clauses à ajouter (interdiction d'extraction systématique, résiliation) — rédaction juridique = action Vic.

## Lot 4 — "Dossier parcelle" PDF (usage interne client)

1. Bouton sur la fiche parcelle (plans Essentiel et Intégral) : génère un PDF brandé de la parcelle — réutilise le générateur Flash (template allégé, sans page tarifaire) : carte, identité, zonage PLU calibré, risques, ABF/ENS/QPV, DVF alentour, permis proches, sections conditionnelles.
2. Différence avec Flash : réservé aux abonnés, compte dans un quota (config, défaut 20/mois Essentiel, illimité Intégral), mention "Généré via LABUSE pour [raison sociale]".
3. Usage cible : comité d'engagement, banque, client final de l'abonné.

## Lot 5 — Pré-dossier PC (préparatoire, PAS un dossier de permis)

1. Sur une parcelle, génération d'un pack "préparation PC" : CERFA 13406 (maison individuelle) **pré-rempli des seuls champs parcelle/terrain** (références cadastrales, adresse BAN, surface, zonage) — PDF remplissable, champs projet laissés vides ; plan de situation auto (carte + cadastre) ; fiche des règles du zonage (PLU calibré) ; liste des pièces exigées et servitudes connues (ABF etc.).
2. **Libellé impératif sur chaque page** : "Document préparatoire établi à partir de données publiques — ne constitue pas un dossier de demande de permis. À compléter et vérifier par le pétitionnaire ou son architecte."
3. Vérifier le n° de CERFA en vigueur avant d'implémenter. Réservé Intégral.

## Lot 6 — Recherche en langage naturel (le "wow" démo)

1. Barre de recherche sur l'app : l'utilisateur tape une question libre ("parcelles dont le gérant est en redressement à Saint-Paul", "villas mutées récemment avec grand jardin sans piscine au Tampon").
2. **Architecture stricte** : appel LLM (API Anthropic, clé en env) avec un prompt système contenant le registry des filtres du moteur de segments (clés, types, valeurs possibles) → le LLM retourne **uniquement un JSON de filtres valides** + la commune éventuelle. Validation du JSON contre le registry avant exécution — tout champ inconnu est rejeté. **Jamais de SQL généré, jamais de texte libre exécuté.**
3. Le résultat s'ouvre dans le query builder standard, filtres visibles et modifiables (l'utilisateur voit la "traduction" — pédagogique et corrige les erreurs du LLM).
4. Si la question sort du périmètre des filtres : réponse honnête "je ne peux filtrer que sur : [liste]", pas d'hallucination.
5. Rate limit : 30 requêtes NL/jour/siège (config). Log des questions posées (anonymisé) → c'est ta roadmap des filtres manquants.
6. Respect des plans : un compte Essentiel qui demande un filtre Intégral (Q×A, redressement/BODACC si classé Intégral) → résultat grisé + CTA upgrade, même mécanique que les presets.

---

## Critères d'acceptation

```sql
-- Lot 1
SELECT count(*) FILTER (WHERE idu IS NOT NULL)::float/count(*) FROM adresses;      -- ≥ 0.9
-- Lot 3
SELECT count(*) FROM export_fingerprints;                                           -- > 0 après 1 export test
-- Lot 6 : 20 questions de test (fournies dans /tests/nl_queries.txt) → ≥ 16 traduites en filtres corrects, 0 exécution de champ hors registry
```

+ Playwright : export publipostage non vide avec adresses BAN ; génération Dossier parcelle < 30 s ; pré-dossier PC affiche le libellé préparatoire ; recherche NL "maisons mutées récemment à Saint-Leu avec jardin" retourne des résultats cohérents ; 301 consultations de fiches le même jour → gel.

## Contraintes

- RGPD inchangé : exports "à l'occupant" sans nom de personne physique ; les questions NL loguées sans identifiant utilisateur nominatif.
- Courrier (Lot 2B) : le contenu envoyé est de la responsabilité du client (case obligatoire) ; pas d'envoi sans paiement du coût courrier.
- LLM (Lot 6) : température basse, aucun contenu de la base envoyé au LLM (seulement la question + le registry) — la donnée ne sort pas.
- Paramètres en config. Réseau : BAN, prestataire courrier retenu, API Anthropic. Rien d'autre.
- Ordre : 1 → 3 → 4 → 6 → 2A → 5 → 2B.

## Rapport de fin attendu

Taux de rattachement BAN, prestataire courrier retenu (ou constat d'absence DOM) avec grille de coûts, seuils anti-scraping actifs, score du jeu de test NL (X/20) avec les échecs commentés, n° CERFA vérifié, et liste des clauses CGV à faire rédiger (action Vic).

---

## AJOUTS SESSION (10/07/2026)

**Vérification au démarrage (Phase 0)** : les Lots 3, 4 et 6 présupposent un système de comptes/sièges/plans (Essentiel/Intégral) — quotas « par siège », gel de compte, gating par plan. S'il n'existe pas encore en base : implémenter quotas et rate limiting au niveau session/IP, stubber le gating par plan (constantes et branchements prêts), et lister « mandat Auth & Plans » comme prérequis à la commercialisation dans le rapport de fin. Ne PAS inventer un système d'authentification dans ce mandat.

**Lot 1, point 6 (ajout)** : rattacher via la table `adresses` les ~13 % de copropriétés RNIC (`rnic_coproprietes`, data-gap LOT 10) encore sans parcelle. Règle générale pour la suite : tout géocodage (Flash, Copro) passe par cette table locale, plus par l'API BAN en ligne.
