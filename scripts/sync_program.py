#!/usr/bin/env python3
"""Sync ONLY the published Program tab into a public, validated program.json."""
import csv, hashlib, io, json, os, pathlib, urllib.request
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTH2Kcf8-n8PRmqhyV8ynIyjueE1sIUGz4tuvEFKHpTJwB93klyVRy6BdkVSDMl2XcyuBfOrxoUpm6x/pub?gid=1105667006&single=true&output=csv"
with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent":"Forma80-program-sync/1.0"}), timeout=25) as resp:
    raw = resp.read(200000)
rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
required = {"Версия","Дата начала","День","Порядок","ID упражнения","Подходы","Мин. повторов","Макс. повторов","Вес, кг","Статус"}
if not rows or not required.issubset(rows[0]): raise ValueError("Unexpected published CSV columns")
approved = [r for r in rows if r["Статус"].strip().lower() == "утверждено"]
if len(approved) != 17: raise ValueError("Expected exactly 17 approved exercises")
versions = {r["Версия"].strip() for r in approved}
dates = {r["Дата начала"].strip() for r in approved}
if len(versions)!=1 or len(dates)!=1: raise ValueError("Inconsistent versions/dates")
date = dates.pop()
if len(date)!=10 or date[4]!='-' or date[7]!='-': raise ValueError("Invalid effective date")
days = {"A":[], "B":[]}; exercises={}; positions={"A":set(),"B":set()}
for r in approved:
    day=r["День"].strip().upper().replace("ДЕНЬ ","").replace("А","A").replace("В","B")
    if day not in days: raise ValueError("Unexpected day")
    eid=r["ID упражнения"].strip()
    if not eid.isascii() or not eid.isalnum() or eid in exercises: raise ValueError("Invalid or duplicate exercise ID")
    pos=int(r["Порядок"])
    if pos in positions[day]: raise ValueError("Duplicate position")
    positions[day].add(pos)
    def number(v): return float(str(v).strip().replace(",","."))
    sets=int(r["Подходы"]); minimum=int(r["Мин. повторов"]); maximum=int(r["Макс. повторов"]); weight=number(r["Вес, кг"])
    if not (1<=sets<=10 and 0<=minimum<=maximum<=100 and 0<=weight<=500): raise ValueError("Out of range")
    exercises[eid]=[sets,minimum,maximum,weight]
    days[day].append((pos,eid))
if len(days["A"])!=9 or len(days["B"])!=8: raise ValueError("Unexpected day sizes")
days={day:[eid for _,eid in sorted(entries)] for day,entries in days.items()}
payload={"schema":1,"effectiveDate":date,"days":days,"exercises":exercises}
canonical=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":"))
payload["version"]="v"+str(int(hashlib.sha256(canonical.encode()).hexdigest()[:12],16))
target=pathlib.Path("program.json")
content=json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
if not target.exists() or target.read_text()!=content: target.write_text(content)
