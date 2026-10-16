# EGRR-DESC-001 W2 preregistration proposal

Status: FREEZE-READY PROPOSAL FOR MAINTAINER INSPECTION ONLY.
NOT FROZEN. NOT APPROVED FOR EXECUTION. NOT RUN.

This document is a proposed standalone W2 registration. It must not be treated
as a frozen registration unless Chad Holland explicitly approves its remaining
decisions and it is committed separately under the repository's W2 process.

## W1 question and scope

For the exactly named 100 synthetic cases, what finite-set outcomes do six
fixed residual-correction methods produce under matched EGR2 corrected-arm
storage, without making population, general-LLM, production-memory, speed, or
novelty claims?

This is descriptive measurement of a finite named set. It is not the original
population P1 (`E[r] > 0.10`), which remains UNRESOLVED / NOT APPROVED. No
p-value, confidence interval, type-I-error guarantee, or inferential success
verdict is part of this study.

## Frozen constants proposed for approval

- Case IDs: exact strings `"000"` through `"099"`, in lexicographic order.
- Proposed case seeds: `380000` through `380099`, mapped in order to those IDs.
- Reserved and prohibited here: population-P1 seeds `280000` through `280099`.
- Generator: `numpy.random.default_rng(case_seed)` using PCG64.
- Draw order, sequentially from that generator, float64:
  1. `W = rng.normal(size=(64, 32))`
  2. `X_cal = rng.normal(size=(256, 64))`
  3. `X_eval = rng.normal(size=(1024, 64))`
- Random-arm generator: `default_rng(case_seed + 1000000)`.
- Quantizer: symmetric per-tensor, 3 bits, repository implementation below.
- Corrected arms: exactly `K=128`; uncorrected arm: `K=0`.
- Serializer/decoder: EGR2 v1, 27-byte little-endian header, packed signed
  codes, float16 corrections, CRC32.
- Corrected-arm expected size at 64×32, 3 bits, K=128:
  `27 + 768 + 128*(2+2) + 4 = 1311` bytes.
- Scoring: float64 decoded-output MSE,
  `mean((X @ (W - W_hat_decoded))**2)`, separately for calibration and
  evaluation inputs.
- Paired descriptive value, only after both MSEs validate:
  `r = 1 - MSE_covariance/MSE_magnitude`.
- A finite positive magnitude MSE is retained. Values in `(0, 1e-12]` receive
  `small_positive_denominator=true` but are not censored. Exact zero yields
  structured `UNDEFINED_RATIO/ZERO_DENOMINATOR`.
- Canonical schema: `EGRR-DESC-001-DRAFT-1`; exact finite float64 values use
  16-character lowercase big-endian IEEE-754 hex; UTF-8 canonical JSON uses
  sorted keys, compact separators, no BOM/trailing newline and `allow_nan=False`.

No seed in either prohibited range may be generated merely to review or freeze
this proposal.

## Case matrix and methods

Every case contains these exact six arms:

| Arm | Selection rule | Corrections | Role |
|---|---|---:|---|
| `covariance` | float16-aware greedy covariance gains using calibration only | 128 | candidate |
| `magnitude` | descending `abs(R)`, stable flattened-index ties | 128 | simplest primary rival (M14) |
| `input_rms` | descending `abs(R)*input_rms`, calibration only | 128 | rival |
| `random` | seeded uniform fixed-budget selection | 128 | rival/control |
| `uncorrected` | no correction | 0 | base quantizer control |
| `smallest_residual` | ascending `abs(R)`, stable ties | 128 | adverse diagnostic, not guaranteed to lose |

Selectors must never access `X_eval`. All corrected arms serialize corrections
as float16 and are scored only after the repository decoder reconstructs them.
Equal corrected payload bytes do not establish equal runtime or working memory.

## Required case and run evidence

Each immutable case envelope contains identity, generator/draw-order/source and
input hashes; all six arm records; payload bytes and SHA-256; correction counts
and indices; decode/integrity state; calibration/evaluation MSE; paired result;
append-only errors; and derived case status. All safely observable causal
errors are retained. Summary precedence is:

`INSTRUMENT_FAILED > SERIALIZATION_ERROR > INVALID_NUMERIC > UNDEFINED_RATIO > VALID`.

The full-set mean is produced only if all 100 registered identities, all six
arms, all integrity gates and all paired ratios are valid. Otherwise it is
`null`; no survivor mean, omitted case, substituted seed, or regeneration is
allowed. Records and manifests use lexicographic three-digit case-ID order,
followed by case-less failures.

Evidence must retain exact commands, expected and actual exits, raw stdout and
stderr, environment, dependency versions, Git/source identities, all payload
and canonical-evidence digests, and every negative/undefined result.

## Numbered instrument predictions (M2/M5)

These are fresh post-freeze instrument checks, not predictions of compression
improvement. Earlier constructed runs are disclosed below and are not fresh
evidence for these predictions.

- **P1 (D1):** every corrected arm in the registered structural fixture has
  exactly 1311 EGR2 bytes. Any mismatch produces `INSTRUMENT_FAILED` and a
  nonzero gate.
- **P2 (D2):** repository deserialization reproduces exactly the registered
  float16-rounded constructed reconstructions. CRC, K, duplicate/out-of-range
  index, shape, or reconstruction sabotage is rejected.
- **P3 (D3):** the benign structural gate prints `GATE: PASS — benign payload`
  and exits 0; `--sabotage` prints `GATE: FAIL — planted corruption detected`
  and exits 1.
- **P4 (D4):** all 100 registered IDs produce a visible case envelope or an
  explicit failure. Missing, duplicate, unexpected, malformed, or seed-mismatched
  inputs block aggregation and remain in the failure manifest.
- **P5 (D5):** constructed pairs `(0.8,1)`, `(1,1)`, `(1.2,1)` retain signed
  improvements `+0.2`, `0`, `-0.2` within absolute tolerance `1e-12`; deletion
  of the negative record prints the registered failure and exits 1.

No sign or magnitude of EGRR improvement on the 100 cases is predicted. The
study reports those observations without an inferential pass criterion.

## Anti-vacuity and stand-ins (M3/M4)

The real repository serializer, decoder, selectors, scoring, envelope,
canonical digest and aggregation code are used. Weights, inputs, payload
mutations, malformed registrations, and numerical examples in qualification
tests are explicitly constructed stand-ins, not study cases.

CRC and reporting sabotage paths must exit 1 while their benign controls exit
0. Malformed/absent registration values must return structured
`INSTRUMENT_FAILED`, never skip or raise an unhandled exception. A failed veto
cannot be outvoted by valid measurements (C-BUILD).

## Proposed implementation identity

Instrument commit submitted for review:
`29c63fe399fa1cbc45974717b8de14a1cd989401`.

Canonical governance identities at that commit:

```text
METHOD.md blob    6e4247ced1f2eef8b3c9917624d17d46d5bb80aa
WORKFLOW.md blob  b74b40203f5e4b2797a4c885edcf9c0bded3c418
CONTROLS.md blob  5d9661cec8044695e325375242aa677494a5c6b3
```

Source SHA-256:

```text
a73f6b6d8e970995cf2c89d6f6c417d11a27e8776a7a42acbdf121b1dd17e756  experiments/egrr_issue28/egrr.py
623fac46c82edff9373e4f17f17e4809b5fcc47daf1a0c9bb5ac7af2bae707e4  experiments/egrr_issue28/covariance_float16.py
79b1140dfeb1c0ad717ca3de735a3986285dc0c3b56704211369c83861abae04  experiments/egrr_issue28/descriptive_scoring.py
522168fb522e40dbe00e5f4659fd5022c123122c5f74b1d02f8ae39a67f5f189  experiments/egrr_issue28/descriptive_case_record.py
bcb4c5289c75a571446a90a35cc021129a49b7d241ece51a5caae2582526fbd5  experiments/egrr_issue28/case_envelope.py
c5de9fb5b42b6d6fd103f75b0020bd82195e6f667bf788b9b7237f5a463e9ceb  experiments/egrr_issue28/canonical_evidence.py
3384fe449c3482b1e86af321674c8ac119714e0cdaf1f95246a013eadbacb69b  experiments/egrr_issue28/verified_aggregate.py
1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1  experiments/egrr_issue28/storage.py
c1fa507ab1ec4b7e493ed5e388bdf31a9bc8a235e8ca5aaaab082ddb36f44097  experiments/egrr_issue28/packing.py
```

Proposed execution environment must be pinned again at freeze. The inspected
local environment is Python 3.14.5, NumPy 2.4.6, macOS ARM64. Chad Holland
independently reported a targeted constructed-fixture PASS at exact commit
`29c63fe` on Android Termux with Python 3.14.6 and NumPy 2.4.4: seven targeted
tests passed in 1.901 seconds with process exit 0, and the reported SHA-256
identities for `verified_aggregate.py` and `test_egr2_integration.py` matched
this proposal. This is attributed cross-environment instrumentation evidence,
not a freeze environment decision or scientific-hypothesis validation. The
review is recorded at:
https://github.com/sunny-kavixo/principia-artificialis/pull/1#pullrequestreview-5546391205

## Trigger table (M16)

| Trigger | Control | Answer and proposed disposition |
|---|---|---|
| Feasibility | C-FEAS | No — the target is the exact named 100-case set; no external eligibility count determines inclusion. |
| Noise | C-NOISE | Yes — floating-point/BLAS differences may alter numeric bits. A three-repeat constructed macOS fixture reported zero within-environment spread, and Chad reported the targeted constructed checks passing on Android Termux. No study arithmetic, cross-platform numerical-bit identity or full-suite equivalence was established. |
| Statistics | C-STAT | No — no quantity is used to infer a population rate, mean, probability or difference. The exact finite set is described. |
| Evidence | C-EVID | No — the scientific question is not whether a rule handles evidence freshness; integrity metadata do not certify scientific truth. |
| Independence | C-INDEP | Chad independently executed targeted repository tests on Android at `29c63fe` and verified the prior `f96cb12` instrumentation defect as corrected. The EGR2 decoder exercised was the repository decoder, not an independently implemented decoder; no scientific replication is claimed. |
| External | C-EXT | Yes — prior art and Chad Holland's reviews influenced the design. Preserve exact GitHub records/URLs, authorship, dates and hashes; do not reconstruct quotations. |
| Device | C-DEVICE | Yes — Chad reported Android Termux runtime/version, test count, duration, exit code and two matching source identities. Raw wrapper JSON/stdout/stderr were not supplied, so only the reported targeted scope is validated; study execution environment remains undecided. |
| Verdict code | C-BUILD | Yes — missing/malformed inputs deny validity; veto failures block aggregation; benign and sabotage paths must both be run. |
| Exploration | C-EXPLORE | Yes — F-003 and calibration-only exploration preceded this design. Preserve them as exploratory and never promote them as study evidence. Neither registered seed block has been inspected. |
| Method comparison | C-METHCOMP | Yes — six methods are compared. The separate methodology-comparison experiment is study-specific and UNRUN; it is not imported as a generic procedure. This registration supplies EGRR's own fixed protocol and controls. |

## Provenance and prior evidence (M13)

Originating investigator and responsible human: Sandeep (`sunny-kavixo`). Chad
Holland supplied maintainer-directed technical/statistical review, executed
the Python 3.14.6 Android Termux reproduction of the old `f96cb12` registration
defect, and independently reported the targeted corrected-instrument checks at
`29c63fe` passing on Android Termux. OpenAI ChatGPT GPT-6 materially assisted
drafting, implementation and self-testing. This is source/instrument review and
targeted constructed verification, not scientific replication.

The v0.4→v0.5 history, F-003 calibration-only exploration, statistical
feasibility negative finding at `e930358`, and merged W9 archive PR #48 remain
append-only. The archive is preservation, not study approval. Constructed test
runs through `29c63fe` are engineering qualification, not empirical EGRR
outcomes. No raw historical arrays or complete original logs may be invented.

## Known deviations and limits

- Constructed instrument checks were built and run before this final W2 file;
  they are disclosed qualification evidence, not unseen scientific outcomes.
  P1–P5 require a fresh run after any registration freeze (M11).
- Chad independently reported seven targeted constructed tests passing at the
  corrected commit on Python 3.14.6 / NumPy 2.4.4 Android Termux. The complete
  suite and this package's raw JSON/stdout/stderr artifacts were not supplied.
- The EGR2 integration test uses the repository serializer and decoder; it is
  not an independent decoder implementation.
- CRC32 detects accidental corruption and is not authenticity protection.
- Float encoding stabilizes serialization, not BLAS/platform arithmetic.
- Equal payload bytes do not establish runtime or memory equivalence.
- Synthetic Gaussian linear-layer observations cannot establish general-LLM,
  production, device-performance, novelty, or population claims.
- Any invalid case makes the full-set mean unavailable; this may leave the
  descriptive question partly unanswered and must not trigger regeneration.

## Decisions requiring Chad Holland's explicit agreement

1. Accept or revise the exact descriptive block `380000`–`380099`; no seed is
   touched by making this decision.
2. Accept `29c63fe` as the proposed instrument identity after reviewing the
   fail-closed and EGR2 corrections.
3. Decide whether Chad's targeted Python 3.14.6 Android Termux qualification
   suffices for C-NOISE/C-DEVICE or whether additional raw/full-suite evidence
   is required before freeze.
4. Approve the M16 answers, especially C-DEVICE and the self-contained handling
   of C-METHCOMP.
5. Approve the exact failure precedence, tiny-positive warning boundary,
   canonical schema and evidence package.
6. Explicitly authorize a separate registration-only commit. That commit still
   would not authorize study execution; execution requires a subsequent,
   separate maintainer decision.

## Freeze and execution gate

If all decisions above are resolved, create one registration-only commit with
no results and no instrument changes. Do not edit that registration afterward;
append dated deviations. Only after it is reviewed and explicitly frozen may a
separate authorization to run be considered. No current comment, PR, archive,
or constructed test supplies that authorization.

## Next unrun checkpoint (M15)

Obtain Chad Holland's review of this standalone proposal and explicit decisions
on the six items above. If he requires additional device evidence, run only the
constructed Termux verification package and retain its JSON/raw stdout/stderr.
Do not generate either research seed block.

Scientific status: **DRAFT / NOT FROZEN / NOT RUN**.
