import json,urllib.request,urllib.error,csv,pathlib
OUT=pathlib.Path("/Users/openclaw/Desktop/labuse-nu3-p/docs/audit-2026-11/nu-3/P/out")
PDFDIR=OUT/"pdf"
idus=[r["idu"] for r in csv.DictReader(open(OUT/"parcelles.csv"))]
for idu in idus:
    body={"idus":[idu],"type_projet":"collectif","objectif":"equilibre","stationnement":"aerien","terrain":"libere"}
    req=urllib.request.Request("http://127.0.0.1:9440/modules/etude/pdf",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=180) as r:
            blob=r.read(); ct=r.headers.get_content_type()
            if "pdf" in ct:
                (PDFDIR/f"{idu}__etude-faisabilite.pdf").write_bytes(blob)
                print(f"{idu} etude-faisa -> 200 {len(blob)}o")
            else: print(f"{idu} etude-faisa -> {ct} {blob[:120]}")
    except urllib.error.HTTPError as e:
        try: msg=json.loads(e.read()).get("detail"); msg=msg.get("message") if isinstance(msg,dict) else msg
        except: msg="?"
        print(f"{idu} etude-faisa -> {e.code} :: {str(msg)[:110]}")
    except Exception as e:
        print(f"{idu} etude-faisa -> ERR {str(e)[:80]}")
