"""Shared models.dev catalog loader for the LLM Price Index.

Every builder (index, API, provider pages) reads the data through this module,
so the published numbers can never diverge between products.

Source cache: the newest models.dev cache available to this Hermes profile.
Override with MODELS_DEV_CACHE=/path/to/cache.json.
"""
import datetime
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://hirehiv.github.io/llm-price-index"
SOURCE_NAME = "models.dev"
SOURCE_URL = "https://models.dev"

CACHE_CANDIDATES = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "profiles",
                 "pricewatch", "models_dev_cache.json"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes",
                 "models_dev_cache.json"),
)


def cache_path():
    override = os.environ.get("MODELS_DEV_CACHE")
    if override:
        if not os.path.isfile(override):
            raise SystemExit("BLOCKED: MODELS_DEV_CACHE does not exist: %s" % override)
        return override
    for path in CACHE_CANDIDATES:
        if os.path.isfile(path):
            return path
    raise SystemExit("BLOCKED: models.dev cache not found. Tried: %s"
                     % ", ".join(p for p in CACHE_CANDIDATES if p))


def slugify(name):
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "provider"


def _iso(ts):
    return datetime.datetime.fromtimestamp(
        ts, datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _num(value):
    return float(value)


def load(cache=None):
    """Return (rows, meta). One row per provider+model with a published price."""
    path = cache or cache_path()
    with open(path, encoding="utf-8") as fh:
        catalog = json.load(fh)

    rows = []
    for provider_id, provider in catalog.items():
        if not isinstance(provider, dict):
            continue
        provider_name = (provider.get("name") or provider_id).strip()
        for model_id, model in (provider.get("models") or {}).items():
            if not isinstance(model, dict):
                continue
            modalities = model.get("modalities") or {}
            if "text" not in (modalities.get("input") or []):
                continue
            if "text" not in (modalities.get("output") or []):
                continue
            context = (model.get("limit") or {}).get("context") or 0
            if not context:
                continue
            cost = model.get("cost") or {}
            if cost.get("input") is None or cost.get("output") is None:
                continue
            price_in = round(_num(cost["input"]), 4)
            price_out = round(_num(cost["output"]), 4)
            rows.append({
                "id": "%s/%s" % (provider_id, model_id),
                "name": (model.get("name") or model_id).strip(),
                "model_id": model_id,
                "provider_id": provider_id,
                "provider": provider_name,
                "input": price_in,
                "output": price_out,
                "blended": round((3 * price_in + price_out) / 4, 4),
                "context": int(context),
                "family": model.get("family") or "",
                "release_date": (model.get("release_date") or "")[:10],
            })

    rows.sort(key=lambda r: (r["blended"], r["name"].lower(), r["provider"].lower()))

    # Deterministic, collision-free slugs for every provider in the catalog.
    slugs = {}
    used = set()
    names = sorted({(r["provider"], r["provider_id"]) for r in rows})
    for name, provider_id in names:
        base = slugify(name)
        slug = base
        n = 2
        while slug in used:
            slug = "%s-%d" % (base, n)
            n += 1
        used.add(slug)
        slugs[provider_id] = slug

    meta = {
        "generated_at": datetime.datetime.now(
            datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": {
            "name": SOURCE_NAME,
            "url": SOURCE_URL,
            "cache_file": os.path.basename(path),
            "cache_modified": _iso(os.path.getmtime(path)),
        },
        "counts": {
            "models": len(rows),
            "providers": len(slugs),
        },
        "currency": "USD",
        "unit": "per 1M tokens",
        "blended_formula": "(3 * input + output) / 4",
    }
    return rows, meta, slugs


def provider_summaries(rows, slugs):
    """Aggregate priced rows per provider, sorted by model count desc."""
    by_provider = {}
    for row in rows:
        entry = by_provider.setdefault(row["provider_id"], {
            "id": row["provider_id"],
            "name": row["provider"],
            "slug": slugs[row["provider_id"]],
            "model_count": 0,
            "free_models": 0,
            "input_min": None, "input_max": None,
            "output_min": None, "output_max": None,
            "blended_min": None, "blended_max": None,
            "cheapest_model": None, "cheapest_blended": None,
        })
        entry["model_count"] += 1
        if row["input"] == 0 and row["output"] == 0:
            entry["free_models"] += 1
        for field, value in (("input_min", row["input"]), ("input_max", row["input"]),
                             ("output_min", row["output"]), ("output_max", row["output"]),
                             ("blended_min", row["blended"]), ("blended_max", row["blended"])):
            current = entry[field]
            if current is None:
                entry[field] = value
            elif field.endswith("_min"):
                entry[field] = min(current, value)
            else:
                entry[field] = max(current, value)
        if entry["cheapest_blended"] is None or row["blended"] < entry["cheapest_blended"]:
            entry["cheapest_blended"] = row["blended"]
            entry["cheapest_model"] = row["name"]

    return sorted(by_provider.values(),
                  key=lambda p: (-p["model_count"], p["name"].lower()))


def money(value):
    """Same formatting as the index table."""
    if value == 0:
        return "free"
    if value >= 0.01:
        return "%.2f" % value
    return "%.4f" % value
