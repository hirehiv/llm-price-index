#!/usr/bin/env python3
"""Build api/models.json, api/providers.json and docs/api/index.html."""
import html
import json
import os

import build_seo
import catalog

API_DIR = os.path.join(catalog.ROOT, "api")
DOCS_DIR = os.path.join(catalog.ROOT, "docs", "api")


def model_payload(rows, slugs):
    out = []
    for row in rows:
        out.append({
            "id": row["id"],
            "name": row["name"],
            "model_id": row["model_id"],
            "provider_id": row["provider_id"],
            "provider": row["provider"],
            "provider_slug": slugs[row["provider_id"]],
            "input_per_1m": row["input"],
            "output_per_1m": row["output"],
            "blended_per_1m": row["blended"],
            "context_window": row["context"],
            "family": row["family"],
            "release_date": row["release_date"],
        })
    return out


def provider_payload(rows, slugs, page_slugs):
    out = []
    for entry in catalog.provider_summaries(rows, slugs):
        out.append({
            "id": entry["id"],
            "name": entry["name"],
            "slug": entry["slug"],
            "model_count": entry["model_count"],
            "free_models": entry["free_models"],
            "input_min_per_1m": entry["input_min"],
            "input_max_per_1m": entry["input_max"],
            "output_min_per_1m": entry["output_min"],
            "output_max_per_1m": entry["output_max"],
            "blended_min_per_1m": entry["blended_min"],
            "blended_max_per_1m": entry["blended_max"],
            "cheapest_model": entry["cheapest_model"],
            "cheapest_blended_per_1m": entry["cheapest_blended"],
            "page": (entry["slug"] + "/") if entry["slug"] in page_slugs else None,
        })
    return out


def envelope(meta):
    return {
        "generated_at": meta["generated_at"],
        "source": meta["source"],
        "counts": meta["counts"],
        "currency": meta["currency"],
        "unit": meta["unit"],
        "blended_formula": meta["blended_formula"],
        "site": catalog.SITE_URL,
    }


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return len(text)


def _price(value):
    return "Free" if value == 0 else "$" + catalog.money(value)


def render_docs(meta, models, providers):
    count = meta["counts"]["models"]
    provider_count = meta["counts"]["providers"]
    generated = meta["generated_at"]
    data_date = meta["source"]["cache_modified"][:10]
    esc = html.escape

    model_sample = json.dumps(
        next((m for m in models if m["blended_per_1m"] > 0 and m["context_window"] >= 128000), models[0]),
        indent=2, ensure_ascii=False)
    provider_sample = json.dumps(
        next((p for p in providers if p["page"]), providers[0]),
        indent=2, ensure_ascii=False)
    model_count_sample = len(models)

    title = "JSON API — LLM Price Index"
    description = ("Free static JSON API for %s LLM model prices across %s providers: "
                   "input, output and blended cost per 1M tokens."
                   % (format(count, ","), provider_count))
    seo = "\n".join([
        build_seo.canonical("docs/api/"),
        build_seo.META_ROBOTS,
        build_seo.jsonld(build_seo.webpage_node("docs/api/", title, description, data_date)),
    ])

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JSON API — LLM Price Index</title>
<meta name="description" content="{description}">
{seo}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../assets/site.css">
</head><body>
<header><div class="wrap bar"><a class="brand" href="../../"><span class="mark">$</span>LLM Price Index</a><nav><a href="../../">Compare</a><a href="../../providers/">Providers</a><a href="./">API</a></nav><div class="spacer"></div><span class="tag">data {data_date}</span></div></header>
<div class="wrap">
<div class="crumbs"><a href="../../">Home</a> / API</div>
<section class="hero">
 <div class="eyebrow">Static JSON · no auth · CORS enabled</div>
 <h1>JSON API</h1>
 <p class="lede">The same dataset that powers the index, as two static JSON files. No key, no rate limit, no signup. Prices are USD list rates per 1M tokens.</p>
</section>
<section class="main prose">
 <table class="kv"><tbody>
   <tr><td>models.json</td><td>GET</td><td><a href="../../api/models.json">../../api/models.json</a> — {count:,} provider+model rows</td></tr>
   <tr><td>providers.json</td><td>GET</td><td><a href="../../api/providers.json">../../api/providers.json</a> — {provider_count} provider summaries</td></tr>
   <tr><td>generated_at</td><td>meta</td><td>{esc(generated)}</td></tr>
   <tr><td>source</td><td>meta</td><td>{esc(meta["source"]["name"])} catalog, cache modified {esc(meta["source"]["cache_modified"])}</td></tr>
 </tbody></table>

 <div class="section-h">Example</div>
 <pre>curl -s {catalog.SITE_URL}/api/models.json | jq '.counts'</pre>
 <pre>{{"models":{count},"providers":{provider_count}}}</pre>

 <div class="section-h">Envelope (both files)</div>
 <table class="kv"><tbody>
   <tr><td>generated_at</td><td>string (ISO 8601 UTC)</td><td>Build time of this file.</td></tr>
   <tr><td>source.name</td><td>string</td><td>Upstream catalog, currently <code>models.dev</code>.</td></tr>
   <tr><td>source.url</td><td>string</td><td>Upstream site.</td></tr>
   <tr><td>source.cache_file</td><td>string</td><td>Cache filename the build read.</td></tr>
   <tr><td>source.cache_modified</td><td>string (ISO 8601 UTC)</td><td>When the upstream cache was last refreshed — this is the data date.</td></tr>
   <tr><td>counts.models</td><td>integer</td><td>Priced provider+model rows in the file.</td></tr>
   <tr><td>counts.providers</td><td>integer</td><td>Providers with at least one priced model.</td></tr>
   <tr><td>currency</td><td>string</td><td>Always <code>USD</code>.</td></tr>
   <tr><td>unit</td><td>string</td><td>Always <code>per 1M tokens</code>.</td></tr>
   <tr><td>blended_formula</td><td>string</td><td><code>(3 * input + output) / 4</code>.</td></tr>
   <tr><td>site</td><td>string</td><td>Public site root.</td></tr>
 </tbody></table>

 <div class="section-h">models.json — array item</div>
 <table class="kv"><tbody>
   <tr><td>id</td><td>string</td><td><code>{{provider_id}}/{{model_id}}</code>, unique per row.</td></tr>
   <tr><td>name</td><td>string</td><td>Display name as published by the provider.</td></tr>
   <tr><td>model_id</td><td>string</td><td>Upstream model id.</td></tr>
   <tr><td>provider_id</td><td>string</td><td>Upstream provider id.</td></tr>
   <tr><td>provider</td><td>string</td><td>Provider display name.</td></tr>
   <tr><td>provider_slug</td><td>string</td><td>Stable slug used in provider page URLs.</td></tr>
   <tr><td>input_per_1m</td><td>number</td><td>USD per 1M input tokens. <code>0</code> means free.</td></tr>
   <tr><td>output_per_1m</td><td>number</td><td>USD per 1M output tokens.</td></tr>
   <tr><td>blended_per_1m</td><td>number</td><td><code>(3*input + output) / 4</code>, rounded to 4dp.</td></tr>
   <tr><td>context_window</td><td>integer</td><td>Context limit in tokens.</td></tr>
   <tr><td>family</td><td>string</td><td>Model family, may be empty.</td></tr>
   <tr><td>release_date</td><td>string</td><td><code>YYYY-MM-DD</code>, may be empty.</td></tr>
 </tbody></table>
 <pre>{esc(model_sample)}</pre>
 <p style="font-size:12px;color:var(--muted)">One object shown. The live file has {model_count_sample:,}.</p>

 <div class="section-h">providers.json — array item</div>
 <table class="kv"><tbody>
   <tr><td>id / name / slug</td><td>string</td><td>Provider identity; slug is used in <code>providers/&lt;slug&gt;/</code>.</td></tr>
   <tr><td>model_count</td><td>integer</td><td>Priced models for this provider.</td></tr>
   <tr><td>free_models</td><td>integer</td><td>Rows with both input and output at 0.</td></tr>
   <tr><td>input_min_per_1m …</td><td>number</td><td>Min/max input, output and blended price across its models.</td></tr>
   <tr><td>cheapest_model</td><td>string</td><td>Lowest blended price; ties resolved by name.</td></tr>
   <tr><td>cheapest_blended_per_1m</td><td>number</td><td>That model's blended price.</td></tr>
   <tr><td>page</td><td>string or null</td><td>Relative page path when a provider page is generated (top 20 by model count), else <code>null</code>.</td></tr>
 </tbody></table>
 <pre>{esc(provider_sample)}</pre>

 <div class="section-h">Notes</div>
 <ul>
   <li>Only text-in/text-out models with a published input and output price and a context limit are included.</li>
   <li>One row per provider+model: the same model can appear under several providers at different prices.</li>
   <li>Responses are cached by GitHub Pages; <code>Access-Control-Allow-Origin: *</code> is set, so browser fetches work.</li>
   <li>Field names are stable. Counts, prices and <code>generated_at</code> change on every rebuild.</li>
   <li>Prices are published list rates. Providers change them; verify before committing volume.</li>
   <li>Upstream: <a href="https://models.dev">models.dev</a>. This index is independent and takes no placement fees.</li>
 </ul>
 <div class="foot"><b>LLM Price Index</b> · <a href="../../">Compare prices</a> · <a href="../../providers/">Providers</a></div>
</section>
</div></body></html>"""


def build(rows, meta, slugs, page_slugs):
    models = model_payload(rows, slugs)
    providers = provider_payload(rows, slugs, page_slugs)

    models_doc = envelope(meta)
    models_doc["models"] = models
    providers_doc = envelope(meta)
    providers_doc["providers"] = providers

    size_models = _write_json(os.path.join(API_DIR, "models.json"), models_doc)
    size_providers = _write_json(os.path.join(API_DIR, "providers.json"), providers_doc)

    os.makedirs(DOCS_DIR, exist_ok=True)
    docs_path = os.path.join(DOCS_DIR, "index.html")
    docs = render_docs(meta, models, providers)
    with open(docs_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(docs)

    print("wrote api/models.json (%s bytes, %d models)" % (format(size_models, ","), len(models)))
    print("wrote api/providers.json (%s bytes, %d providers)" % (format(size_providers, ","), len(providers)))
    print("wrote docs/api/index.html (%s bytes)" % format(len(docs), ","))
    return providers


if __name__ == "__main__":
    rows, meta, slugs = catalog.load()
    page_slugs = {p["slug"] for p in catalog.provider_summaries(rows, slugs)[:20]}
    build(rows, meta, slugs, page_slugs)
