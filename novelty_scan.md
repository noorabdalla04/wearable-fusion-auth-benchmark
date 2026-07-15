# Novelty scan, fast multi-signal wearable authentication

**Question addressed:** Is "find a combination of biomarkers, captured together in a few seconds on a wearable, that authenticates a person uniquely and consistently" a novel research direction, or has it been done?

**Method.** Systematic search of arXiv/OpenAlex (which indexes IEEE, Elsevier, MDPI *Sensors*, ACM), decomposing the idea into its facets and searching each; key prior-art papers pulled at full text. The Semantic Scholar full-text snippet endpoint (Asta) was unavailable (server-side timeouts) on the day of the scan, so paper *bodies* were spot-checked via direct full-text fetch of the two closest papers rather than a full snippet index. Confidence: **medium-high** for the headline verdict; the two decisive papers were read at full text.

## Verdict

The **literal idea is not novel.** "Fuse multiple wearable body signals to identify/verify a person" is an established subfield with its own surveys. The **disciplined version is plausibly novel and useful:** a *fast, single-shot, multi-signal wrist fusion* system evaluated *cross-session with subject-wise splits* and reported honestly against the fingerprint/Face-ID security bar, including where it fails. The opening exists specifically because prior work takes the flattering slice (within-session, or single-signal cross-session, or continuous-not-fast) and stops.

## What already exists (the prior art you must cite and beat)

**The single most on-target paper** is [Blasco & Peris-Lopez 2018, *On the Feasibility of Low-Cost Wearable Sensors for Multi-Modal Biometric Verification*](https://doi.org/10.3390/s18092782) (*Sensors*). It builds a low-cost wearable prototype capturing **PPG + ECG + accelerometer + GSR** on 25 subjects across three activity states (seated/walking/post-stroll), fuses them, and reports the best configuration (ECG+PPG+GSR) at **AUC 0.99 / EER 0.02 with 60 s of training**, and *makes its dataset public.* This is almost exactly the proposed system. **The one thing it explicitly did not do, and flags as its own key limitation, is cross-day evaluation:** in its own words, "the signals were acquired only once on a given day … an in-depth analysis of the permanence property (e.g., cross-day and long-term analysis) is recommended in a future study." That sentence is the doorway to the novel contribution.

**The cross-session reality is documented, for single-signal PPG.** [Sancho, Alesanco & García 2018, *Biometric Authentication Using the PPG: A Long-Term Feasibility Study*](https://doi.org/10.3390/s18051525) (*Sensors*) tests PPG across four databases and finds within-session EER of 1-8% but **up to 23.2% across different days**, quantifying exactly the permanence collapse that the fusion papers avoid measuring. It is single-signal, so it does not answer whether *fusion* survives the cross-day drop.

**Wearable multi-channel fusion for identity is done, but continuous, not fast.** Vhaduri & Poellabauer fuse coarse wearable channels (HR, calories, steps, distance) for [implicit authentication](https://arxiv.org/abs/1907.06563) and [across sedentary/non-sedentary states](https://arxiv.org/abs/1811.07060). This is background/continuous verification over long windows, the opposite of a few-seconds unlock.

**ECG+PPG fusion for identity exists** ([multimodal ECG+PPG identification, 2020](https://doi.org/10.1145/3423603.3424053); [multimodal physiological recognition, 2019](https://doi.org/10.1109/access.2019.2923856)), as does **single-signal cross-session ECG** ([A Key to Your Heart, 2019](https://arxiv.org/abs/1906.09181), 55 subjects, two sessions 4 months apart). **Fast few-seconds fusion capture** exists ([camera-PPG + fingerprint, 2024](https://arxiv.org/abs/2412.05660)), but leans on a fingerprint and reports the cross-session drop to **6.9% EER**. **Lightweight/small models for PPG auth** exist ([low-frame-rate hybrid, 2025](https://arxiv.org/abs/2511.04037); [CVT-ConvMixer, 2023](https://doi.org/10.3390/s24010015)). **PPG spoofing** is studied ([Video is All You Need, 2022](https://arxiv.org/abs/2203.00928)).

## The gap, stated precisely

No paper found satisfies all three simultaneously:
1. **Fast / single-shot** (a few-seconds window, excludes Vhaduri's continuous approach);
2. **Multiple signals fused, captured together** (not one signal; not carried by a fingerprint);
3. **Cross-session, subject-wise evaluation, reported honestly**, including a plain statement of how far short of fingerprint (~1/50,000 FAR) / Face ID (~1/1,000,000 FAR) it lands.

The Blasco multimodal prototype is (1)+(2) but *not* (3), and says so itself. The Sancho long-term study is (3) but *not* (2). Nobody has closed the triangle. That is the contribution: **a cross-session-honest benchmark of fast multi-signal wrist fusion, quantifying whether fusion's within-session advantage survives across days, on public data, reported as a result even when unflattering.**

## Why it is defensible and beginner-feasible

- **Data already exists and is public:** Blasco's own multimodal dataset (PPG+ECG+ACC+GSR, released with the paper); PPG-DaLiA (PPG+ACC+ECG, 8 activities); PTT-PPG (synchronized ECG+PPG+ACC); PhysioNet Exam-Stress (E4 multi-signal, 3 sessions → a genuine cross-day pilot); BioSec2 (PPG, two sessions ~17 days apart) as the cross-day baseline to beat.
- **No privileged hardware access needed**, this is a data-analysis contribution, not a shipped unlock.
- **A small/interpretable model is the appropriate vehicle** (tiny datasets, on-device framing), but it is not itself the novelty.

## Honest caveats

- The Blasco dataset makes the "novel combination" framing weak, the *combination* (PPG+ECG+ACC+GSR) is taken. Frame the contribution as the **cross-session evaluation and the honest security-bar accounting**, not a new signal set.
- Even done perfectly, the expected finding is that fast wrist fusion does **not** reach fingerprint/Face-ID security across days. That is a valuable negative/benchmark result, not a product.
- This scan is arXiv/OpenAlex-anchored; a full Semantic Scholar snippet pass and an IEEE Xplore / ACM DL manual check would harden it further before submission.
