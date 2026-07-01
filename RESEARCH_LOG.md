# Research log

This is the project's lab notebook. It records decisions, rationale, and dead ends
in the order they happened — including the ones that didn't work out. It is meant to
be read top-to-bottom as the story of how the project reached its conclusions.

---

## 2026 — Project framing

**Goal (as refined with the project owner).** Find whether a *combination* of body
signals, captured together in a few seconds on a wearable, can authenticate a person
"uniquely, credibly, consistently, and fast" — the password-like unlock idea.

**Reality check performed before any code.** A literature + feasibility review
established three hard constraints on the *product* version of this idea:

1. **Accuracy collapses across sessions.** Fused within-session numbers look excellent
   (near-zero EER) but degrade sharply across days; single-signal wrist PPG rises to
   ~23% EER cross-day (Sancho et al. 2018, doi:10.3390/s18051525). The best *honest*
   cross-session fusion number found still includes a fingerprint and lands at ~6.9%
   EER (arXiv:2412.05660) — thousands of times short of Touch ID / Face ID.
2. **Hardware access.** No consumer wrist device exposes the simultaneous *raw* signals
   a hobbyist would need without privileged/partner access.
3. **Platform lock.** iOS/Android do not let a third-party biometric gate device unlock.

**Decision.** Do *not* pursue a shippable unlock. Pursue the **honest scientific
contribution** the field skips: a cross-session-honest benchmark of fast multi-signal
wrist fusion, quantifying how far it falls short of the security bar. Framed as a
benchmark / negative result, this is publishable and beginner-feasible on public data.

**Novelty scan (verified).** The single closest prior work is Blasco & Peris-Lopez 2018
(doi:10.3390/s18092782): PPG+ECG+ACC+GSR on 25 subjects across 3 activity states, fused,
AUC 0.99 / EER 0.02 with 60 s training — dataset released publicly. Crucially, its own
stated limitation is that signals "were acquired only once on a given day" and cross-day
analysis is "recommended in a future study." That future study is our opening. Full scan:
`novelty_scan.md` (kept with the project record).

**Anchor dataset.** Blasco 2018 — we extend the exact paper that did the within-session
version.

---

### Open questions being carried forward
- Cross-DAY data is the weak link: the multi-signal sets are single-day. Plan uses
  Blasco's 3 activity states as a cross-condition proxy, plus PhysioNet Exam-Stress
  (3 sessions) for a true — if small — cross-day test.
- Expected headline result is a negative one. That is acceptable and is the point.
