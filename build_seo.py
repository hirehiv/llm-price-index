#!/usr/bin/env python3
"""Search plumbing for the LLM Price Index.

Owns three generated root files (robots.txt, sitemap.xml, the IndexNow key file)
and the canonical / robots-meta / JSON-LD fragments that every page renderer
embeds, so the sitemap cannot drift from the pages that are actually built.

URLs are always derived from catalog.SITE_URL (project Pages, no trailing slash).
"""
import json
import os
from xml.sax.saxutils import escape as xml_escape

import catalog

SITE_URL = catalog.SITE_URL  # https://hirehiv.github.io/llm-price-index

# IndexNow ownership key. Must match the file name at the repo root.
INDEXNOW_KEY = "ebc1c36989036f4fb1c963a2927dbb1c"
INDEXNOW_KEY_FILE = INDEXNOW_KEY + ".txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
SITEMAP_URL = SITE_URL + "/sitemap.xml"

META_ROBOTS = '<meta name="robots" content="index,follow">'


def page_url(path=""):
    """Absolute URL for a site-relative path ("" or "providers/openrouter/")."""
    return SITE_URL + "/" + path.lstrip("/")


def canonical(path=""):
    return '<link rel="canonical" href="%s">' % page_url(path)


def jsonld(*nodes):
    """A single <script type="application/ld+json"> holding a @graph of nodes."""
    text = json.dumps({"@context": "https://schema.org", "@graph": list(nodes)},
                      ensure_ascii=False, separators=(",", ":"))
    # A literal "</script>" inside the payload would close the element early.
    text = text.replace("<", "\\u003c")
    return '<script type="application/ld+json">%s</script>' % text


def website_node(description):
    return {
        "@type": "WebSite",
        "@id": SITE_URL + "/#website",
        "url": page_url(""),
        "name": "LLM Price Index",
        "description": description,
        "inLanguage": "en",
    }


def dataset_node(meta):
    count = meta["counts"]["models"]
    providers = meta["counts"]["providers"]
    data_date = meta["source"]["cache_modified"][:10]
    return {
        "@type": "Dataset",
        "@id": SITE_URL + "/#dataset",
        "name": "LLM Price Index — published LLM prices per 1M tokens",
        "description": (
            "Input, output and blended USD list prices per 1M tokens for %s text "
            "models across %s providers, sourced from the models.dev catalog."
            % (format(count, ","), providers)
        ),
        "url": page_url(""),
        "isPartOf": {"@id": SITE_URL + "/#website"},
        "isAccessibleForFree": True,
        "dateModified": meta["generated_at"],
        "temporalCoverage": data_date,
        "keywords": ["LLM pricing", "API pricing", "cost per token",
                     "language model prices", "token pricing"],
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Input price per 1M tokens", "unitText": "USD"},
            {"@type": "PropertyValue", "name": "Output price per 1M tokens", "unitText": "USD"},
            {"@type": "PropertyValue", "name": "Blended price per 1M tokens", "unitText": "USD"},
        ],
        "distribution": [
            {"@type": "DataDownload", "name": "models.json",
             "contentUrl": page_url("api/models.json"),
             "encodingFormat": "application/json"},
            {"@type": "DataDownload", "name": "providers.json",
             "contentUrl": page_url("api/providers.json"),
             "encodingFormat": "application/json"},
        ],
    }


def webpage_node(path, name, description, date_modified):
    url = page_url(path)
    return {
        "@type": "WebPage",
        "@id": url + "#webpage",
        "url": url,
        "name": name,
        "description": description,
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": "LLM Price Index", "url": page_url("")},
        "dateModified": date_modified,
    }


def sitemap_paths(page_slugs):
    """Every HTML page: index, providers hub, the provider pages, API docs."""
    paths = ["", "providers/", "docs/api/"]
    paths.extend("providers/%s/" % slug for slug in sorted(page_slugs))
    return paths


def render_robots():
    return ("# %s/\n"
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            "Sitemap: %s\n" % (SITE_URL, SITEMAP_URL))


def render_sitemap(paths, lastmod):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in paths:
        lines.append("  <url>")
        lines.append("    <loc>%s</loc>" % xml_escape(page_url(path)))
        lines.append("    <lastmod>%s</lastmod>" % lastmod)
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _write(name, text):
    path = os.path.join(catalog.ROOT, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def write(meta, page_slugs):
    """Write robots.txt, sitemap.xml and the IndexNow key file. Returns paths."""
    lastmod = meta["source"]["cache_modified"][:10]
    paths = sitemap_paths(page_slugs)
    _write("robots.txt", render_robots())
    _write("sitemap.xml", render_sitemap(paths, lastmod))
    # The key file holds the key and nothing else (IndexNow spec).
    _write(INDEXNOW_KEY_FILE, INDEXNOW_KEY)
    print("wrote robots.txt, sitemap.xml (%d urls) and %s" % (len(paths), INDEXNOW_KEY_FILE))
    return paths


if __name__ == "__main__":
    rows, meta, slugs = catalog.load()
    import build_providers
    top = catalog.provider_summaries(rows, slugs)[:build_providers.TOP_N]
    for p in write(meta, {e["slug"] for e in top}):
        print("  " + page_url(p))
