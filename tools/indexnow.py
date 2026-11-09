#!/usr/bin/env python3
"""Submit every sitemap URL to IndexNow (Bing, Yandex; Google ignores it).

The key file must already be live: IndexNow fetches keyLocation to verify that
the submitting party controls the host. Run this only after the deploy that
publishes build_seo.INDEXNOW_KEY_FILE.

Records the HTTP status, body and URL list to Reports/pricewatch/indexnow-<date>.json.

Usage:
  python tools/indexnow.py --dry-run
  python tools/indexnow.py
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_seo  # noqa: E402
import catalog  # noqa: E402

SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
LOG_DIR = os.path.abspath(os.path.join(catalog.ROOT, "..", "..", "Reports", "pricewatch"))


def sitemap_urls():
    """Read the built sitemap so the submission cannot drift from it."""
    root = ET.parse(os.path.join(catalog.ROOT, "sitemap.xml")).getroot()
    return [e.text for e in root.iter(SM_NS + "loc")]


def payload(urls):
    host = urlsplit(catalog.SITE_URL).hostname
    return {
        "host": host,
        "key": build_seo.INDEXNOW_KEY,
        "keyLocation": "%s/%s" % (catalog.SITE_URL, build_seo.INDEXNOW_KEY_FILE),
        "urlList": urls,
    }


def main():
    urls = sitemap_urls()
    body = payload(urls)
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")

    print("endpoint: %s" % build_seo.INDEXNOW_ENDPOINT)
    print("host: %s (keyLocation %s)" % (body["host"], body["keyLocation"]))
    print("urls: %d" % len(urls))

    if "--dry-run" in sys.argv:
        print("dry run, not posting")
        print(raw.decode("utf-8")[:400] + " ...")
        return 0

    req = urllib.request.Request(
        build_seo.INDEXNOW_ENDPOINT, data=raw, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "LLMPriceIndex-IndexNow/1.0"})
    record = {
        "endpoint": build_seo.INDEXNOW_ENDPOINT,
        "submitted_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "host": body["host"],
        "key_location": body["keyLocation"],
        "url_count": len(urls),
        "urls": urls,
    }
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            record["status"] = resp.status
            record["response_body"] = resp.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as exc:
        record["status"] = exc.code
        record["response_body"] = exc.read().decode("utf-8", "replace").strip()
    except Exception as exc:  # noqa: BLE001 - network errors are a recorded outcome
        record["status"] = None
        record["response_body"] = ""
        record["error"] = repr(exc)

    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = record["submitted_at"][:10]
    path = os.path.join(LOG_DIR, "indexnow-%s.json" % stamp)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")

    print("status: %s" % record["status"])
    print("body:   %s" % (record["response_body"] or "(empty)"))
    if record.get("error"):
        print("error:  %s" % record["error"])
    print("record: %s" % path)
    # 200 = submitted, 202 = accepted (key pending validation). Anything else is a failure.
    return 0 if record["status"] in (200, 202) else 1


if __name__ == "__main__":
    sys.exit(main())
