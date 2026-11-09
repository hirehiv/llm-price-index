# Data changelog

Every rebuild reads the models.dev cache through `catalog.py`; this file records
what changed in the published data, not every code change.

- **2026-11-09** — switched the build to the fresh profile cache
  (`models_dev_cache.json`, modified 2026-11-09 15:41 EET). Published dataset:
  **8,449** priced provider+model rows across **226** providers, up from
  **6,913** rows / **193** providers built from the 2026-08-28 cache.
  Added `api/models.json`, `api/providers.json`, `docs/api/`, and 20 provider pages.
