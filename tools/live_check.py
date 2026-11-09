#!/usr/bin/env python3
"""Check the deployed GitHub Pages site: status codes, live counts, CORS header."""
import json
import sys
import urllib.error
import urllib.request

BASE = "https://hirehiv.github.io/llm-price-index/"
PATHS = ["", "providers/", "providers/openrouter/", "providers/nanogpt/",
         "providers/zenmux/", "docs/api/", "api/models.json",
         "api/providers.json", "assets/site.css"]


def get(path):
    url = BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "pricewatch-verify"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), b""


fail = 0
for path in PATHS:
    status, headers, body = get(path)
    mark = "ok  " if status == 200 else "FAIL"
    fail += 0 if status == 200 else 1
    print("%s /%-24s %s %8d bytes" % (mark, path, status, len(body)))
    if path == "api/models.json":
        doc = json.loads(body)
        print("     counts=%s generated_at=%s data=%s"
              % (doc["counts"], doc["generated_at"], doc["source"]["cache_modified"]))
        print("     CORS=%s content-type=%s"
              % (headers.get("Access-Control-Allow-Origin"),
                 headers.get("Content-Type")))
    if path == "api/providers.json":
        doc = json.loads(body)
        pages = [p["slug"] for p in doc["providers"] if p["page"]]
        print("     counts=%s provider_pages=%d" % (doc["counts"], len(pages)))
    if path in ("", "providers/openrouter/", "docs/api/"):
        text = body.decode("utf-8", "replace")
        for needle in ("8,449", "OpenRouter pricing", "JSON API"):
            if needle in text:
                print("     contains %r" % needle)

print("\n%d failures" % fail)
sys.exit(1 if fail else 0)
