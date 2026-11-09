#!/usr/bin/env python3
"""Extract the inline homepage script so `node --check` can validate its syntax."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as fh:
    doc = fh.read()
match = re.search(r"<script>(.*)</script>", doc, re.S)
if not match:
    sys.exit("no inline script found")
out = os.path.join(os.environ.get("TEMP", "/tmp"), "llm-price-index.js")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(match.group(1))
print(out)
