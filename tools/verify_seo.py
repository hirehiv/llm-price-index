#!/usr/bin/env python3
"""Verify the search plumbing: robots, sitemap, canonical, robots meta, JSON-LD.

Local mode checks the built files on disk. --live re-checks the deployed site
and the IndexNow key file. Exit code is the number of failures (0 = all good).

Usage:
  python tools/verify_seo.py
  python tools/verify_seo.py --live
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_seo  # noqa: E402
import catalog  # noqa: E402

ROOT = catalog.ROOT
SITE = catalog.SITE_URL
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

RE_CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)">')
RE_ROBOTS = re.compile(r'<meta name="robots" content="([^"]*)">', re.I)
RE_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

failures = []
checks = 0


def check(ok, label, detail=""):
    global checks
    checks += 1
    if not ok:
        failures.append(label + ((" — " + detail) if detail else ""))
        print("FAIL  %s%s" % (label, (" — " + detail) if detail else ""))
    else:
        print("ok    %s%s" % (label, (" — " + detail) if detail else ""))


def page_path_for(rel_file):
    """index.html relative path -> site path ('' or 'providers/foo/')."""
    rel = rel_file.replace("\\", "/")
    assert rel.endswith("index.html")
    return rel[: -len("index.html")]


def html_pages():
    pages = []
    for dirpath, _dirnames, filenames in os.walk(ROOT):
        if ".git" in dirpath.replace("\\", "/").split("/"):
            continue
        if "index.html" in filenames:
            rel = os.path.relpath(os.path.join(dirpath, "index.html"), ROOT)
            pages.append(rel.replace("\\", "/"))
    return sorted(pages)


def jsonld_of(text):
    return [json.loads(m) for m in RE_LD.findall(text)]


def types_of(docs):
    out = []
    for doc in docs:
        nodes = doc.get("@graph", [doc]) if isinstance(doc, dict) else []
        for node in nodes:
            t = node.get("@type") if isinstance(node, dict) else None
            if t:
                out.append(t)
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "LLMPriceIndex-SEO-Check/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read()


def local_checks():
    print("== local files ==")

    # 1. robots.txt
    robots_path = os.path.join(ROOT, "robots.txt")
    robots = open(robots_path, encoding="utf-8").read() if os.path.isfile(robots_path) else ""
    check(os.path.isfile(robots_path), "robots.txt exists")
    check("User-agent: *" in robots and re.search(r"(?m)^Allow: /\s*$", robots) is not None,
          "robots.txt allows all")
    check(("Sitemap: %s" % build_seo.SITEMAP_URL) in robots,
          "robots.txt points at the sitemap", build_seo.SITEMAP_URL)
    check("Disallow" not in robots, "robots.txt has no Disallow rules")

    # 2. sitemap.xml
    sm_path = os.path.join(ROOT, "sitemap.xml")
    check(os.path.isfile(sm_path), "sitemap.xml exists")
    try:
        tree = ET.parse(sm_path)
        root = tree.getroot()
        parsed = True
    except ET.ParseError as exc:
        root, parsed = None, False
        check(False, "sitemap.xml is valid XML", str(exc))
    if parsed:
        check(root.tag == SM_NS + "urlset", "sitemap.xml is a urlset", root.tag)
        locs = [e.text for e in root.iter(SM_NS + "loc")]
        check(len(locs) == len(set(locs)), "sitemap has no duplicate URLs", "%d locs" % len(locs))

        expected = {build_seo.page_url(page_path_for(p)) for p in html_pages()}
        check(set(locs) == expected, "sitemap covers every HTML page",
              "%d urls, %d pages" % (len(locs), len(expected)))
        missing = expected - set(locs)
        extra = set(locs) - expected
        if missing:
            print("      missing: %s" % sorted(missing))
        if extra:
            print("      extra:   %s" % sorted(extra))
        check(all(u.startswith(SITE + "/") for u in locs), "every loc is absolute on the site root")
        check(all(u.endswith("/") for u in locs), "every loc is a directory URL")
        print("      sitemap lastmod: %s" % ", ".join(
            sorted({e.text for e in root.iter(SM_NS + "lastmod")})))

    # 3/4. per-page canonical, robots meta, JSON-LD
    pages = html_pages()
    print("\n== %d HTML pages: canonical + robots meta ==" % len(pages))
    canon_bad, robots_bad, ld_bad = [], [], []
    for rel in pages:
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        path = page_path_for(rel)
        want = build_seo.page_url(path)

        found = RE_CANONICAL.findall(text)
        if found != [want]:
            canon_bad.append("%s -> %s" % (rel, found))

        robots_meta = RE_ROBOTS.findall(text)
        if len(robots_meta) != 1 or robots_meta[0].replace(" ", "").lower() != "index,follow":
            robots_bad.append("%s -> %s" % (rel, robots_meta))

        if "noindex" in text.lower():
            ld_bad.append("%s contains noindex" % rel)

        docs = jsonld_of(text)
        if not docs:
            ld_bad.append("%s has no JSON-LD" % rel)
            continue
        try:
            types = types_of(docs)
        except (ValueError, AttributeError) as exc:
            ld_bad.append("%s JSON-LD: %s" % (rel, exc))
            continue
        if path == "":
            if not {"WebSite", "Dataset"} <= set(types):
                ld_bad.append("%s JSON-LD types %s" % (rel, types))
        elif path.startswith("providers/") and path != "providers/":
            if "WebPage" not in types:
                ld_bad.append("%s JSON-LD types %s" % (rel, types))
        elif "WebPage" not in types:
            ld_bad.append("%s JSON-LD types %s" % (rel, types))

    check(not canon_bad, "canonical on all %d pages" % len(pages), "; ".join(canon_bad[:4]))
    check(not robots_bad, "meta robots index,follow on all %d pages" % len(pages),
          "; ".join(robots_bad[:4]))
    check(not ld_bad, "JSON-LD parses on all %d pages, no noindex" % len(pages),
          "; ".join(ld_bad[:4]))

    # 5. key file
    key_path = os.path.join(ROOT, build_seo.INDEXNOW_KEY_FILE)
    check(os.path.isfile(key_path), "IndexNow key file at repo root", build_seo.INDEXNOW_KEY_FILE)
    if os.path.isfile(key_path):
        body = open(key_path, encoding="utf-8").read().strip()
        check(body == build_seo.INDEXNOW_KEY, "key file contains exactly the key",
              "%d chars" % len(body))


def live_checks():
    print("\n== live ==")
    for label, url in (("robots.txt", SITE + "/robots.txt"),
                       ("sitemap.xml", SITE + "/sitemap.xml"),
                       ("IndexNow key", "%s/%s" % (SITE, build_seo.INDEXNOW_KEY_FILE))):
        try:
            status, body = fetch(url)
            check(status == 200, "%s returns 200" % label, "%d, %d bytes" % (status, len(body)))
        except urllib.error.HTTPError as exc:
            check(False, "%s returns 200" % label, "HTTP %d" % exc.code)
            continue
        except Exception as exc:  # noqa: BLE001 - report any transport error
            check(False, "%s returns 200" % label, repr(exc))
            continue

        if label == "sitemap.xml":
            try:
                root = ET.fromstring(body)
                locs = [e.text for e in root.iter(SM_NS + "loc")]
                expected = {build_seo.page_url(page_path_for(p)) for p in html_pages()}
                check(root.tag == SM_NS + "urlset", "live sitemap.xml is valid urlset")
                check(set(locs) == expected, "live sitemap lists every page",
                      "%d urls" % len(locs))
            except ET.ParseError as exc:
                check(False, "live sitemap.xml parses", str(exc))
        if label == "IndexNow key":
            check(body.decode("utf-8").strip() == build_seo.INDEXNOW_KEY,
                  "live key file content matches")

    samples = ["", "providers/openrouter/", "docs/api/"]
    for path in samples:
        url = build_seo.page_url(path)
        try:
            status, body = fetch(url)
        except Exception as exc:  # noqa: BLE001
            check(False, "live page %s" % (path or "/"), repr(exc))
            continue
        text = body.decode("utf-8", "replace")
        canon = RE_CANONICAL.findall(text)
        robots_meta = RE_ROBOTS.findall(text)
        try:
            types = types_of(jsonld_of(text))
            ld_ok = bool(types)
        except ValueError as exc:
            types, ld_ok = [], False
            print("      JSON-LD error: %s" % exc)
        check(status == 200 and canon == [url], "live canonical %s" % (path or "/"), str(canon))
        check(robots_meta and robots_meta[0].replace(" ", "").lower() == "index,follow",
              "live robots meta %s" % (path or "/"), str(robots_meta))
        check(ld_ok, "live JSON-LD parses %s" % (path or "/"), ", ".join(types))


if __name__ == "__main__":
    local_checks()
    if "--live" in sys.argv:
        live_checks()
    print("\n%d checks, %d failed" % (checks, len(failures)))
    sys.exit(len(failures))
