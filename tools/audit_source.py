#!/usr/bin/env python3
"""Audit the models.dev cache exactly the way generate.py filters it."""
import json, os, datetime, sys

PATHS = {
    "generate.py target": os.path.expandvars(r"%LOCALAPPDATA%\hermes\models_dev_cache.json"),
    "profile cache": r"C:\Users\matia\AppData\Local\hermes\profiles\pricewatch\models_dev_cache.json",
}


def audit(label, path):
    d = json.load(open(path, encoding="utf-8"))
    provs = len(d)
    total = 0
    text_models = 0
    rows = []
    for pid, prov in d.items():
        if not isinstance(prov, dict):
            continue
        pname = prov.get("name") or pid
        for mid, m in (prov.get("models") or {}).items():
            total += 1
            if not isinstance(m, dict):
                continue
            mods = m.get("modalities") or {}
            if "text" not in (mods.get("input") or []) or "text" not in (mods.get("output") or []):
                continue
            text_models += 1
            if not (m.get("limit") or {}).get("context"):
                continue
            cost = m.get("cost") or {}
            if cost.get("input") is None or cost.get("output") is None:
                continue
            rows.append({
                "provider_id": pid,
                "provider": pname,
                "model_id": mid,
                "name": m.get("name") or mid,
                "input": round(float(cost["input"]), 4),
                "output": round(float(cost["output"]), 4),
                "context": (m.get("limit") or {}).get("context") or 0,
                "family": m.get("family") or "",
                "release_date": (m.get("release_date") or "")[:10],
            })
    print("== %s ==" % label)
    print("  path=%s" % path)
    print("  size=%s mtime=%s" % (format(os.path.getsize(path), ","),
          datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")))
    print("  providers=%d raw_model_entries=%d text_in_out=%d priced_rows=%d priced_providers=%d"
          % (provs, total, text_models, len(rows), len({r["provider"] for r in rows})))
    return d, rows


if __name__ == "__main__":
    for label, p in PATHS.items():
        d, rows = audit(label, p)
        # inspect metadata that could give a source date
        meta = {k: v for k, v in d.items() if not (isinstance(v, dict) and "models" in v)}
        if meta:
            print("  non-provider top-level keys: %s" % list(meta)[:10])
        if rows:
            dates = [r["release_date"] for r in rows if r["release_date"]]
            print("  latest release_date in data: %s" % (max(dates) if dates else "none"))
