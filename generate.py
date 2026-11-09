#!/usr/bin/env python3
"""Build the LLM Price Index site from the local models.dev catalog.

Input : %LOCALAPPDATA%/hermes/models_dev_cache.json
Output: public/index.html (self-contained, data embedded as JSON)

Only models with a published cost are included. One row per provider+model,
because the same model is often cheaper at a different provider.
"""
import json, os, datetime, html

CACHE = os.path.expandvars(r"%LOCALAPPDATA%\hermes\models_dev_cache.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

def main():
    d = json.load(open(CACHE, encoding="utf-8"))
    rows = []
    for pid, prov in d.items():
        pname = prov.get("name") or pid
        for mid, m in (prov.get("models") or {}).items():
            if not isinstance(m, dict):
                continue
            mods = m.get("modalities") or {}
            if "text" not in (mods.get("input") or []) or "text" not in (mods.get("output") or []):
                continue  # text-in/text-out models only
            if not (m.get("limit") or {}).get("context"):
                continue
            cost = m.get("cost") or {}
            inp = cost.get("input")
            out = cost.get("output")
            if inp is None or out is None:
                continue
            rows.append({
                "n": m.get("name") or mid,
                "p": pname,
                "i": round(float(inp), 4),
                "o": round(float(out), 4),
                "c": (m.get("limit") or {}).get("context") or 0,
                "f": m.get("family") or "",
                "d": (m.get("release_date") or "")[:10],
                "b": round((3 * float(inp) + float(out)) / 4, 4),
            })
    rows.sort(key=lambda r: (r["b"], r["n"]))
    data = json.dumps(rows, separators=(",", ":"))
    today = datetime.date.today().isoformat()
    providers = len({r["p"] for r in rows})

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM Price Index — cost per million tokens</title>
<meta name="description" content="Compare published prices for {len(rows):,} LLM models across {providers} providers. Input, output and blended cost per 1M tokens, with a cost calculator.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--bg:#FBFBFD;--surface:#fff;--ink:#0A0C10;--ink2:#3A424E;--muted:#5B6472;--line:#E6E9EF;--blue:#1D4ED8;--soft:#EEF3FF;--chip:#F3F5F9;--ok:#0F7B4F;--r:10px;--sans:"Inter",system-ui,sans-serif;--mono:"JetBrains Mono",monospace}}
*{{box-sizing:border-box}}html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;font-feature-settings:"cv01","ss03"}}
a{{color:inherit;text-decoration:none}}.wrap{{max-width:1160px;margin:0 auto;padding:0 28px}}
header{{background:var(--surface);border-bottom:1px solid var(--line)}}.bar{{height:64px;display:flex;align-items:center;gap:24px}}
.brand{{font-weight:700;font-size:17px;letter-spacing:-.03em;display:flex;gap:9px;align-items:center}}
.mark{{width:22px;height:22px;border-radius:6px;background:var(--blue);color:#fff;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700}}
.spacer{{flex:1}}nav{{display:flex;gap:20px;font-size:13.5px;font-weight:500;color:var(--muted)}}nav a:hover{{color:var(--ink)}}
.hero{{padding:54px 0 30px;border-bottom:1px solid var(--line)}}
.eyebrow{{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--blue);margin-bottom:16px}}
h1{{font-weight:600;font-size:clamp(38px,4.6vw,56px);line-height:1.02;letter-spacing:-.045em;margin:0 0 14px;max-width:760px}}
.lede{{color:var(--muted);font-size:16.5px;max-width:620px;margin:0 0 24px}}
.calc{{display:grid;grid-template-columns:1.4fr .7fr .7fr .9fr;gap:0;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--surface);max-width:820px;box-shadow:0 1px 2px rgba(10,12,16,.04)}}
.calc > *{{border:0;background:transparent;padding:0 14px;height:48px;font-family:var(--sans);font-size:13.5px;color:var(--ink);outline:none}}
.calc select{{border-right:1px solid var(--line);font-size:13px}}
.calc input{{border-right:1px solid var(--line);font-family:var(--mono);font-size:12.5px}}
.calc .out{{display:flex;align-items:center;justify-content:flex-end;font-family:var(--mono);font-size:14px;font-weight:500;color:var(--blue);white-space:nowrap}}
.main{{padding:30px 0 60px}}
.tools{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:14px}}
.tools input{{flex:1;min-width:220px;height:40px;border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:0 12px;font-family:var(--sans);font-size:13.5px;outline:none}}
.tools select{{height:40px;border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:0 10px;font-size:13px;color:var(--ink2);outline:none}}
.count{{font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:auto}}
.table{{background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
thead th{{position:sticky;top:0;background:var(--surface);text-align:left;padding:11px 14px;font-family:var(--mono);font-size:9.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap}}
thead th:hover{{color:var(--blue)}}
tbody td{{padding:10px 14px;border-bottom:1px solid var(--line);vertical-align:baseline}}
tbody tr:hover{{background:var(--soft)}}
.mname{{font-weight:600;letter-spacing:-.01em}}
.prov{{color:var(--muted);font-size:11.5px}}
.num{{font-family:var(--mono);font-size:11.5px;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.ctx{{font-family:var(--mono);font-size:10.5px;color:var(--muted);text-align:right}}
.tag{{font-family:var(--mono);font-size:9px;padding:2px 6px;border-radius:4px;background:var(--chip);color:var(--muted);text-transform:uppercase;letter-spacing:.05em}}
.foot{{padding:26px 0 40px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);margin-top:30px}}
.foot b{{color:var(--ink)}}
@media(max-width:800px){{.calc{{grid-template-columns:1fr 1fr}}.calc select{{grid-column:span 2;border-right:0;border-bottom:1px solid var(--line)}}.calc .out{{border-top:1px solid var(--line)}}nav{{display:none}}thead th:nth-child(5),tbody td:nth-child(5){{display:none}}}}
</style></head><body>
<header><div class="wrap bar"><a class="brand" href="/"><span class="mark">$</span>LLM Price Index</a><nav><a href="#table">Compare</a><a href="#method">Method</a></nav><div class="spacer"></div><span class="tag">updated {today}</span></div></header>
<div class="wrap">
<section class="hero">
 <div class="eyebrow">Published prices · {len(rows):,} models · {providers} providers</div>
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
 <div class="foot" id="method"><b>Method.</b> Prices are published list rates per 1M tokens, pulled from the models.dev catalog on {today}. Blended = (3×input + output) / 4. Providers set their own prices; verify before committing volume. This index is independent and takes no placement fees.</div>
</section>
</div>
<script>
const DATA={data};
const $=id=>document.getElementById(id);
let rows=DATA.slice(), sortK='b', sortAsc=true;
const fmt=n=>n===0?'free':n>=0.01?n.toFixed(2):n.toFixed(4);
const ctx=n=>n>=1000000?(n/1000000).toFixed(1)+'M':n>=1000?(n/1000).toFixed(0)+'k':'—';
const provs=[...new Set(DATA.map(r=>r.p))].sort();
provs.forEach(p=>{{const o=document.createElement('option');o.value=p;o.textContent=p;$('prov').appendChild(o);}});
const picks=DATA.filter(r=>r.b>0&&r.c>=100000).slice(0,120);
picks.forEach((r)=>{{const idx=DATA.indexOf(r);const o=document.createElement('option');o.value=idx;o.textContent=r.n+' · '+r.p;$('cmodel').appendChild(o);}});
function render(){{
  const q=$('q').value.toLowerCase(), p=$('prov').value, minc=+$('ctx').value, incFree=$('free').checked;
  rows=DATA.filter(r=>(!q||(r.n+' '+r.p+' '+r.f).toLowerCase().includes(q))&&(!p||r.p===p)&&(r.c>=minc)&&(incFree||r.b>0));
  rows.sort((a,b)=>{{const x=a[sortK],y=b[sortK];return (typeof x==='string'?x.localeCompare(y):x-y)*(sortAsc?1:-1);}});
  const slice=rows.slice(0,400);
  $('rows').innerHTML=slice.map(r=>`<tr><td><div class="mname">${{r.n}}</div><div class="prov">${{r.f||''}}</div></td><td class="prov">${{r.p}}</td><td class="num">$${{fmt(r.i)}}</td><td class="num">$${{fmt(r.o)}}</td><td class="num" style="font-weight:600">$${{fmt(r.b)}}</td><td class="ctx">${{ctx(r.c)}}</td><td class="ctx">${{r.d||'—'}}</td></tr>`).join('');
  $('count').textContent=rows.length.toLocaleString()+' models'+(rows.length>400?' · showing first 400':'');
}}
function cost(){{const r=DATA[+$('cmodel').value];if(!r)return;const i=+$('cin').value||0,o=+$('cout').value||0;const c=(i/1e6)*r.i+(o/1e6)*r.o;$('cost').textContent='$'+c.toFixed(c<1?4:2);}}
document.querySelectorAll('thead th').forEach(th=>th.onclick=()=>{{const k=th.dataset.k;sortAsc=sortK===k?!sortAsc:true;sortK=k;render();}});
['q','prov','ctx','free'].forEach(id=>$(id).oninput=render);
['cmodel','cin','cout'].forEach(id=>$(id).oninput=cost);
render();cost();
</script></body></html>"""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "index.html")
    open(path, "w", encoding="utf-8").write(doc)
    print("wrote", path, len(doc), "bytes |", len(rows), "models |", providers, "providers")

if __name__ == "__main__":
    main()
