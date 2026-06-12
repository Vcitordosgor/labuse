# ANNEXE — Revue carte des seuils A/N et ER (lecture seule)

> Demandé par la DIRECTIVE de re-priorisation (§2). Triple cohorte issue de la ré-évaluation
> des 3 000 parcelles de Saint-Paul (rules `f81b35a`). But : Vic valide visuellement les seuils
> `an_hard_exclude_pct`=90 / `an_mixte_min_pct`=5 / `er_hard_exclude_pct`=50, et récupère les
> **10 réadmises** comme leads. Liens carte = OpenStreetMap au centroïde (fond cadastral via le calque BD Parcellaire).


## 1. Les 10 réadmises — `faux positif → à creuser` (leads à creuser)

Zonage mixte A/N + U/AU : exclues à tort sous l'ancien « A/N = exclusion totale », désormais reconnues partiellement constructibles (emprise clippée à la part U/AU).

| IDU | Sect./N° | Zones (part) | Opp. | Part inconstructible | Carte |
|---|---|---|---:|---|---|
| 97415000BK0062 | BK 62 | N 34%, N 4%, Nerl 30%, U1e 32% | 16 | 68 % | [carte](https://www.openstreetmap.org/?mlat=-20.98921&mlon=55.29348#map=19/-20.98921/55.29348) |
| 97415000BK0092 | BK 92 | N 67%, U1f 33% | 1 | 67 % | [carte](https://www.openstreetmap.org/?mlat=-20.99083&mlon=55.30014#map=19/-20.99083/55.30014) |
| 97415000BK0100 | BK 100 | Acu, N 74%, Nerl, U1f 26% | 8 | 74 % | [carte](https://www.openstreetmap.org/?mlat=-20.99137&mlon=55.30084#map=19/-20.99137/55.30084) |
| 97415000BT0016 | BT 16 | N, N 67%, Nerl, U1f 33% | 33 | 67 % | [carte](https://www.openstreetmap.org/?mlat=-21.00948&mlon=55.28230#map=19/-21.00948/55.28230) |
| 97415000BV0087 | BV 87 | Ncor 82%, U6c 18% | 24 | 82 % | [carte](https://www.openstreetmap.org/?mlat=-21.01401&mlon=55.28484#map=19/-21.01401/55.28484) |
| 97415000BV0199 | BV 199 | A 51%, Ncor 14%, U6c 35% | 17 | 65 % | [carte](https://www.openstreetmap.org/?mlat=-21.01977&mlon=55.28555#map=19/-21.01977/55.28555) |
| 97415000BV0206 | BV 206 | A 52%, U6c 48% | 60 | 52 % | [carte](https://www.openstreetmap.org/?mlat=-21.02064&mlon=55.28552#map=19/-21.02064/55.28552) |
| 97415000BV0310 | BV 310 | Ncor 75%, U6c 25% | 25 | 75 % | [carte](https://www.openstreetmap.org/?mlat=-21.01395&mlon=55.28518#map=19/-21.01395/55.28518) |
| 97415000BV0418 | BV 418 | Ncor 82%, U6c 18% | 24 | 82 % | [carte](https://www.openstreetmap.org/?mlat=-21.01411&mlon=55.28463#map=19/-21.01411/55.28463) |
| 97415000BV1521 | BV 1521 | A 90%, U6c 10% | 32 | 90 % | [carte](https://www.openstreetmap.org/?mlat=-21.02035&mlon=55.28515#map=19/-21.02035/55.28515) |

## 2. Les 17 « zonage mixte » (5–90 % A/N) — seuil `an_mixte_min_pct`/`an_hard_exclude_pct`

Surface partagée entre A/N (inconstructible) et U/AU (constructible). Statut conservé, mais capacité bornée à la portion U/AU. Inclut les 10 réadmises ci-dessus.

| IDU | Sect./N° | Zones (part) | Statut | Opp. | Carte |
|---|---|---|---|---:|---|
| 97415000BC0343 | BC 343 | N 78%, Ncu 1%, Nerl 3%, U4c 18% | faux_positif_probable | 27 | [carte](https://www.openstreetmap.org/?mlat=-20.99218&mlon=55.31529#map=19/-20.99218/55.31529) |
| 97415000BK0062 | BK 62 | N 34%, N 4%, Nerl 30%, U1e 32% | a_creuser | 16 | [carte](https://www.openstreetmap.org/?mlat=-20.98921&mlon=55.29348#map=19/-20.98921/55.29348) |
| 97415000BK0092 | BK 92 | N 67%, U1f 33% | a_creuser | 1 | [carte](https://www.openstreetmap.org/?mlat=-20.99083&mlon=55.30014#map=19/-20.99083/55.30014) |
| 97415000BK0100 | BK 100 | Acu, N 74%, Nerl, U1f 26% | a_creuser | 8 | [carte](https://www.openstreetmap.org/?mlat=-20.99137&mlon=55.30084#map=19/-20.99137/55.30084) |
| 97415000BK0101 | BK 101 | N 47%, U1f 53% | faux_positif_probable | 12 | [carte](https://www.openstreetmap.org/?mlat=-20.99117&mlon=55.30088#map=19/-20.99117/55.30088) |
| 97415000BR0088 | BR 88 | N, Nerl 6%, U1b 94% | faux_positif_probable | 25 | [carte](https://www.openstreetmap.org/?mlat=-21.01498&mlon=55.26489#map=19/-21.01498/55.26489) |
| 97415000BT0016 | BT 16 | N, N 67%, Nerl, U1f 33% | a_creuser | 33 | [carte](https://www.openstreetmap.org/?mlat=-21.00948&mlon=55.28230#map=19/-21.00948/55.28230) |
| 97415000BV0087 | BV 87 | Ncor 82%, U6c 18% | a_creuser | 24 | [carte](https://www.openstreetmap.org/?mlat=-21.01401&mlon=55.28484#map=19/-21.01401/55.28484) |
| 97415000BV0199 | BV 199 | A 51%, Ncor 14%, U6c 35% | a_creuser | 17 | [carte](https://www.openstreetmap.org/?mlat=-21.01977&mlon=55.28555#map=19/-21.01977/55.28555) |
| 97415000BV0206 | BV 206 | A 52%, U6c 48% | a_creuser | 60 | [carte](https://www.openstreetmap.org/?mlat=-21.02064&mlon=55.28552#map=19/-21.02064/55.28552) |
| 97415000BV0234 | BV 234 | AU6c, N 28%, U6c 72% | faux_positif_probable | 33 | [carte](https://www.openstreetmap.org/?mlat=-21.01866&mlon=55.28913#map=19/-21.01866/55.28913) |
| 97415000BV0310 | BV 310 | Ncor 75%, U6c 25% | a_creuser | 25 | [carte](https://www.openstreetmap.org/?mlat=-21.01395&mlon=55.28518#map=19/-21.01395/55.28518) |
| 97415000BV0418 | BV 418 | Ncor 82%, U6c 18% | a_creuser | 24 | [carte](https://www.openstreetmap.org/?mlat=-21.01411&mlon=55.28463#map=19/-21.01411/55.28463) |
| 97415000BV0834 | BV 834 | Nerl 32%, U6c 68% | faux_positif_probable | 31 | [carte](https://www.openstreetmap.org/?mlat=-21.01996&mlon=55.29123#map=19/-21.01996/55.29123) |
| 97415000BV0871 | BV 871 | Nerl 62%, U6c 38% | faux_positif_probable | 42 | [carte](https://www.openstreetmap.org/?mlat=-21.01990&mlon=55.29195#map=19/-21.01990/55.29195) |
| 97415000BV1361 | BV 1361 | A 17%, U6c 83% | a_creuser | 54 | [carte](https://www.openstreetmap.org/?mlat=-21.02100&mlon=55.28532#map=19/-21.02100/55.28532) |
| 97415000BV1521 | BV 1521 | A 90%, U6c 10% | a_creuser | 32 | [carte](https://www.openstreetmap.org/?mlat=-21.02035&mlon=55.28515#map=19/-21.02035/55.28515) |

## 3. Les 10 ER-HARD — emplacement réservé ≥ 50 % (`er_hard_exclude_pct`)

Emprise majoritairement grevée par un emplacement réservé public (servitude levable). 9/10 étaient déjà faux positifs par d'autres signaux ; à valider que l'exclusion est juste.

| IDU | Sect./N° | Statut | Opp. | Motif ER | Carte |
|---|---|---|---:|---|---|
| 97415000BO0376 | BO 376 | faux_positif_probable | 0 | Emplacement réservé 88 : Extension de la gare routière (100 %) — emp… | [carte](https://www.openstreetmap.org/?mlat=-21.00951&mlon=55.27510#map=19/-21.00951/55.27510) |
| 97415000BO0377 | BO 377 | faux_positif_probable | 0 | Emplacement réservé 88 : Extension de la gare routière (100 %) — emp… | [carte](https://www.openstreetmap.org/?mlat=-21.00979&mlon=55.27501#map=19/-21.00979/55.27501) |
| 97415000BO0378 | BO 378 | faux_positif_probable | 0 | Emplacement réservé 88 : Extension de la gare routière (100 %) — emp… | [carte](https://www.openstreetmap.org/?mlat=-21.00976&mlon=55.27511#map=19/-21.00976/55.27511) |
| 97415000BO0379 | BO 379 | faux_positif_probable | 0 | Emplacement réservé 88 : Extension de la gare routière (100 %) — emp… | [carte](https://www.openstreetmap.org/?mlat=-21.00970&mlon=55.27520#map=19/-21.00970/55.27520) |
| 97415000BO0641 | BO 641 | faux_positif_probable | 0 | Emplacement réservé 88 : Extension de la gare routière (100 %) — emp… | [carte](https://www.openstreetmap.org/?mlat=-21.00936&mlon=55.27509#map=19/-21.00936/55.27509) |
| 97415000BO0642 | BO 642 | faux_positif_probable | 0 | Emplacement réservé 88 : Extension de la gare routière (100 %) — emp… | [carte](https://www.openstreetmap.org/?mlat=-21.00949&mlon=55.27491#map=19/-21.00949/55.27491) |
| 97415000BP0699 | BP 699 | faux_positif_probable | 0 | Emplacement réservé 68 : Aménagement des réseaux et de la ruelle Ti … | [carte](https://www.openstreetmap.org/?mlat=-21.01243&mlon=55.26694#map=19/-21.01243/55.26694) |
| 97415000BT0024 | BT 24 | faux_positif_probable | 0 | Emplacement réservé 83 : Sécurisation du carrefour de la RD5 et du T… | [carte](https://www.openstreetmap.org/?mlat=-21.01184&mlon=55.27644#map=19/-21.01184/55.27644) |
| 97415000BT0025 | BT 25 | faux_positif_probable | 0 | Emplacement réservé 83 : Sécurisation du carrefour de la RD5 et du T… | [carte](https://www.openstreetmap.org/?mlat=-21.01192&mlon=55.27619#map=19/-21.01192/55.27619) |
| 97415000BT0026 | BT 26 | faux_positif_probable | 0 | Emplacement réservé 83 : Sécurisation du carrefour de la RD5 et du T… | [carte](https://www.openstreetmap.org/?mlat=-21.01206&mlon=55.27627#map=19/-21.01206/55.27627) |

---

**Lecture des seuils** : les réadmises (§1) montrent que `an_hard_exclude_pct`=90 évite d'exclure des terrains à moitié constructibles ; les ER-HARD (§3) que `er_hard_exclude_pct`=50 ne frappe que des emprises massivement grevées. Si un cas limite te paraît mal classé, dis-le — le seuil est un PLACEHOLDER ajustable.
