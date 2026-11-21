# ECARTS — AUDIT-CHIRURGICAL-1

> Chasse aux bugs et incohérences, LECTURE SEULE. Aucune correction appliquée.
> Base locale `labuse`, API live sur `:7440`, front sur `:10240` (env=local, auth désactivée).
> Échantillon de 38 parcelles (`echantillon.csv`, reproductible via `echantillon_run.sh`).
> Oracle indépendant (`oracle.csv`, `oracle.sql`), matrice des faits (`MATRICE.csv`, `DIVERGENCES_auto.csv`).
> Preuves par parcelle dans `~/Desktop/chasse-1/<idu>/` ; captures d'écran dans `~/Desktop/chasse-1/_ecrans/`.

Classement : **faux** (valeur fausse) · **contradictoire** (deux sources, deux valeurs) · **trompeur** (exact mais induit en erreur) · **cosmétique**.

---

## Résultat d'ensemble

Sur les faits **servis en direct** (fiche `/parcels/{idu}`, Dossier via `builder` qui lit `parcel_fiche`), la cohérence est **forte** et vérifiée par recalcul indépendant : surface, parts d'aléa par niveau, emprise bâtie servie, parts de zone / EBC, RNU — tout concorde (voir COUVERTURE.md, section « Conformités prouvées »). Les seules divergences de valeur systématiques détectées par la matrice portent sur l'**emprise citée dans le motif de score**, et se rattachent au **calcul de nuit gelé** (connu, non compté — K1 ci-dessous). Les écarts réellement nouveaux sont peu nombreux et de faible gravité.

---

## ÉCARTS (nouveaux, comptés)

### E1 — COSMÉTIQUE — Surface : l'autocomplétion montre le dessin, la fiche/Dossier le cadastre
- **Parcelle** : 97422000AD0887 (et par construction toute parcelle où dessin ≠ contenance).
- **Deux valeurs** : autocomplétion de recherche = **1 699 m²** (dessin, `surface_m2`=1698.59) ; tuile « Surface » de la fiche + Dossier = **1 703 m²** (cadastre, `contenance_m2`=1703, `surface_source="cadastre"`).
- **Où le lire** : écran — taper l'IDU dans la recherche (menu déroulant `listbox`), puis ouvrir la fiche (tuile Surface) ; capture `~/Desktop/chasse-1/_ecrans/fiche_AD0887_1440.png`. API — `/parcels/97422000AD0887` (`surface_m2` vs `contenance_m2`).
- **Reproduire** : rechercher `97422000AD0887`, comparer le « 1 699 m² » du menu au « 1 703 m² » de la fiche.
- **Cause probable** : l'autocomplétion (`/parcels/search`) renvoie `surface_m2` (dessin) ; la fiche et le Dossier affichent `contenance_m2` (cadastre). Un fait « surface », deux surfaces nommées, non réconciliées côté recherche. Écart 4,4 m².

### E2 — TROMPEUR/COSMÉTIQUE — Apporteur : un refus livré en HTTP 200 sous forme de PDF
- **Parcelle** : toutes (env. d'audit sans compte nommé) — 97422000AD0887, 97416000HT0538, 97424000AO1198, 97404000AM0838 testées.
- **Fait** : `GET /apporteur/{idu}.pdf` renvoie **HTTP 200** + un **PDF 1 page de 1 174 octets** dont le texte est « *Document non genere / Renseignez le nom de votre société dans Compte* ». L'inventaire du code prévoit un **422** pour « compte sans nom ».
- **Où le lire** : `~/Desktop/chasse-1/97422000AD0887/apporteur.pdf` (`pdftotext` → 2 lignes). 
- **Reproduire** : `curl -s -o a.pdf -w '%{http_code}' http://127.0.0.1:7440/apporteur/97422000AD0887.pdf` → `200`, `pdftotext a.pdf -`.
- **Cause probable** : le gabarit de refus de l'Apporteur est rendu en PDF et renvoyé avec un code 200 (document « réussi » qui est en fait une erreur) ; le libellé de repli « *non genere* » n'est pas accentué (chaîne ASCII de dev). 
- **Réserve** : comportement attendu quand aucun compte nommé n'est connecté (cas de l'audit) ; l'Apporteur complet n'est pas testable sans « société » renseignée (voir COUVERTURE). La gravité tient au couple *200 + libellé dev non accentué*, pas au refus lui-même.

### E3 — CONTRADICTOIRE (à confirmer) — `parcel_constructibilite` périmée et incomplète vs la fiche live
- **Parcelles** : 97404000AM0838 (zone UE, fiche live = *non constructible, « Habitat interdit dans cette zone »*), slivers 97424000AO1198 / 97415000DE0669 / 97405000AZ0993 (fiche live = *« Terrain trop exigu »*), RNU 97417000AO0050 (fiche live = *non constructible*). **Toutes absentes** de `parcel_constructibilite`.
- **Deux sources** : la table `parcel_constructibilite` (précalcul, `computed_at` = **2026-07-29**, 11 782 lignes) ne contient PAS ces parcelles ; la fiche live `/parcels/{idu}` les déclasse pourtant non-constructibles. La table est lue par `flash/data.py`, `api/tiles.py`, `scoring/p_v2/pipeline.py`.
- **Où le lire** : `SELECT p.idu, pc.label, pc.cause FROM parcels p LEFT JOIN parcel_constructibilite pc ON pc.parcel_id=p.id WHERE p.idu IN (…)` → label/cause vides ; comparer à `GET /parcels/97404000AM0838` → `potentiel_a_batir.constructible=false, motif="Habitat interdit dans cette zone"`.
- **Reproduire** : les deux requêtes ci-dessus.
- **Cause probable** : table régénérée par le **job nocturne gelé** (connu) → périmée ; OU le précalcul ne couvre qu'une partie des motifs (`terrain_exigu`, `habitat_interdit`) que la fiche live recalcule. Impact client possible : Flash / tuiles affichant une constructibilité différente de la fiche. **À confirmer** : déterminer si l'écart tient au gel (auquel cas rattacher à K1) ou à une différence de seuil live/précalcul.

---

## ÉCARTS ATTRIBUÉS À DES CAUSES DÉJÀ CONNUES (NON COMPTÉS)

### K1 — Emprise du motif de score ≠ emprise servie (⇒ ratio « bâtie saturée » surévalué) — *calcul de nuit gelé*
- **Parcelles** (4/38) : AD0887 (motif 689 m²/41 %), AH1301 (91/71 %), AY0153 (114/44 %), DT0356 (238/46 %).
- **Fait** : le `score_v2.motif` (« bâtie saturée — ratio X % (emprise N m², source max(BD TOPO, CoSIA)) », `declasse=true`) cite une emprise **1,4–2×** supérieure à l'emprise **servie** (fiche `le_bien`, Dossier : 345/36/70/168 m², BD TOPO union) et au **recalcul indépendant**.
- **Preuve que c'est le run figé** : pour AD0887, `p_model_bati.emprise_bati_m2` **actuel = 425 m²** (= MAX(BD TOPO 345, CoSIA 425)) ; l'union réelle BD TOPO ∪ CoSIA recalculée = **457 m²** ; le motif sert **689** — valeur d'un run antérieur au correctif d'union (RECETTE-6, « effet au rebuild »). Le motif provient du *dryrun servi* figé.
- **Conclusion** : manifestation du **calcul de nuit gelé** (mandat : connu, à ne pas re-signaler). **Non compté.** Détecté automatiquement (`DIVERGENCES_auto.csv`). Signalé ici pour la traçabilité de la méthode.

---

## CANARIS (défauts connus, NON comptés — retrouvés par la méthode, preuve de non-aveuglement)

- **C-a (HT0538 — aucune place de stationnement exigée)** : `POST /modules/etude/stationnement {idus:[97416000HT0538],type_projet:collectif}` → `general.mode="absent"`, `ratio_par_logement=null`, `etat="document manquant — à confirmer"`. Preuve : `~/Desktop/chasse-1/_canaris/stationnement_97416000HT0538.json`. **Retrouvé seul.**
- **C-b (AD0887 — écart estimation rapide vs esquisse)** : Dossier AD0887 : « *constructible restante ≈ 719 m² … Surface à retenir : 795 m² (esquisse …) … L'estimation rapide donnait 1 047 m²* ». Trois grandeurs (719 / 795 / 1 047) pour une même « surface ». Preuve : `~/Desktop/chasse-1/97422000AD0887/dossier.txt`. **Retrouvé seul.**
- **C-c (AD0887 — règle maison appliquée à un immeuble)** : le *payload* de stationnement montre Ud12.2 « 1 place / logement », `etat="règle vérifiée"` ; la bascule maison↔immeuble se joue dans le **moteur complet** (Étude M22, non exécuté intégralement ici). Partiellement observé (voir COUVERTURE).

---

## Pour mémoire — vérifié SANS écart (détail en COUVERTURE.md)
Surface (38/38 = recalcul `ST_Area`), parts d'aléa par niveau (38/38 ≈ recalcul `georisque_alea` « fort »), emprise servie `le_bien` (38/38 ≈ union BD TOPO), part EBC (IS0448 34,4 % = part zone N recalculée), RNU St-Philippe (correct), absence de jetons de dev / `None` / `NaN` / dates futures dans les 38 Dossiers, valeurs écran = API sur la fiche AD0887.
