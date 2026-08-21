# Demande — PLU zonage SIG de Sainte-Marie et Sainte-Suzanne → CINOR

- **Destinataire :** CINOR (Communauté Intercommunale du Nord de la Réunion)
- **Statut :** 🟠 à envoyer
- **Suivi :** date d'envoi — · relance — · réponse —

## Contexte (audit)

Demande **déjà identifiée, jamais envoyée**. Le zonage PLU (règlement graphique) de **Sainte-Marie**
et **Sainte-Suzanne** n'est pas disponible en vecteur exploitable via le GPU au niveau attendu ; la
CINOR, compétente en planification sur son territoire (Saint-Denis, Sainte-Marie, Sainte-Suzanne),
détient le SIG source.

**Ce que ça débloque :** compléter le **zonage PLU** (`plu_gpu_zone` / `parcel_zone_plu`) sur ces
deux communes → le **scoring cascade zonage**, la **faisabilité**, et le **simulateur PLU** (bascule
de zone) y gagnent une couverture réelle, au lieu d'un repli/estimation.

---

## Lettre

**[Expéditeur — à compléter]**
LABUSE — [raison sociale / SIREN]
[adresse postale]
Courriel : kampusreunion@gmail.com — Tél. : [—]

[Lieu], le [date]

**Monsieur/Madame le Président de la CINOR**
[adresse du siège — Sainte-Clotilde, à compléter]

*À l'attention du service en charge de la planification / de l'urbanisme (SIG).*

**Objet :** Demande de communication et de réutilisation du zonage PLU (SIG) des communes de Sainte-Marie et Sainte-Suzanne

Madame, Monsieur le Président,

LABUSE édite un outil professionnel d'analyse foncière et d'urbanisme à La Réunion, à destination des opérateurs de l'aménagement. L'outil agrège exclusivement des données publiques et restitue chacune avec sa source et son millésime, pour éclairer l'analyse d'une parcelle — le **zonage du PLU** en étant la base.

Nous sollicitons la **communication et l'autorisation de réutilisation** du **règlement graphique (zonage) au format SIG** des documents d'urbanisme en vigueur des communes de **Sainte-Marie** et **Sainte-Suzanne** :

- **format SIG** conforme au standard **CNIG** (Shapefile ou GeoJSON), avec les entités de zonage
  (U, AU, A, N et sous-zones) et, si disponibles, les **prescriptions** associées ;
- accompagné du **millésime** (document approuvé, date) et de la **source** ;
- **sous Licence Ouverte (Etalab 2.0)** ou licence de réutilisation équivalente.

**Usage prévu**, que nous nous engageons à respecter : affichage **informatif** du zonage à l'échelle de la parcelle, avec **citation systématique de la source (CINOR) et du millésime**, la portée opposable restant celle du document d'urbanisme et du certificat d'urbanisme. Aucune revente de la donnée brute ; aucune modification de la géométrie source.

Cette demande s'inscrit dans le **droit de réutilisation des informations publiques** (Code des relations entre le public et l'administration, art. L. 321-1 et suivants), réutilisation par défaut sous Licence Ouverte (décret n° 2017-638). Nous notons que ces documents ont vocation à figurer au **Géoportail de l'Urbanisme** ; à défaut d'y être disponibles en vecteur exploitable, nous vous en sollicitons la communication directe.

Nous restons à votre disposition pour préciser le cadre technique. En vous remerciant par avance, je vous prie d'agréer, Madame, Monsieur le Président, l'expression de ma haute considération.

**[Nom, qualité]**
LABUSE

---

## Notes pratiques

- **Vérifier l'adresse** du siège CINOR (Sainte-Clotilde) et adresser au **service urbanisme / SIG**
  via le Président.
- À réception : consigner **licence + millésime + format**, puis ingérer au standard (mise à jour
  `plu_gpu_zone` / `parcel_zone_plu`, catalogue + radar) pour ces deux communes.
