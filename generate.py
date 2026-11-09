#!/usr/bin/env python3
"""Build the LLM Price Index homepage from the models.dev catalog.

Input : models.dev cache (see catalog.py)
Output: index.html (self-contained data, external shared stylesheet)

Only models with a published input+output cost are included. One row per
provider+model, because the same model is often cheaper at a different provider.
"""
import html
import os

import build_seo
import catalog

OUT = catalog.ROOT

JS = r"""
const DATA=__DATA__;
const $=id=>document.getElementById(id);
let rows=DATA.slice(), sortK='b', sortAsc=true;
const money=n=>n===0?'Free':'$'+(n>=0.01?n.toFixed(2):n.toFixed(4));
const ctx=n=>n>=1000000?(n/1000000).toFixed(1)+'M':n>=1000?(n/1000).toFixed(0)+'k':'—';
const provs=[...new Set(DATA.map(r=>r.p))].sort();
provs.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p;$('prov').appendChild(o);});
const picks=DATA.filter(r=>r.b>0&&r.c>=100000).slice(0,120);
picks.forEach((r)=>{const idx=DATA.indexOf(r);const o=document.createElement('option');o.value=idx;o.textContent=r.n+' · '+r.p;$('cmodel').appendChild(o);});
function render(){
  const q=$('q').value.toLowerCase(), p=$('prov').value, minc=+$('ctx').value, incFree=$('free').checked;
  rows=DATA.filter(r=>(!q||(r.n+' '+r.p+' '+r.f).toLowerCase().includes(q))&&(!p||r.p===p)&&(r.c>=minc)&&(incFree||r.b>0));
  rows.sort((a,b)=>{const x=a[sortK],y=b[sortK];return (typeof x==='string'?x.localeCompare(y):x-y)*(sortAsc?1:-1);});
  const slice=rows.slice(0,400);
  $('rows').innerHTML=slice.map(r=>`<tr><td><div class="mname">${r.n}</div><div class="prov">${r.f||''}</div></td><td class="prov">${r.s?`<a href="providers/${r.s}/">${r.p}</a>`:r.p}</td><td class="num">${money(r.i)}</td><td class="num">${money(r.o)}</td><td class="num" style="font-weight:600">${money(r.b)}</td><td class="ctx">${ctx(r.c)}</td><td class="ctx">${r.d||'—'}</td></tr>`).join('');
  $('count').textContent=rows.length.toLocaleString()+' models'+(rows.length>400?' · showing first 400':'');
}
function cost(){const r=DATA[+$('cmodel').value];if(!r)return;const i=+$('cin').value||0,o=+$('cout').value||0;const c=(i/1e6)*r.i+(o/1e6)*r.o;$('cost').textContent='$'+c.toFixed(c<1?4:2);}
document.querySelectorAll('thead th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortAsc=sortK===k?!sortAsc:true;sortK=k;render();});
['q','prov','ctx','free'].forEach(id=>$(id).oninput=render);
['cmodel','cin','cout'].forEach(id=>$(id).oninput=cost);
render();cost();
"""


def render(rows, meta, slugs, page_slugs):
    count = meta["counts"]["models"]
    providers = meta["counts"]["providers"]
    data_date = meta["source"]["cache_modified"][:10]

    data = []
    for row in rows:
        slug = slugs[row["provider_id"]]
        data.append({
            "n": row["name"],
            "p": row["provider"],
            "i": row["input"],
            "o": row["output"],
            "c": row["context"],
            "f": row["family"],
            "d": row["release_date"],
            "b": row["blended"],
            "s": slug if slug in page_slugs else "",
        })

    import json
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    description = ("Compare published prices for %s LLM models across %s providers. "
                   "Input, output and blended cost per 1M tokens, with a cost calculator."
                   % (format(count, ","), providers))
    seo = "\n".join([
        build_seo.canonical(""),
        build_seo.META_ROBOTS,
        build_seo.jsonld(build_seo.website_node(description),
                         build_seo.dataset_node(meta)),
    ])

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM Price Index — cost per million tokens</title>
<meta name="description" content="{description}">
{seo}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css">
</head><body>
<header><div class="wrap bar"><a class="brand" href="./"><span class="mark">$</span>LLM Price Index</a><nav><a href="#table">Compare</a><a href="providers/">Providers</a><a href="docs/api/">API</a></nav><div class="spacer"></div><span class="tag">data {data_date}</span></div></header>
<div class="wrap">
<section class="hero">
 <div class="eyebrow">Published prices · {count:,} models · {providers} providers</div>
 <h1>What does one million tokens actually cost?</h1>
 <p class="lede">Input, output and blended price per 1M tokens for every model with a published rate. No estimates, no “contact sales”.</p>
 <div class="calc">
   <select id="cmodel"></select>
   <input id="cin" type="number" min="0" value="1000000" placeholder="Input tokens" title="Input tokens">
   <input id="cout" type="number" min="0" value="200000" placeholder="Output tokens" title="Output tokens">
   <div class="out" id="cost">—</div>
 </div>
</section>
<section class="main" id="table">
 <div class="tools">
   <input id="q" placeholder="Search model, provider or family…">
   <select id="prov"><option value="">All providers</option></select>
   <select id="ctx"><option value="0">Any context</option><option value="32000">32k+</option><option value="128000">128k+</option><option value="1000000">1M+</option></select>
   <label style="font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:6px"><input type="checkbox" id="free"> include free</label>
   <span class="count" id="count"></span>
 </div>
 <div class="table"><table><thead><tr>
   <th data-k="n">Model</th><th data-k="p">Provider</th><th data-k="i" class="num">Input $/1M</th><th data-k="o" class="num">Output $/1M</th><th data-k="b" class="num">Blended</th><th data-k="c" class="ctx">Context</th><th data-k="d" class="ctx">Released</th>
 </tr></thead><tbody id="rows"></tbody></table></div>
 <div class="foot" id="method"><b>Method.</b> Prices are published list rates per 1M tokens, pulled from the models.dev catalog on {data_date}. Blended = (3×input + output) / 4. Providers set their own prices; verify before committing volume. This index is independent and takes no placement fees. <a href="api/models.json"><b>JSON API</b></a> · <a href="providers/">Provider pages</a></div>
</section>
</div>
<script>{JS.replace("__DATA__", payload)}</script></body></html>"""


def build(rows, meta, slugs, page_slugs=None):
    if page_slugs is None:
        page_slugs = {p["slug"] for p in catalog.provider_summaries(rows, slugs)[:20]}
    doc = render(rows, meta, slugs, page_slugs)
    path = os.path.join(OUT, "index.html")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    return path, len(doc)


def main():
    rows, meta, slugs = catalog.load()
    path, size = build(rows, meta, slugs)
    print("wrote %s (%s bytes) | %d models | %d providers | data %s"
          % (path, format(size, ","), meta["counts"]["models"],
             meta["counts"]["providers"], meta["source"]["cache_modified"][:10]))


if __name__ == "__main__":
    main()
