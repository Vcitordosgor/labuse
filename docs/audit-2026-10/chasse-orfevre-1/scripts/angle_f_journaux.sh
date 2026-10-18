#!/bin/sh
# ANGLE F — collecte & analyse des journaux de prod LABUSE (30 jours).
# LECTURE SEULE sur le VPS : uniquement journalctl / cat / zcat / grep / ls / df.
# Les copies et analyses se font sur le Mac dans /tmp/orfevre-logs/.
# Usage : sh angle_f_journaux.sh   (ssh labuse-vps déjà configuré)
set -eu
DEPUIS="2026-09-18"
OUT=/tmp/orfevre-logs
mkdir -p "$OUT"

echo "── 1. Topologie ──────────────────────────────────────────────"
ssh labuse-vps 'systemctl list-units --type=service --all | grep -iE "labuse|caddy|postgres|docker";
  sudo docker ps 2>/dev/null; cat /etc/cron.d/labuse; ls /etc/cron.d/;
  ls -la /var/log/labuse/ /var/log/labuse/jobs/ /var/log/caddy/ /var/log/postgresql/;
  systemctl cat labuse.service; journalctl --list-boots | tail -3; sudo journalctl --disk-usage; df -h /'

echo "── 2. Rapatriement des logs ──────────────────────────────────"
ssh labuse-vps "sudo journalctl -u labuse --since '$DEPUIS' --no-pager -o short-iso" > "$OUT/labuse-journal.log"
ssh labuse-vps 'sudo cat /var/log/caddy/access.log | gzip -c' > "$OUT/caddy-access.log.gz"
ssh labuse-vps 'sudo sh -c "cat /var/log/postgresql/postgresql-18-main.log.1; cat /var/log/postgresql/postgresql-18-main.log";
  for f in 2 3 4 5; do sudo zcat /var/log/postgresql/postgresql-18-main.log.$f.gz; done' > "$OUT/postgres.log" 2>&1
ssh labuse-vps 'cd /var/log/labuse && for f in *.log jobs/*.log; do echo "===== $f ====="; cat "$f"; done' > "$OUT/labuse-joblogs.txt"
ssh labuse-vps "sudo journalctl --since '$DEPUIS' --no-pager -o short-iso _COMM=cron | grep CMD" > "$OUT/cron-full.txt"

echo "── 3. API : restarts, 500, tracebacks groupés ────────────────"
grep -E "systemd\[1\]: (Started|Stopping) labuse" "$OUT/labuse-journal.log" || true
grep -E '" 500' "$OUT/labuse-journal.log" | awk '{print substr($1,1,10)}' | sort | uniq -c
# groupes de tracebacks par ligne d'exception finale (1re/dernière occurrence, compte)
awk '/Traceback \(most recent call last\)/ {intb=1; ts=substr($0,1,19)}
  intb { line=$0; sub(/^[^ ]+ [^ ]+ labuse\[[0-9]+\]: /,"",line);
    if (line !~ /^Traceback/ && line !~ /^ / && line !~ /^$/) { print ts "\t" line; intb=0 } }' \
  "$OUT/labuse-journal.log" | sort | awk -F"\t" '{c[$2]++; if(!($2 in f)) f[$2]=$1; l[$2]=$1}
  END{for(k in c) printf "%5d  %s → %s  %s\n", c[k], f[k], l[k], substr(k,1,150)}' | sort -rn
# erreurs hors fenêtre incident 06-07/10
awk '($0<"2026-10-06T18:00" || $0>"2026-10-07T04:00")' "$OUT/labuse-journal.log" \
  | grep -iE "error|warning" | grep -viE '(GET|POST|HEAD) /' \
  | sed -E 's/^[^ ]+ [^ ]+ labuse\[[0-9]+\]: //' | sort | uniq -c | sort -rn | head -30

echo "── 4. Jobs : échecs datés + régularité ───────────────────────"
ssh labuse-vps 'cd /var/log/labuse/jobs && for f in *.log; do
  echo "== $f : $(grep -c début "$f") débuts / $(grep -c "fin (code" "$f") fins";
  grep -E "fin \(code [^0]" "$f" | head -5; done'
# échecs datés (le wrapper n écrit pas de date sur la ligne d échec → on prend le dernier "début")
ssh labuse-vps 'awk "/début/{d=\$1} /en échec|ÉCHOUÉ|Traceback/{print FILENAME, d}" /var/log/labuse/jobs/*.log | sort -u | head -40'
# contrôle « cron a-t-il tiré ? » (ATTENTION : journald PERD des lignes — recouper avec le wrapper)
grep -oE "jobs run [a-z-]+" "$OUT/cron-full.txt" | sort | uniq -c

echo "── 5. Caddy : 5xx/4xx/latences (python3, flux) ───────────────"
zcat < "$OUT/caddy-access.log.gz" | python3 -c '
import sys, json, collections, datetime
W = datetime.datetime(2026,9,18,tzinfo=datetime.timezone(datetime.timedelta(hours=4))).timestamp()
tz = datetime.timezone(datetime.timedelta(hours=4))
st5=collections.Counter(); d5=collections.Counter(); u404=collections.Counter(); u401=collections.Counter(); slow=[]; cls=collections.Counter(); n=0
for line in sys.stdin:
    try: r=json.loads(line)
    except: continue
    if r.get("ts",0)<W: continue
    n+=1; s=r.get("status",0); req=r.get("request",{}); uri=req.get("uri","").split("?")[0]
    cls[s//100]+=1
    day=datetime.datetime.fromtimestamp(r["ts"],tz).strftime("%Y-%m-%d")
    if s>=500: st5[(s,uri)]+=1; d5[day]+=1
    elif s==404: u404[uri]+=1
    elif s==401: u401[uri]+=1
    if r.get("duration",0)>30: slow.append((day,uri,round(r["duration"],1),s))
print("total:",n,"classes:",dict(cls))
print("5xx/route:",st5.most_common(15)); print("5xx/jour:",sorted(d5.items()))
print("404 top:",u404.most_common(10)); print("401 top:",u401.most_common(10))
print(">30s:",len(slow), sorted(slow,key=lambda t:-t[2])[:10])'

echo "── 6. Système : OOM, pg, fail2ban, certs ─────────────────────"
ssh labuse-vps "sudo journalctl -k --since '$DEPUIS' --no-pager | grep -iE 'oom|out of memory|killed process' | head"
grep -E "ERROR|FATAL|PANIC" "$OUT/postgres.log" | grep -vE "terminating connection|is shutting down" \
  | sed -E 's/at character [0-9]+//' | awk '{d=substr($1,1,10); sub(/^[^A-Z]*/,""); c[d" "substr($0,1,110)]++}
  END{for(k in c) print c[k],k}' | sort | head -40
grep -E "VACUUM cannot" "$OUT/postgres.log"
ssh labuse-vps "sudo grep -hc 'Ban ' /var/log/fail2ban.log; sudo journalctl -u caddy --since '$DEPUIS' -p warning --no-pager | tail -5"
echo "Fini. Matière dans $OUT ; synthèse : brouillons/ANGLE-F.md"
