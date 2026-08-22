# DETTE — Hauteur PLU : zones « non renseignée », renvois, gel

**M130-12 (rattrapage).** Consigne ce qui sort « hauteur non renseignée au PLU
calibré » — jamais un trou silencieux — et les valeurs réelles connues mais non
gravées.

**M131 (apurement).** Us + 2AUa–e (Le Tampon) sont **lues et gravées** (sortent de
dette, cf. §1). Les renvois `Uazi`/`Ucm` reçoivent leur mention « via renvoi »
(§3 apuré). **Une nouvelle dette apparaît** : le gel implicite par défaut (§4).

---

## 1. Le mécanisme `zones_au_st` fabriquait une hauteur (corrigé + apuré)

**Défaut (corrigé `plu_rules.py`, M130-12)** : les zones portées par `zones_au_st`
(secteurs de transition / gel : `AU*st`, `2AU*`, `Us`, `AU0*`) recevaient
`hf_m = float(st.get("hauteur_max_m", 4))` — soit **4 m codé en dur** quand le
YAML ne définit pas `hauteur_max_m`. **Aucune** commune ne le définit → le 4 m
n'était **jamais** une règle lue au règlement, mais un repli du schéma, que le
YAML Saint-Pierre déclare lui-même **INEXACT**. C'était la valeur-signature du
mécanisme. **Correctif** : absence de `hauteur_max_m` = absence de règle →
`hf_m = None` (« non renseignée au PLU calibré »). Le repli 4 m reste **supprimé**
(vérifié M131 : aucun `hauteur_max_m", 4` ni équivalent dans `plu_rules.py`).

### Apurement M131 — valeurs RÉELLES lues et gravées

Ces zones **portent** une hauteur au règlement ; elles ont migré du mécanisme
`zones_au_st` vers des **entrées `zones:` propres** portant `he_m`/`hf_m` +
`hauteur_src` **et** `constructible_neuf: false` (gel conservé). Sortent de dette :

| Commune | Zone | hé / hf | Source gravée | Gel |
|---|---|---|---|---|
| Saint-Pierre (97416) | `Us` | 6 / 11 | `Art. Us3 §5 « 5/ Hauteur — Règle générale », p.134` | conservé (`constructible_neuf: false`) |
| Le Tampon (97422) | `2AUa` | 21 / 25 | `Art. Ua10.2, p.16` via renvoi (ZONE AUindicée, p.83) | conservé |
| Le Tampon (97422) | `2AUb` | 13 / 17 | `Art. Ub10.2, p.31` via renvoi | conservé |
| Le Tampon (97422) | `2AUc` | 9 / 13 | `Art. Uc10.2, p.46` via renvoi | conservé |
| Le Tampon (97422) | `2AUd` | 7 / 11 | `Art. Ud10.2, p.61` via renvoi | conservé |
| Le Tampon (97422) | `2AUe` | 12 / **—** | `Art. Ue10.2, p.75-76` via renvoi | conservé |

Notes de lecture :
- **`Us`** : la citation d'origine « p.130 » était **imprécise** (p.130 = `Us1`
  destinations, chap. 1). La hauteur est `Us3 §5`, **p.134** (chap. 2). La seule
  dérogation (équipements publics 8/13) est une **autre destination**, non gravée
  pour le logement — convention `Uf3.5`.
- **`2AU*`** : hauteur **par renvoi**. L'`Art. AUindicée 10, p.86` (« se reporter
  au règlement de la zone U en indice ») → article `U`-indice. L'`Art. 2.2.3, p.84`
  servi jusqu'ici est l'**ouverture / phasage**, **pas** la hauteur. Offset
  PDF↔imprimée **+2** sur ce document (imprimée p.83 = PDF p.85). Libellé unique
  « via renvoi (ZONE AUindicée, p.83) », aligné sur les `1AU`.
- **`2AUe`** : le règlement `Ue10.2` ne fixe que l'**égout (12 m)** ; **faîtage
  non précisé** → `hf_m: null`, rendu « faîtage non réglementé ». **Rien inféré.**

### Reste en dette (non lu / partiel)

- **`AU0*` (Saint-Pierre : AU01/AU02/AU03/AU0c-1)** : gel `zones_au_st` conservé,
  hauteur **non lue** → « non renseignée ». Construction interdite ; hauteur à
  instruire (règle d'annexes éventuelle).
- **`2AUe` faîtage** : partiel (égout seul). Non un trou : la règle égout est lue,
  le faîtage est **absent du règlement** `Ue10.2`.

---

## 2. Zones A / N — hauteur non extraite (inchangé)

`config/plu_saint_pierre.yaml` **ne calibre que les zones constructibles U / AU**.
Les zones **A / N** n'y sont pas → `resolve_zone` retombe sur l'estimation
générique (he = hf = None) → « non renseignée au PLU calibré ». Sur P3 :
Saint-Pierre `A` · `N`. **On ne sait pas** si le règlement chiffre une hauteur
A / N (chapitres existants, hauteur non extraite). Panne ≠ absence : « non
renseignée au PLU calibré » est l'état honnête d'une donnée absente du calibrage.
Pour lever : lire les chap. A / N et graver (ou marquer « non réglementée au
règlement, chap. X p.Y », fait sourcé).

---

## 3. Renvois servis sans mention « via renvoi » — APURÉ (M131, Phase C)

Cosmétique d'affichage, aucune valeur ni source fausse. **Corrigé** : le libellé
« via renvoi » est désormais porté par les deux `hauteur_src` (affichage seul,
article et valeur inchangés) :

- **`Uazi` (Saint-Pierre)** → `Art. Ua3.5, p.177 (règle générale) via renvoi
  (secteur Uazi régi par le chapitre « zone Ua et AUazi »)`.
- **`Ucm` (Le Tampon)** → `Art. Uc10.2, p.46 via renvoi (indice « m » régi par les
  règles chiffrées de la zone Uc — « m » n'ajoute aucune règle de hauteur)`.

Aligné sur `1AUb` (« via renvoi (ZONE AUindicée, p.83) ») et sur les `2AU*` gravés.

---

## 4. Dette NOUVELLE (M131) — gel implicite par défaut sur les entrées `zones:`

**Mécanisme.** Pour graver une hauteur PAR ZONE sur une zone gelée sans perdre le
gel, M131 a autorisé **une seule** modification de `plu_rules.py` : `_to_rules`
lit désormais `constructible_neuf=v.get("constructible_neuf", True)`. Le gel d'une
entrée `zones:` **ne tient donc QUE par la présence explicite** de la clé
`constructible_neuf: false` dans le YAML.

**Le piège.** Le **défaut est `True`**. Sur une zone qui doit rester gelée
(famille `AU*st` : `Us`, `2AU*`, `AU0*`), **OMETTRE** `constructible_neuf: false`
dans son entrée `zones:` la rend **constructible en silence** — la hauteur est
gravée mais le gel disparaît, sans aucune erreur ni signal. La ligne SDP du PDF
projet vient du **cache** `parcel_residuel` (pas de `resolve_zone` en direct) →
au rendu du projet seul, la régression **ne se voit pas** ; elle frappe la fiche,
le dossier et le **prochain recalcul batch** (`constructible_neuf=True` en direct).

**Zones concernées** (toute entrée `zones:` sur une zone de `zones_au_st` /
famille AU\*st) : aujourd'hui `Us` (97416), `2AUa–e` (97422). Demain toute zone
gelée qu'on gravera.

**Vérification à REFAIRE à chaque nouvelle entrée `zones:` sur une zone AU\*st** :
1. l'entrée porte-t-elle bien `constructible_neuf: false` ? (sinon gel perdu) ;
2. inventaire gel avant/après : dumper `resolve_zone(code, commune).constructible_neuf`
   pour **toutes** les zones des deux communes, graver, redumper, differ. **Toute**
   zone qui passe à `True` = échec → stop. (Procédure M131 : `/tmp/gel_before.json`
   → `/tmp/gel_after.json` ; attendu strict : seules `he/hf` bougent, jamais un
   `constructible_neuf`.)

**Traitement de fond (hors périmètre M131)** : un gel exprimé par un défaut
implicite est fragile. Piste = signal de gel **indépendant** (liste `zones_au_st`
consultée même quand une entrée `zones:` existe, ou clé obligatoire sur les zones
AU\*st). Rejoint la conflation `Us`/`AU0` de **M130-6 F.2** et le diagnostic
**M131 Phase D** (libellé « zone fermée à l'urbanisation » imprécis pour `Us`).
