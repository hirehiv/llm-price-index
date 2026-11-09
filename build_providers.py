#!/usr/bin/env python3
"""Build providers/index.html and providers/<slug>/index.html for the top N providers."""
import html
import os

import catalog

PROVIDERS_DIR = os.path.join(catalog.ROOT, "providers")
TOP_N = 20
CHEAPEST_SHOWN = 10


def _price(value):
    return "Free" if value == 0 else "$" + catalog.money(value)


def _range(lo, hi):
    return _price(lo) if lo == hi else "%s – %s" % (_price(lo), _price(hi))


def _head(title, description, root, data_date):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/site.css">
</head><body>
<header><div class="wrap bar"><a class="brand" href="{root}"><span class="mark">$</span>LLM Price Index</a><nav><a href="{root}">Compare</a><a href="{root}providers/">Providers</a><a href="{root}docs/api/">API</a></nav><div class="spacer"></div><span class="tag">data {data_date}</span></div></header>
<div class="wrap">"""


def _foot(root, data_date, count):
    return f"""<div class="foot"><b>Method.</b> Published list prices per 1M tokens from the models.dev catalog, data {data_date}. Blended = (3×input + output) / 4. {count:,} priced text models in this view. Prices change; verify before committing volume. <a href="{root}">Back to the full index</a> · <a href="{root}docs/api/">JSON API</a></div>
</div></body></html>"""


def render_provider(entry, rows, meta):
    name = entry["name"]
    count = entry["model_count"]
    data_date = meta["source"]["cache_modified"][:10]
    cheapest = sorted(rows, key=lambda r: (r["blended"], r["name"].lower()))[:CHEAPEST_SHOWN]

    body_rows = []
    for i, row in enumerate(cheapest, 1):
        body_rows.append(
            "<tr><td class=\"ctx\">{rank}</td><td><div class=\"mname\">{name}</div><div class=\"prov\">{family}</div></td>"
            "<td class=\"num\">{inp}</td><td class=\"num\">{out}</td>"
            "<td class=\"num\" style=\"font-weight:600\">{blend}</td><td class=\"ctx\">{ctx}</td></tr>".format(
                rank=i,
                name=html.escape(row["name"]),
                family=html.escape(row["family"] or "—"),
                inp=_price(row["input"]),
                out=_price(row["output"]),
                blend=_price(row["blended"]),
                ctx=("%.1fM" % (row["context"] / 1000000)) if row["context"] >= 1000000
                else ("%.0fk" % (row["context"] / 1000) if row["context"] >= 1000 else "—"),
            ))

    free_note = "%s free" % format(entry["free_models"], ",") if entry["free_models"] else "none free"
    title = "%s pricing — %s models compared" % (name, format(count, ","))
    description = ("Published %s prices per 1M tokens: %s text models from %s to %s input. "
                   "The 10 cheapest models, from the LLM Price Index." %
                   (name, format(count, ","), _price(entry["input_min"]), _price(entry["input_max"])))

    return (
        _head(title, description, "../../", data_date)
        + f"""
<div class="crumbs"><a href="../../">Home</a> / <a href="../">Providers</a> / {html.escape(name)}</div>
<section class="hero">
 <div class="eyebrow">Provider · {count:,} priced models</div>
 <h1>{html.escape(name)} pricing</h1>
 <p class="lede">Published list prices per 1M tokens for every text model with a rate on {html.escape(name)}, from the models.dev catalog. Blended = (3×input + output) / 4.</p>
</section>
<section class="main">
 <div class="stats">
   <div class="stat"><div class="k">Models indexed</div><div class="v">{count:,}</div><div class="s">{free_note}</div></div>
   <div class="stat"><div class="k">Input $/1M</div><div class="v">{_range(entry["input_min"], entry["input_max"])}</div><div class="s">cheapest to dearest</div></div>
   <div class="stat"><div class="k">Output $/1M</div><div class="v">{_range(entry["output_min"], entry["output_max"])}</div><div class="s">cheapest to dearest</div></div>
   <div class="stat"><div class="k">Cheapest blended</div><div class="v">{_price(entry["cheapest_blended"])}</div><div class="s">{html.escape(entry["cheapest_model"] or "")}</div></div>
 </div>
 <div class="section-h">10 cheapest models</div>
 <div class="table"><table><thead><tr>
  <th class="ctx">#</th><th>Model</th><th class="num">Input $/1M</th><th class="num">Output $/1M</th><th class="num">Blended</th><th class="ctx">Context</th>
 </tr></thead><tbody>
 {''.join(body_rows)}
 </tbody></table></div>
""" + _foot("../../", data_date, count)
    )


def render_index(entries, meta):
    data_date = meta["source"]["cache_modified"][:10]
    total = meta["counts"]["models"]
    body = []
    for i, entry in enumerate(entries, 1):
        body.append(
            "<tr><td class=\"ctx\">{rank}</td><td><a class=\"mname\" href=\"{slug}/\">{name}</a></td>"
            "<td class=\"num\">{count:,}</td><td class=\"num\">{inp}</td>"
            "<td class=\"num\">{out}</td><td class=\"num\" style=\"font-weight:600\">{blend}</td></tr>".format(
                rank=i,
                slug=entry["slug"],
                name=html.escape(entry["name"]),
                count=entry["model_count"],
                inp=_range(entry["input_min"], entry["input_max"]),
                out=_range(entry["output_min"], entry["output_max"]),
                blend=_price(entry["cheapest_blended"]),
            ))
    return (
        _head("Providers — LLM Price Index",
              "Model counts and price ranges for the 20 providers with the most priced models.",
              "../", data_date)
        + f"""
<div class="crumbs"><a href="../">Home</a> / Providers</div>
<section class="hero">
 <div class="eyebrow">Top 20 by model count · {total:,} models indexed</div>
 <h1>Provider pricing</h1>
 <p class="lede">The 20 providers with the most priced text models in the index. Each page lists its model count, full price range and the 10 cheapest models per 1M tokens.</p>
</section>
<section class="main">
 <div class="table"><table><thead><tr>
  <th class="ctx">#</th><th>Provider</th><th class="num">Models</th><th class="num">Input $/1M</th><th class="num">Output $/1M</th><th class="num">From (blended)</th>
 </tr></thead><tbody>
 {''.join(body)}
 </tbody></table></div>
""" + _foot("../", data_date, total)
    )


def build(rows, meta, slugs):
    entries = catalog.provider_summaries(rows, slugs)
    top = entries[:TOP_N]
    page_slugs = {e["slug"] for e in top}

    by_provider = {}
    for row in rows:
        by_provider.setdefault(row["provider_id"], []).append(row)

    written = []
    for entry in top:
        out_dir = os.path.join(PROVIDERS_DIR, entry["slug"])
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "index.html")
        doc = render_provider(entry, by_provider[entry["id"]], meta)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(doc)
        written.append(path)

    index_path = os.path.join(PROVIDERS_DIR, "index.html")
    os.makedirs(PROVIDERS_DIR, exist_ok=True)
    with open(index_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_index(top, meta))

    print("wrote providers/index.html + %d provider pages (top %d by model count)" % (len(written), TOP_N))
    for entry in top:
        print("  %-28s %-26s %4d models" % (entry["name"], entry["slug"], entry["model_count"]))
    return page_slugs


if __name__ == "__main__":
    rows, meta, slugs = catalog.load()
    build(rows, meta, slugs)
