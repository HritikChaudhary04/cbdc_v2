# Confirmation time in a permissioned retail CBDC: code, testbed and data

Companion material for the paper *"Confirmation time in a permissioned retail CBDC: a queueing model validated on a
Hyperledger Fabric testbed"* (H. Chaudhary et al.). It contains the analytical model and simulator, the Hyperledger
Fabric testbed used for all measurements, the analysis scripts, the result files behind every table and figure, and
the figure scripts.

## Quick start

Open **`reproduce_paper.ipynb`** (saved with its outputs). It reads the saved results and rebuilds the paper's main
tables and all figures in about a minute, without rerunning the long simulations. `make_reproduce_nb.py` regenerates
the notebook itself.

## Contents

| Folder | What it holds |
|---|---|
| `model/` | Analytical model (`cbdc_v2_formulas.py`), SimPy pipeline simulator (`cbdc_v2_core.py`), matrix-analytic MAP/PH code (`cbdc_v2_map.py`), **measured** parameters (`cbdc_v2_params.py`), the runners for every simulation table (`run*_measured.py`, `sweep_meas.py`, `map_measured.py`, `mapph_measured.py`) and their outputs (`res*_measured.json`). |
| `verification/` | Stand-alone checks of individual results (endorsement order statistic, block formation, ordering QBD, commitment, full chain, operating-point planner). |
| `testbed/cbdc-network/` | The Fabric network: 5 institutions with one peer each, 3 Raft orderers; Go wallet chaincode run as a service; build scripts (`scripts/01_generate.sh` to `06_init_accounts.sh`), benchmark driver (`07_benchmark.sh`, `collect.py`), failure and policy scripts, the campaign driver (`scripts/campaign.sh`) and all Caliper benchmark files. See its own `README.md`. |
| `analysis/` | Scripts that turn raw testbed rounds into the paper's numbers: `campaign_stats.py` (per-round and per-configuration statistics with 95% intervals), `params.py` (stage parameters), `predict2.py` (model against measurement), `cpu.py`, `contention.py`, `ext2.py`, `ext3.py` (contention correction), `ef_timeline.py` (failure and surge timelines), `sameblock_mc.py` (same-block conflict prediction), `texrows.py`. |
| `results/` | Processed results: `campaign_rounds.csv` (one row per measured round), `campaign_stats.csv` (mean, 95% interval, min, max per configuration and load), `stage_parameters.txt`, `model_vs_measured.txt`, `contention_model.txt`. |
| `figures/` | `scripts/` (one script per figure) and `output/` (PDF and PNG of every figure; `fig_pipeline.tex` is the TikZ schematic). |
| `data/raw/` | Raw testbed data: `campaign_data.tar.gz` (all reportable rounds: block-level CSVs, metrics, summaries, console logs), `EF_results.tar.gz` (failure and surge rounds) and `B10C_results.tar.gz` (B = 10 drift check). The full archive including raw peer and orderer logs (about 700 MB) is available on request. |

## Map from the paper to the files

| Paper item | Produced by | Data |
|---|---|---|
| Table tab:stageparams, Sec. 5.3 | `analysis/params.py` | raw campaign rounds |
| Tables tab:validation, Sec. 5.3; Fig. fig:validation | `analysis/predict2.py`, `analysis/texrows.py`, `figures/scripts/fig_validation.py` | `results/campaign_rounds.csv`, `results/model_vs_measured.txt` |
| Contention correction, Eq. (ps), Sec. 5.3 | `analysis/cpu.py`, `contention.py`, `ext2.py`, `ext3.py` | raw campaign rounds |
| Table tab:status, Sec. 4.1 | `model/run03_measured.py`, `run04_measured.py`, `sweep_meas.py` | `model/res03/res04/res10_sweep_measured.json` |
| Tables in Sec. 4.3 (replication, end-to-end) | `model/run04_measured.py`, `sweep_meas.py` | `model/res04_measured.json`, `res10_sweep_measured.json` |
| Sec. 4.5 and 6.1 (reference designs, comparison) | `model/run09_measured.py` | `model/res09_measured.json`, `res09_priority_classes_measured.json` |
| Sec. 4.6 (capacity, operating point) | `verification/operating_point.py`, `model/cbdc_v2_formulas.py` | measured parameters |
| Sec. 4.7 (bursty arrivals, PH service) | `model/map_measured.py`, `model/mapph_measured.py` | `model/res_map_measured.json`, `res_mapph_measured.json` |
| Sec. 6.2 (block size), Fig. fig:blocksize | `model/run04_measured.py`, `figures/scripts/fig_block_size.py` | `model/res04_measured.json`, `results/campaign_rounds.csv` |
| Sec. 6.3 (institutions, threshold), Fig. fig:institutions | `model/run03_measured.py`, `figures/scripts/fig_institutions.py` | `model/res03_measured.json`, `results/campaign_rounds.csv` |
| Sec. 6.4 (validator failure) | `model/run10_failure_measured.py`, `analysis/ef_timeline.py` | `model/res10_failure_measured.json`, `EF_results.tar.gz` |
| Sec. 6.5 (surge, ramp), Fig. fig:surge | `model/run10_surge_measured.py`, `analysis/ef_timeline.py`, `figures/scripts/fig_surge.py` | `model/res10_surge_measured.json`, `EF_results.tar.gz` |
| Sec. 6.6 (load sweep), Fig. fig:loadcurve | `model/sweep_meas.py`, `figures/scripts/fig_loadcurve.py` | `model/res10_sweep_measured.json`, `results/campaign_rounds.csv` |
| Sec. 6.7 (contention), Fig. fig:contention | `analysis/sameblock_mc.py`, `figures/scripts/fig_contention.py` | `results/campaign_rounds.csv` |
| Fig. fig:dispatch, Sec. 4.2 | `figures/scripts/fig_endorsement_dispatch.py` | simulated on the fly |

## Reproducing

Requirements: Python 3.10 or later with `numpy`, `scipy`, `simpy`, `matplotlib`, `pyyaml`.

- **Model and simulation tables:** `cd model && python3 run04_measured.py` (and the other runners). Runners are resumable and
  write their JSON next to them; long ones stop after about 200 s per call and continue when run again.
- **Figures:** `cd figures/scripts && python3 fig_validation.py` (and the others); output goes to `figures/output/`.
  `fig_surge.py` panel (b) needs the failure and surge rounds: extract `EF_results.tar.gz` into `data/raw/EF_results/`
  or pass its path as the first argument.
- **Statistics from raw rounds:** extract `campaign_data.tar.gz`, copy the `analysis/` scripts and the `model/` modules into
  the extracted folder, and run `python3 campaign_stats.py` (then `params.py`, `predict2.py`, and so on).
- **Testbed:** see `testbed/cbdc-network/README.md`. Software used: Hyperledger Fabric 2.5.14, Fabric CA 1.5.17,
  Go 1.25.14 for the chaincode (base images pinned by digest in the Dockerfile), Docker 29.1.3, Compose 2.40.3,
  Caliper 0.7.1 with fabric-gateway 1.7.1, Node 22.23.3, Ubuntu 22.04.5 under WSL 2. Host: Intel Core i5-13420H, one
  16 GB DDR5 module, one NVMe SSD; Linux limited to 8 GB and 12 threads, Fabric on 9 threads and Caliper on 3.
  The campaign (`scripts/campaign.sh <block>`) clears the page cache and pauses 30 s before every round.

## Notes

- All service parameters are those measured on the testbed at 25 and 50 TPS (paper Table tab:stageparams).
- Absolute values are specific to the single-host testbed; the procedure and scripts are what should transfer.
- The peak-load band (120 to 200 TPS) and the 2.5x surge are stated assumptions, not measurements.

## Licence

Code: MIT licence. Data and figures: Creative Commons Attribution 4.0 (CC BY 4.0). See `LICENSE`.
