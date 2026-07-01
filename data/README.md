# Datasets

**Raw data is never committed to this repo** (see `.gitignore`). Each dataset retains its
own license; download it yourself into `data/<dataset>/` and point the loader at it. This
directory documents provenance, license, and access route for every dataset the pipeline
supports.

| Dataset | Signals | Subjects | Sessions / states | Cross-day? | Access | License |
|---|---|---|---|---|---|---|
| **Blasco 2018** (anchor) | PPG, ECG, ACC, GSR | 25 | 3 activity states, single day | No (proxy via states) | Released with paper (doi:10.3390/s18092782) | See paper / dataset page |
| PPG-DaLiA | PPG, ACC, ECG | 15 | 8 activities, single session | No | UCI ML Repository | CC BY 4.0 (verify) |
| PTT-PPG | ECG, PPG, ACC | 22 | multiple activity states, single day | No | PhysioNet | PhysioNet open (verify) |
| PhysioNet Exam-Stress | E4 (PPG/EDA/ACC/TEMP) | ~10 | 3 exam sessions | **Yes** (true cross-day) | PhysioNet | Open (verify) |
| BioSec2 | PPG | ~100 | 2 sessions ~17 days apart | **Yes** | Request / material transfer | Restricted (verify) |

## Provenance rules

- Record the exact download URL, date, and file checksums in the loader's docstring or a
  per-dataset `PROVENANCE.txt` when you download.
- Confirm each license before use; the "verify" notes above mean the license has not yet
  been re-checked against the source this session.
- Loaders map each dataset into the **common schema** (see `src/wfab/`) so the analysis
  code is identical across datasets.

## Layout expected by loaders

```
data/
  blasco2018/      # you download here
  ppg_dalia/
  ptt_ppg/
  exam_stress/
  biosec2/
```
