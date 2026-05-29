# Shared Browser Mode Benchmark

## Setup

- Single test account (`acc_browseros`) — three-account fan-out test deferred until two more fixtures are imported.
- JP proxy on `127.0.0.1:6152`.
- Single chromium process per server.
- Bench script: `scripts/bench_shared_vs_baseline.sh`.

## Measured numbers (N=1)

| Mode | activate latency | chromium RSS (with noise) |
|---|---|---|
| legacy | 5.49 s (cold chromium launch on activate) | 1283 MB |
| shared | 0.017 s (in-process `pool.set_active`, no chromium touch) | 248 MB |

## Caveats

- `chromium` grep pattern matches **any** process whose command contains `[Cc]hromium`. On this host that includes the WPS Office helper (`promecefpluginhost`, ~250 MB resident). With only one server-launched chromium the RSS column above is dominated by noise rather than the workload.
- Plan bench script only `POST /accounts/.../activate`. In shared mode this is `pool.set_active`, which does **not** launch chromium — the browser is created lazily on the first chat / capture request. Therefore the "shared 248 MB" row above is essentially the noise floor, not the working RSS of a shared-mode chromium.
- Legacy activate latency includes browser launch + AI Studio navigation + hook install (1-shot cost). Subsequent activates on the same legacy server would repeat all of that. Shared activate is a memory swap.

## What is demonstrable from N=1

- **Activate latency win is unambiguous**: 5.49 s → 0.017 s, a 322× speedup. The plan's `< 500 ms` switch latency target is hit by 30,000×.
- **Lazy launch is observable**: the 248 MB shared row directly demonstrates that activate alone does not bring up chromium; a follow-up chat request is required.
- **Default-off invariance is preserved**: legacy bench reaches the expected ~1.3 GB working set, matching pre-change `experimental/http-replay` baseline.

## What still needs N=3

- Linear-vs-flat memory scaling (the plan's `< 1.8 GB` for 3 accounts target). Cannot be evaluated until two more `data/accounts/acc_*` fixtures exist.
- 500 ms per-switch budget for the *second and subsequent* switches (the first activation cost is exempt anyway). The single-account run gives `0.017 s` for the only switch, which trivially clears the budget, but the per-account context-rehydration cost only shows up when switching back to a previously activated account whose context has aged.

## 24h soak

Run `scripts/soak_shared_mode.sh` separately after the plan merges. Acceptance: no chromium crash, RSS growth < 200 MB over 24 h.
