#!/usr/bin/env python3
"""One-shot build: index page, JSON API, API docs, top-20 provider pages, README counts.

Run from the repo root: python build.py
"""
import os
import re

import build_api
import build_providers
import build_seo
import catalog
import generate

README = os.path.join(catalog.ROOT, "README.md")
START = "<!-- api:start -->"
END = "<!-- api:end -->"


def update_readme(meta, pages):
    count = meta["counts"]["models"]
    providers = meta["counts"]["providers"]
    generated = meta["generated_at"]
    data_date = meta["source"]["cache_modified"][:10]
    block = "\n".join([
        START,
        "- %s priced provider+model rows across %s providers (data %s, built %s)."
        % (format(count, ","), providers, data_date, generated),
        "- [`api/models.json`](api/models.json) — one row per provider+model.",
        "- [`api/providers.json`](api/providers.json) — provider summaries.",
        "- Docs and schema: [`docs/api/`](docs/api/index.html).",
        "- Provider pages: [`providers/`](providers/index.html) — top %d by model count."
        % pages,
        END,
    ])
    if not os.path.isfile(README):
        return
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n## API\n" + block + "\n"
    with open(README, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("updated README.md API block")


def main():
    rows, meta, slugs = catalog.load()
    providers = catalog.provider_summaries(rows, slugs)
    page_slugs = {p["slug"] for p in providers[:build_providers.TOP_N]}

    print("source: %s | data %s | %d models | %d providers"
          % (meta["source"]["cache_file"], meta["source"]["cache_modified"],
             meta["counts"]["models"], meta["counts"]["providers"]))

    path, size = generate.build(rows, meta, slugs, page_slugs)
    print("wrote %s (%s bytes)" % (path, format(size, ",")))

    build_api.build(rows, meta, slugs, page_slugs)
    build_providers.build(rows, meta, slugs)
    build_seo.write(meta, page_slugs)
    update_readme(meta, len(page_slugs))


if __name__ == "__main__":
    main()
