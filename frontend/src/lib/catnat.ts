// OUTIL-COMMUNES-FIX-6 LOT 3 — « et N autres » du détail CatNat.
// Le détail des arrêtés est tronqué (requête LIMIT) et seules `montres` entrées sont affichées. Le
// nombre d'entrées RESTANTES doit se calculer sur le TOTAL de la source (`totalPerils`, le count(*) par
// péril de `catnat_arretes`), pas sur la longueur de la liste tronquée — sinon « et 6 autres » alors
// qu'il en reste 18 (Saint-Paul : 24 au total − 6 affichées).
export function catnatReste(
  totalPerils: number | null | undefined,
  detailLen: number,
  montres: number,
): number {
  // LOT 0 (filet) : implémentation COURANTE (buggée) — calcule sur la liste tronquée. Corrigée au LOT 3.
  void totalPerils
  return detailLen - montres
}
