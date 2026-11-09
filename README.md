# LLM Price Index

Published cost per 1M tokens for every text model in the models.dev catalog.
Blended = (3*input + output) / 4. One row per provider+model, because the same
model is often cheaper at a different provider.

Live: https://hirehiv.github.io/llm-price-index/

## API

<!-- api:start -->
- 8,449 priced provider+model rows across 226 providers (data 2026-11-09, built 2026-11-09T14:29:00Z).
- [`api/models.json`](api/models.json) — one row per provider+model.
- [`api/providers.json`](api/providers.json) — provider summaries.
- Docs and schema: [`docs/api/`](docs/api/index.html).
- Provider pages: [`providers/`](providers/index.html) — top 20 by model count.
<!-- api:end -->

## Build

```
python build.py
```

Reads the models.dev cache through `catalog.py`, then writes `index.html`,
`api/*.json`, `docs/api/index.html` and the top-20 `providers/` pages.
GitHub Pages serves the repo root on `main`.

Data source: https://models.dev
