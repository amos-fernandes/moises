Per-asset 5M-timestep run helpers

Files
- `run_single_5m_asset.ps1` — PowerShell helper to run a single asset's 5M-timestep training. It creates a temporary `scripts.config` override so the training script sees only the single asset and writes models under `src/model/5m_runs/<asset>`.
- `run_all_assets_5m.ps1` — Simple sequential loop that invokes `run_single_5m_asset.ps1` for a small asset map (edit as needed).

Usage
PowerShell (from repo root):

```powershell
# single asset (example for ETH)
.
\scripts\run_single_5m_asset.ps1 -AssetKey 'crypto_eth' -Ticker 'ETH-USD' -Timesteps 5000000

# run sequentially for a set of assets
.
\scripts\run_all_assets_5m.ps1
```

Estimates and schedule
- Per-asset timeline (approximate, depends on hardware):
  - 5M timesteps on CPU-only machine (typical laptop): 4–10+ days depending on env complexity and model size.
  - With a decent GPU (mid-range): 1–3 days.
  - With multi-GPU or distributed setup: <1 day if properly parallelized.

Recommended staging
1. Smoke run (done): 5k timesteps to validate correctness and artifact paths. Typical time: 5–20 minutes.
2. Pilot run: 50k–200k timesteps per asset to observe training curves and checkpointing. Typical time: hours.
3. Full 5M run: only after pilot confirms stability and model checkpoints are saved reliably.

Notes
- The scripts create a temporary `scripts/config.py` under a temp folder and prepend it to PYTHONPATH so it overrides project `scripts.config` during the run; the temp folder is removed after the run.
- Edit `run_all_assets_5m.ps1` to match your desired asset list and parallelization strategy.
- Consider using containerized runs (Docker) or a cluster when running many 5M jobs concurrently.
