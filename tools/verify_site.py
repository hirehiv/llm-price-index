#!/usr/bin/env python3
"""Verify the built site end to end.

Checks, in order:
  1. api/*.json parse and match the catalog (counts, per-provider aggregates, blended math).
  2. index.html embeds the same number of rows as the API.
  3. Every HTML page returns 200 from a local `python -m http.server`.
  4. Every internal link/asset resolves (no 404s, no root-absolute hrefs).
  5. Provider pages: exactly TOP_N, each with 10 model rows and its real count.

Exit code 0 only when every check passes. Prints a machine-checkable summary.
"""
import html.parser
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import catalog  # noqa: E402
import build_providers  # noqa: E402

API_DIR = os.path.join(ROOT, "api")
FAILS = []
CHECKS = [0]


def check(condition, message):
    CHECKS[0] += 1
    if not condition:
        FAILS.append(message)
        print("FAIL  " + message)
    else:
        print("ok    " + message)


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("href", "src"):
            if values.get(key):
                self.urls.append(values[key])


def html_files():
    found = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in files:
            if name.endswith(".html"):
                found.append(os.path.join(base, name))
    return sorted(found)


def local_path(url_path):
    rel = url_path.lstrip("/")
    target = os.path.join(ROOT, rel)
    if url_path.endswith("/"):
        target = os.path.join(target, "index.html")
    return target


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code
    except Exception as err:  # noqa: BLE001
        return "ERR:%s" % err


def main():
    rows, meta, slugs = catalog.load()
    summaries = catalog.provider_summaries(rows, slugs)
    top = summaries[:build_providers.TOP_N]

    with open(os.path.join(API_DIR, "models.json"), encoding="utf-8") as fh:
        models_doc = json.load(fh)
    with open(os.path.join(API_DIR, "providers.json"), encoding="utf-8") as fh:
        providers_doc = json.load(fh)

    # --- 1. API vs catalog -------------------------------------------------
    check(models_doc["counts"]["models"] == len(models_doc["models"]) == len(rows),
          "models.json counts.models == array length == catalog rows (%d)" % len(rows))
    check(models_doc["counts"]["providers"] == providers_doc["counts"]["providers"]
          == len(providers_doc["providers"]) == len(summaries),
          "providers count matches catalog (%d)" % len(summaries))
    check(models_doc["counts"] == providers_doc["counts"], "both files carry identical counts")
    check(models_doc["generated_at"] == providers_doc["generated_at"],
          "both files carry the same generated_at (%s)" % models_doc["generated_at"])
    check(models_doc["source"]["name"] == "models.dev", "source.name is models.dev")
    check(len({m["id"] for m in models_doc["models"]}) == len(models_doc["models"]),
          "model ids are unique")

    required_model = ["id", "name", "model_id", "provider_id", "provider", "provider_slug",
                      "input_per_1m", "output_per_1m", "blended_per_1m", "context_window",
                      "family", "release_date"]
    check(all(set(m) == set(required_model) for m in models_doc["models"]),
          "every model object has exactly the documented fields")
    check(all(m["input_per_1m"] >= 0 and m["output_per_1m"] >= 0 for m in models_doc["models"]),
          "no negative prices")
    bad_math = [m for m in models_doc["models"]
                if abs(round((3 * m["input_per_1m"] + m["output_per_1m"]) / 4, 4)
                       - m["blended_per_1m"]) > 0.0001]
    check(not bad_math, "blended_per_1m obeys (3*input+output)/4")

    required_provider = ["id", "name", "slug", "model_count", "free_models",
                         "input_min_per_1m", "input_max_per_1m", "output_min_per_1m",
                         "output_max_per_1m", "blended_min_per_1m", "blended_max_per_1m",
                         "cheapest_model", "cheapest_blended_per_1m", "page"]
    check(all(set(p) == set(required_provider) for p in providers_doc["providers"]),
          "every provider object has exactly the documented fields")
    check(sum(p["model_count"] for p in providers_doc["providers"]) == len(models_doc["models"]),
          "provider model_count values sum to total models")

    # spot-check aggregates for the top 20 against the raw rows
    by_provider = {}
    for row in rows:
        by_provider.setdefault(row["provider_id"], []).append(row)
    agg_ok = True
    for entry in top:
        live = [p for p in providers_doc["providers"] if p["id"] == entry["id"]][0]
        provider_rows = by_provider[entry["id"]]
        if (live["model_count"] != len(provider_rows)
                or abs(live["input_max_per_1m"] - max(r["input"] for r in provider_rows)) > 1e-9
                or abs(live["blended_min_per_1m"] - min(r["blended"] for r in provider_rows)) > 1e-9):
            agg_ok = False
            print("      aggregate mismatch:", entry["name"])
    check(agg_ok, "top-20 provider aggregates match raw rows")

    # --- 2. index embeds the same rows ------------------------------------
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as fh:
        index_html = fh.read()
    marker = "const DATA="
    start = index_html.index(marker) + len(marker)
    end = index_html.index(";", start)
    embedded = json.loads(index_html[start:end])
    check(len(embedded) == len(models_doc["models"]),
          "index.html embeds %d rows (API has %d)" % (len(embedded), len(models_doc["models"])))
    check(len({r["p"] for r in embedded}) == providers_doc["counts"]["providers"],
          "index.html embeds %d distinct providers" % providers_doc["counts"]["providers"])

    # --- 3. HTTP 200 through a local server --------------------------------
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d/" % port
    try:
        for _ in range(50):
            if fetch(base + "index.html") == 200:
                break
            time.sleep(0.1)
        pages = html_files()
        bad = [(os.path.relpath(p, ROOT), fetch(base + os.path.relpath(p, ROOT).replace("\\", "/")))
               for p in pages]
        bad = [b for b in bad if b[1] != 200]
        check(not bad, "all %d HTML pages return 200 via local http.server" % len(pages))
        if bad:
            print("      non-200:", bad[:10])

        # --- 4. internal links -------------------------------------------
        broken = []
        absolute = []
        checked = set()
        for page in pages:
            rel = os.path.relpath(page, ROOT).replace("\\", "/")
            page_url = base + rel
            with open(page, encoding="utf-8") as fh:
                parser = Links()
                parser.feed(fh.read())
            for raw in parser.urls:
                if raw.startswith(("#", "mailto:", "javascript:", "data:")):
                    continue
                parsed = urlparse(raw)
                if parsed.scheme in ("http", "https"):
                    continue
                if raw.startswith("/"):
                    absolute.append((rel, raw))
                    continue
                target = urljoin(page_url, raw)
                path = urlparse(target).path
                if path in checked:
                    continue
                checked.add(path)
                fs = local_path(path)
                if not os.path.isfile(fs):
                    broken.append((rel, raw))
                    continue
                status = fetch(target)
                if status != 200:
                    broken.append((rel, raw, status))
        check(not broken, "all internal links resolve (%d unique targets)" % len(checked))
        if broken:
            print("      broken:", broken[:10])
        check(not absolute, "no root-absolute internal links")
        if absolute:
            print("      absolute:", absolute[:10])

        # --- 5. provider pages -------------------------------------------
        provider_dirs = sorted(
            d for d in os.listdir(os.path.join(ROOT, "providers"))
            if os.path.isdir(os.path.join(ROOT, "providers", d)))
        check(len(provider_dirs) == build_providers.TOP_N,
              "exactly %d provider pages generated" % build_providers.TOP_N)
        check(set(provider_dirs) == {e["slug"] for e in top},
              "provider page slugs match the top-20 list")

        page_ok = True
        for entry in top:
            path = os.path.join(ROOT, "providers", entry["slug"], "index.html")
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            tbodies = text.count("<tr>") - 1  # minus the header row
            if "%d priced models" % entry["model_count"] not in text:
                page_ok = False
                print("      count text missing:", entry["slug"])
            if tbodies != build_providers.CHEAPEST_SHOWN:
                page_ok = False
                print("      rows=%d on %s" % (tbodies, entry["slug"]))
        check(page_ok, "every provider page shows its real model count and 10 cheapest rows")

        print("\nPAGES %d html | %d provider pages | %d models | %d providers | data %s"
              % (len(pages), len(provider_dirs), len(rows), len(summaries),
                 meta["source"]["cache_modified"][:10]))
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    print("\n%d checks, %d failed" % (CHECKS[0], len(FAILS)))
    if FAILS:
        print("BLOCKED: verification failed: %s" % "; ".join(FAILS[:5]))
        return 1
    print("VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
