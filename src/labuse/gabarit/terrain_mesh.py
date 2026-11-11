"""GABARIT-3D-1 (pilote, étape 1 ter) — MAILLAGE triangulé du terrain, fixé côté serveur.

Verrou Astra : il n'y a qu'UNE surface, un maillage de TRIANGLES, construit sur les pixels NATIFS du
MNT. Les coupes sont l'INTERSECTION avec ces faces — EXACTEMENT celles que la visionneuse affichera.
Une maille non plane (sommets 0,0,0,4) est donc rendue par deux faces planes (pas une nappe bilinéaire).

Un `TerrainMesh` enveloppe le tableau natif (NaN = lacune) et expose :
  - ``altitude(x, y)`` : altitude PAR INTERSECTION avec la face triangulaire contenant le point
    (None si la face touche une lacune ou si le point est hors maillage) ;
  - ``faces(ox, oy, bounds)`` : sommets + triangles en repère local (pour la visionneuse), les faces
    touchant une lacune étant retirées (trous conservés).

Le pas des sommets vaut ``step × pas_natif`` : ``step=1`` sur la parcelle (faces 1 m), ``step=2`` sur
le voisinage (faces 2 m). Le raccord 1 m / 2 m = deux jeux de faces juxtaposés, lus par le même code.
"""
from __future__ import annotations

import math
from typing import Optional


class TerrainMesh:
    def __init__(self, arr, ox: float, oy: float, pas: float, step: int = 1):
        import numpy as np
        self.a = np.asarray(arr, dtype="float64")
        self.a[(self.a <= -1000.0) | ~np.isfinite(self.a)] = np.nan
        self.ox, self.oy, self.pas, self.step = ox, oy, pas, step      # (ox,oy) = coin HAUT-GAUCHE
        self.ny, self.nx = self.a.shape
        self.vpas = pas * step                                         # pas des sommets (m)

    # — sommet (I,J) = pixel (I·step, J·step), à son centre —
    def _z(self, I: int, J: int):
        r, c = I * self.step, J * self.step
        if r < 0 or c < 0 or r >= self.ny or c >= self.nx:
            return None
        v = self.a[r, c]
        return None if (v != v) else float(v)                         # NaN → None

    def altitude(self, x: float, y: float) -> Optional[float]:
        """Altitude par intersection avec la face triangulaire contenant (x,y). None = lacune/hors maille."""
        fj = (x - self.ox - 0.5 * self.pas) / self.vpas               # colonne-sommet fractionnaire
        fi = (self.oy - y - 0.5 * self.pas) / self.vpas               # ligne-sommet fractionnaire
        J, I = math.floor(fj), math.floor(fi)
        tc, tr = fj - J, fi - I
        z00, z10 = self._z(I, J), self._z(I, J + 1)
        z01, z11 = self._z(I + 1, J), self._z(I + 1, J + 1)
        # deux triangles par maille, diagonale P00–P11 (même découpe que les faces exportées)
        if tc >= tr:                                                   # triangle (P00, P10, P11)
            if None in (z00, z10, z11):
                return None
            return z00 * (1 - tc) + z10 * (tc - tr) + z11 * tr
        if None in (z00, z11, z01):                                   # triangle (P00, P11, P01)
            return None
        return z00 * (1 - tr) + z11 * tc + z01 * (tr - tc)

    def profil(self, ox: float, oy: float, ux: float, uy: float, L: float) -> list[dict]:
        """Profil le long de la ligne par FRANCHISSEMENT DES FACES (pas par échantillonnage au mètre) :
        un point à CHAQUE arête de triangle traversée → une crête entre deux pixels est retrouvée. Entre
        deux franchissements la face est plane donc le profil est exact. Lacune = None (reste une lacune).

        Arêtes du maillage (pas natif = self.vpas) : verticales x=const (colonnes de sommets),
        horizontales y=const (lignes de sommets), diagonales x+y=const (découpe P00–P11 de chaque maille)."""
        p = self.vpas
        ds = {0.0, round(L, 6)}
        x0, y0 = ox, oy
        x1, y1 = ox + ux * L, oy + uy * L
        # verticales : x = self.ox + (k+0.5)*p
        if abs(ux) > 1e-12:
            k_lo = math.floor((min(x0, x1) - self.ox) / p - 0.5)
            k_hi = math.ceil((max(x0, x1) - self.ox) / p - 0.5)
            for k in range(k_lo, k_hi + 1):
                d = (self.ox + (k + 0.5) * p - x0) / ux
                if 0 <= d <= L:
                    ds.add(round(d, 6))
        # horizontales : y = self.oy - (k+0.5)*p
        if abs(uy) > 1e-12:
            k_lo = math.floor((self.oy - max(y0, y1)) / p - 0.5)
            k_hi = math.ceil((self.oy - min(y0, y1)) / p - 0.5)
            for k in range(k_lo, k_hi + 1):
                d = (self.oy - (k + 0.5) * p - y0) / uy
                if 0 <= d <= L:
                    ds.add(round(d, 6))
        # diagonales : x + y = (self.ox + self.oy) + m*p
        if abs(ux + uy) > 1e-12:
            base = self.ox + self.oy
            s0, s1 = x0 + y0, x1 + y1
            m_lo = math.floor((min(s0, s1) - base) / p)
            m_hi = math.ceil((max(s0, s1) - base) / p)
            for m in range(m_lo, m_hi + 1):
                d = (base + m * p - s0) / (ux + uy)
                if 0 <= d <= L:
                    ds.add(round(d, 6))
        out = []
        for d in sorted(ds):
            z = self.altitude(x0 + ux * d, y0 + uy * d)
            out.append({"d": round(d, 2), "z": (None if z is None else round(z, 2))})
        return out

    def faces(self, lox: float, loy: float, bounds=None) -> dict:
        """Sommets (x,y,z local) + triangles (indices). `bounds`=(minx,miny,maxx,maxy) 2975 : limite le
        maillage à la fenêtre (pour juxtaposer 1 m / 2 m sans recouvrement ni sommets inutiles)."""
        nI = (self.ny - 1) // self.step + 1
        nJ = (self.nx - 1) // self.step + 1
        # plage de sommets (I,J) couvrant `bounds` (+1 pour fermer les faces de bord)
        Ia, Ib, Ja, Jb = 0, nI, 0, nJ
        if bounds is not None:
            Ja = max(0, int(math.floor((bounds[0] - self.ox - 0.5 * self.pas) / self.vpas)))
            Jb = min(nJ, int(math.ceil((bounds[2] - self.ox - 0.5 * self.pas) / self.vpas)) + 2)
            Ia = max(0, int(math.floor((self.oy - bounds[3] - 0.5 * self.pas) / self.vpas)))
            Ib = min(nI, int(math.ceil((self.oy - bounds[1] - 0.5 * self.pas) / self.vpas)) + 2)
        verts, idx = [], {}
        for I in range(Ia, Ib):
            for J in range(Ja, Jb):
                z = self._z(I, J)
                if z is None:
                    continue
                x = self.ox + (J * self.step + 0.5) * self.pas
                y = self.oy - (I * self.step + 0.5) * self.pas
                idx[(I, J)] = len(verts)
                verts.append([round(x - lox, 2), round(y - loy, 2), round(z, 2)])
        tris = []
        for I in range(Ia, Ib - 1):
            for J in range(Ja, Jb - 1):
                p00, p10 = idx.get((I, J)), idx.get((I, J + 1))
                p01, p11 = idx.get((I + 1, J)), idx.get((I + 1, J + 1))
                if None not in (p00, p10, p11):
                    tris.append([p00, p10, p11])
                if None not in (p00, p11, p01):
                    tris.append([p00, p11, p01])
        return {"vertices": verts, "triangles": tris, "pas_m": self.vpas}
