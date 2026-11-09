#!/usr/bin/env python3
"""Report the active models.dev cache and every fallback candidate.

Run before a rebuild to confirm which data file the site will read and how
fresh it is. Uses the same resolution order as catalog.py.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import catalog  # noqa: E402


def audit(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    rows, meta, slugs = catalog.load(cache=path)
    print("  %s" % path)
    print("    modified=%s size=%s priced_rows=%d providers=%d raw_providers=%d"
          % (meta["source"]["cache_modified"], format(os.path.getsize(path), ","),
             len(rows), meta["counts"]["providers"], len(data)))
    return len(rows)


def main():
    active = catalog.cache_path()
    print("active cache (catalog.py):")
    audit(active)
    print("\nother candidates:")
    for path in catalog.CACHE_CANDIDATES:
        if os.path.isfile(path) and os.path.abspath(path) != os.path.abspath(active):
            audit(path)


if __name__ == "__main__":
    main()
