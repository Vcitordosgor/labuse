"""LOT 1 — vérifie, pour TOUTE zone de Saint-Paul servie à des parcelles, la page de mixité citée :
« pp. 14-15 » n'apparaît QUE pour le livret 1 (zones U1*). Zones sans page connue signalées."""
import psycopg, sys
from collections import defaultdict
sys.path.insert(0, 'src')
from labuse.faisabilite.bilan import _zone_mixite_regle

cx = psycopg.connect('postgresql://openclaw@localhost:5432/labuse', connect_timeout=15)
cx.execute('SET default_transaction_read_only = on')
rows = cx.execute("""SELECT z.zone_lib, count(*) FROM parcel_zone_plu z JOIN parcels p ON p.idu=z.idu
    WHERE p.commune='Saint-Paul' GROUP BY z.zone_lib ORDER BY z.zone_lib""").fetchall()

bad_14_15 = []       # zones hors livret 1 citant pp.14-15
no_page = []         # zones sans page connue
pages = defaultdict(int)
total_parc = 0
for zone, n in rows:
    r = _zone_mixite_regle("Saint-Paul", zone, None)
    page = r["page"] if r else None
    total_parc += n
    pages[page] += n
    livret1 = zone.startswith("U1") or zone.startswith("AU1")
    if page == "pp. 14-15" and not livret1:
        bad_14_15.append((zone, n))
    if page is None:
        no_page.append((zone, n))

print(f"Zones Saint-Paul : {len(rows)} ; parcelles : {total_parc}")
print("\nPages citées (par nb de parcelles) :")
for pg, n in sorted(pages.items(), key=lambda kv: -kv[1]):
    print(f"   {str(pg):14} {n}")
print(f"\n« pp. 14-15 » HORS livret 1 : {len(bad_14_15)} zone(s)  ->  {bad_14_15}")
print(f"Zones SANS page connue (aucune page citée) : {len(no_page)} zone(s)")
for z, n in no_page:
    print(f"   {z:10} {n} parcelles")
