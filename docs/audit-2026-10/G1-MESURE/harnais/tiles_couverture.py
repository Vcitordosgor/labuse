#!/usr/bin/env python3
"""G1-MESURE — couverture de tuiles + poids octets (déterministe, insensible à la charge).

Calcule, pour la vue île à un zoom donné, l'ensemble des tuiles slippy couvrant le canvas
(1030×844, padding 40 → viewport 950×764), puis mesure le poids octets servi par deux sources :
`parcels-ile` (/map/tiles/{z}/{x}/{y}.pbf) et `limites_parcelles` (/map/tiles/limites_parcelles/…).
On mesure RAW (sans compression), BROTLI et GZIP via Accept-Encoding — les octets sont
déterministes (aucun temps mesuré)."""
import math, subprocess, sys

API = "http://127.0.0.1:8720"
ILE = (55.20, -21.42, 55.87, -20.85)  # w,s,e,n  (= ILE_BOUNDS de MapView.tsx)
CANVAS_W, CANVAS_H = 1030, 844
PAD = 40
VW, VH = CANVAS_W - 2*PAD, CANVAS_H - 2*PAD  # 950 x 764

def merc_x(lon): return (lon + 180.0) / 360.0
def merc_y(lat):
    s = math.sin(math.radians(lat))
    return 0.5 - math.log((1+s)/(1-s)) / (4*math.pi)

def fit_zoom():
    """zoom fractionnaire qui fait tenir ILE dans VW×VH (logique maplibre cameraForBounds)."""
    w,s,e,n = ILE
    dx = merc_x(e) - merc_x(w)
    dy = merc_y(s) - merc_y(n)  # y croît vers le sud
    zx = math.log2(VW / (256*dx))
    zy = math.log2(VH / (256*dy))
    return min(zx, zy)

def tiles_for(zoom_int, bounds=ILE):
    """tuiles slippy couvrant ILE au niveau entier zoom_int."""
    w,s,e,n = bounds
    nt = 2**zoom_int
    x0 = int(merc_x(w) * nt); x1 = int(merc_x(e) * nt)
    y0 = int(merc_y(n) * nt); y1 = int(merc_y(s) * nt)
    return [(zoom_int, x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)]

def tile_bytes(path, enc=None):
    cmd = ["curl","-s","-o","/dev/null","-w","%{size_download}", f"{API}{path}"]
    if enc: cmd[1:1] = ["-H", f"Accept-Encoding: {enc}"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    try: return int(out)
    except: return 0

def measure(source, zoom_int):
    tiles = tiles_for(zoom_int)
    raw=br=gz=0
    for (z,x,y) in tiles:
        if source == "parcels":
            p = f"/map/tiles/{z}/{x}/{y}.pbf"
        else:
            p = f"/map/tiles/{source}/{z}/{x}/{y}.pbf"
        raw += tile_bytes(p)
        br  += tile_bytes(p, "br")
        gz  += tile_bytes(p, "gzip")
    return {"source":source, "z":zoom_int, "n":len(tiles),
            "raw":raw, "br":br, "gz":gz, "tiles":[f"{z}/{x}/{y}" for z,x,y in tiles]}

if __name__ == "__main__":
    print(f"fit_zoom(ILE, {VW}x{VH}) = {fit_zoom():.3f}  → tuile niveau {math.floor(fit_zoom())}")
    print("z9 parcels tiles:", [f"{z}/{x}/{y}" for z,x,y in tiles_for(9)])
