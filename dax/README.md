# dax/ — Dynamic AI Exposure index (W0 infra)

Monorepo layout per docs/DAX_Execution_Plan_with_AI_Agents.md §W0:

| dir | stage | notes |
|---|---|---|
| `data_raw/` | W2 | immutable inputs, checksum every file on arrival |
| `data_built/` | W2 | derived tables; every file needs `<file>.lineage.json` |
| `mapping/` | W3 | mappings A (GDPval), B (Tolan-style), C (rescoring) |
| `capability_panel/` | W4 | capability/cost panel — own budget line, not the L1 envelope |
| `index/` | W5 | DAX index + EIV sensitivity |
| `analysis/firststage_synthetic/` | pre-gate | synthetic first stage only, allowed before GATE 1 |
| `analysis/outcomes/` | **SEALED** | does not exist in git until tag `v1.0-preregistered`; guarded 3 ways (see below) |
| `memo/` | W1 | design memo → GATE 1 tag target |
| `paper/`, `release/` | W9/W10 | release excludes outcomes/first-stage/NDA |

## The pre-registration seal (W0 req 2)

1. **CI**: any committed file under `dax/analysis/outcomes/` fails the build
   until the `v1.0-preregistered` tag exists (.github/workflows/ci.yml).
2. **Runtime**: every outcomes script must start with
   `import preregistration_guard` (from `dax/analysis/`) — it SystemExits
   pre-tag, fail-closed. `make guard` shows the current seal state.
3. **NDA**: CI greps the whole repo for OpenAI-NDA aggregate markers; NDA
   data never enters this repo regardless of tag state.

## Lineage (W0 req 4)

Every pipeline stage ends with
`python ../ops/runner/lineage.py <output> <input> [...]`.
CI verifies each committed artifact in `data_built/`, `capability_panel/`,
`index/` carries a sibling `.lineage.json`.

Environment: `requirements.txt` (Python 3.11); R 4.x deps listed there too.
Makefile targets: data, map, panel, index, validate, firststage_synth,
outcomes, robustness, paper (unbuilt stages exit loudly).
