# EGRR-DESC-001 W2 preregistration proposal

Status: BOUNDED REVISION FOR MAINTAINER INSPECTION ONLY.
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

## Constants proposed for a future freeze

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

These constants are not a registration identity. Before a freeze, an immutable
artifact must bind each case ID to its seed; source commit and normative file
SHA-256s; generator and exact draw order; canonical schema; and required Python,
NumPy and platform identity. The authorized study entrypoint must validate that
identity before generating or aggregating cases and fail closed on a mismatch.
The caller-supplied `expected_seeds` mapping in `verified_aggregate.py` is not
frozen scientific authority.

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

`verified_aggregate.py` checks supplied payload bytes against reported lengths
and SHA-256s, arm metadata, canonical digests, identities and the reported
`decode_ok` flag. It does not run the EGR2 decoder on each payload. The future
authorized entrypoint must run the real decoder on the exact serialized bytes,
verify shape, K, indices, float16 corrections and reconstructed weights, then
score decoded calibration and evaluation outputs. It must bind the payload
digest, decoder/source identity and decode result to the case evidence before
aggregation; missing or mismatched provenance vetoes the mean. A constructed
negative test with forged `decode_ok=true` and plausible metadata on non-EGR2
bytes is proposed for that entrypoint, not implemented or run. Existing aggregate
tests use arbitrary constructed payload bytes and cannot prove decoder provenance.

Machine-checkable failure contract:

- malformed fixed registration returns global `INSTRUMENT_FAILED` with
  `INVALID_FIXED_REGISTRATION`; it does not raise or continue aggregation;
- serialization/CRC/byte-count/decode failures retain their arm, stage, code
  and status and veto the full-set mean;
- invalid/nonfinite/negative MSE is `INVALID_NUMERIC`; zero magnitude MSE is
  `UNDEFINED_RATIO/ZERO_DENOMINATOR`; finite ratio overflow is
  `UNDEFINED_RATIO/RATIO_NONFINITE`;
- summary precedence changes only the derived summary and never deletes a
  lower-priority causal error;
- a valid full-set mean requires exactly 100 unique registered cases, every
  required arm and payload, valid identities/seeds/digests and 100 valid paired
  ratios. No failed case is omitted, replaced or regenerated.

## Numbered instrument predictions and executable fixtures (M2/M5)

These are fresh post-freeze instrument checks, not predictions of compression
improvement. Earlier constructed runs are disclosed below and are not fresh
evidence for these predictions.

- **P1 (D1):** the bounded constructed fixture is exactly 64×32, 3 bits and
  K=128, using constructed seed 901. Its corrected EGR2 payload has
  exactly 1311 EGR2 bytes. Any mismatch produces `INSTRUMENT_FAILED` and a
  nonzero gate.
- **P2 (D2):** repository deserialization reproduces exactly the registered
  float16-rounded constructed reconstructions. CRC, K, duplicate/out-of-range
  index, shape, or reconstruction sabotage is rejected.
- **P3 (D3):** the benign fixture prints stdout beginning
  `GATE: PASS — registered constructed payload {`, followed by canonical JSON
  and one newline; it exits 0 with empty stderr. `--sabotage` prints exactly
  `GATE: FAIL — planted CRC corruption detected` plus one newline on stdout,
  exits 1 and has empty stderr. These are constructed qualification contracts.
- **P4 (D4), level A:** the existing constructed 100-record stand-in qualifies
  completeness and fail-closed logic. Tests cover missing payload sets,
  duplicate records, altered seed identities, missing arms, altered payloads and
  digests, and malformed registration. It does not establish scientific cases.
- **P4 (D4), level B — NOT RUN:** after freeze and separate execution approval,
  all 100 registered scientific IDs must yield a case envelope or explicit
  failure. Missing or duplicate records, altered seeds, incomplete evidence and
  invalid aggregation inputs must block the full-set mean and remain in the
  manifest. The future entrypoint must explicitly sabotage these conditions and
  verify rejection; no surviving subset substitutes for the 100.
- **P5 (D5):** constructed pairs `(0.8,1)`, `(1,1)`, `(1.2,1)` retain signed
  improvements `+0.2`, `0`, `-0.2` within absolute tolerance `1e-12`; deletion
  of the negative record prints the registered failure and exits 1.

Exact constructed qualification commands and expected contracts:

| Prediction | Constructed command | Expected contract |
|---|---|---|
| P1, P2, P3 benign | `python reproducibility/egrr_desc_001_termux/registered_fixture_gate.py` | 64×32/K=128, 1,311 bytes; stdout starts `GATE: PASS — registered constructed payload {` and ends in one newline; empty stderr; exit 0 |
| P2, P3 sabotage | same command with `--sabotage` | stdout exactly `GATE: FAIL — planted CRC corruption detected` plus one newline; empty stderr; exit 1 |
| P2 adversarial EGR2 cases | `cd experiments/egrr_issue28 && python -m pytest -q test_egr2_integration.py` | four tests; exit 0 |
| P4 level A only | `cd experiments/egrr_issue28 && python -m pytest -q test_verified_aggregate.py` | constructed malformed, missing, duplicate, altered-seed, corrupted and veto cases retained/blocking; exit 0; level B NOT RUN |
| P5 benign | `cd experiments/egrr_issue28 && python descriptive_reporting_gate.py` | exact pass message; exit 0 |
| P5 sabotage | same command with `--sabotage` | exact reporting-completeness failure; exit 1 |

The pre-existing `structural_gate.py` 16×8/K=8 fixture remains an engineering
test but is not the registered P1 1,311-byte fixture. The commands above are
qualification evidence now and must be run fresh after freeze to count under
M11; their pre-registration results cannot confirm P1–P5.

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

Governing METHOD.md identity: commit
`2f2f2430b6bd4d1e6c42c82add3b32c00cc9c4f9`, blob
`6e4247ced1f2eef8b3c9917624d17d46d5bb80aa`. The instrument commit contains
that unchanged blob. WORKFLOW.md and CONTROLS.md identities below are likewise
the blobs present at the proposed instrument commit.

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

Corrected-wrapper macOS qualification evidence is retained at
`reproducibility/egrr_desc_001_termux/evidence/macos-2026-10-17/`.
It was produced from an isolated sparse clean checkout plus a temporary local,
unpublished verification-package commit. The wrapper recorded
`checkout_clean=true`, normative source identity success, Python 3.14.5,
NumPy 2.4.6, pytest 9.1.1 and macOS ARM64. Its twelve checks all met their
registered exit/message conditions; the three same-input outputs were exactly
equal with SHA-256
`7f06becf77c6daeb806ec2833f6123e9c777e407f1cac1e089fc664fae901afc`.
The structured JSON SHA-256 is
`22591c0951fed15fa3f6350aeff7dae3171d7d247df9d56f68a35484a7617a90`.
This is self-tested macOS engineering evidence, not Android execution,
cross-platform numerical equivalence or fresh post-freeze confirmation.

Chad Holland's October 19 [Android device report](https://github.com/sunny-kavixo/principia-artificialis/pull/1#issuecomment-6266462875)
records owner-operated execution from clean detached checkout
`52915857c8bddee66cf86d48c5c8cbc5807168a5` on Samsung Galaxy S25 Ultra,
Android 17 ARM64, Termux, Python 3.14.6, NumPy 2.4.4 and pytest 9.1.1.
The submitted verifier reported `verification_exit=0`, 12/12 checks, 111
constructed regression tests, four EGR2 integration tests, expected CRC and
reporting sabotage exits, and three identical C-NOISE stdout byte streams with
SHA-256 `7f06becf77c6daeb806ec2833f6123e9c777e407f1cac1e089fc664fae901afc`.
This digest matches the retained macOS constructed-probe report only. The raw
Android archive remains on the owner's device; its reported SHA-256 is
`ba7722bfcbc0d60ea5468f99e2bb468b8561a0904c33f32815ce9c6b8f531d8d`.
It has not been independently retrieved or hash-verified after transfer.
These are accepted reported engineering checks, not scientific findings.

## Trigger table (M16)

| Trigger | Control | Answer and proposed disposition |
|---|---|---|
| Feasibility | C-FEAS | No — the target is the exact named 100-case set; no external eligibility count determines inclusion. |
| Noise | C-NOISE | Yes — `noise_probe.py` uses constructed seed 902, magnitude selection, one decoded payload and one MSE on 32 inputs; it does not exercise covariance candidate selection or separate decoded calibration/evaluation scoring. Three same-input repeats were byte-identical on macOS and on the reported Android run; the constructed stdout digest matched across those two reports. A new constructed-only repeated covariance-path probe is required before freeze, using no reserved seed and recording exact command, source hash, environment, exits, raw output and an explicit equality/tolerance policy before execution. It is proposed, not implemented or passed. The paired-ratio consistency policy remains `rel_tol=1e-12`, `abs_tol=1e-15`; complete cross-platform numerical equivalence is unproven. |
| Statistics | C-STAT | No — no quantity is used to infer a population rate, mean, probability or difference. The exact finite set is described. |
| Evidence | C-EVID | No — the scientific question is not whether a rule handles evidence freshness; integrity metadata do not certify scientific truth. |
| Independence | C-INDEP | Yes — the reported Android execution independently ran repository-provided engineering checks at `5291585`. The EGR2 decoder was the repository decoder, not an independently implemented decoder; no scientific replication is claimed. |
| External | C-EXT | Yes — prior art and Chad Holland's reviews influenced the design. Preserve exact GitHub records/URLs, authorship, dates and hashes; do not reconstruct quotations. |
| Device | C-DEVICE | Yes — the corrected wrapper was reported executed on Android 17 ARM64 at `5291585` with Python 3.14.6, NumPy 2.4.4 and pytest 9.1.1; 12/12 checks passed. Raw JSON/stdout/stderr and the archive are retained on the owner's device, not independently retrieved after transfer. C-DEVICE's post-transfer identity check remains outstanding if a transferred archive is relied upon. The future study environment is undecided. |
| Verdict code | C-BUILD | Yes — missing/malformed inputs deny validity; veto failures block aggregation; benign and sabotage paths must both be run. |
| Exploration | C-EXPLORE | Yes — F-003 and calibration-only exploration preceded this design. Preserve them as exploratory and never promote them as study evidence. Neither registered seed block has been inspected. |
| Method comparison | C-METHCOMP | Yes — six methods are compared. The separate methodology-comparison experiment is study-specific and UNRUN; it is not imported as a generic procedure. This registration supplies EGRR's own fixed protocol and controls. |

C-EXT records used here include Chad Holland's October 16 Android verification
review (`pullrequestreview-5546391205`) and bounded-revision review
(`pullrequestreview-5547377495`) at their exact PR URLs. They remain attributed
external review statements; they are not reconstructed scientific evidence or
implied endorsement of the hypothesis.
The October 19 [engineering report](https://github.com/sunny-kavixo/principia-artificialis/pull/1#issuecomment-6266462875)
and [read-only P0 review](https://github.com/sunny-kavixo/principia-artificialis/pull/1#issuecomment-6266590730)
are additional attributed external records, not independent archive custody.

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
- The October 19 Android verifier reported the 12/12 corrected-wrapper checks
  and 111 constructed regression tests passing. Raw Android evidence remains
  locally retained and has not been independently retrieved after transfer.
- The EGR2 integration test uses the repository serializer and decoder; it is
  not an independent decoder implementation.
- CRC32 detects accidental corruption and is not authenticity protection.
- Float encoding stabilizes serialization, not BLAS/platform arithmetic.
- Equal payload bytes do not establish runtime or memory equivalence.
- Synthetic Gaussian linear-layer observations cannot establish general-LLM,
  production, device-performance, novelty, or population claims.
- Any invalid case makes the full-set mean unavailable; this may leave the
  descriptive question partly unanswered and must not trigger regeneration.

## W2/M16 decisions requiring maintainer review

| # | Decision | Existing evidence | Required correction | Current status | Remaining maintainer decision | Execution authorized? |
|---:|---|---|---|---|---|---|
| 1 | Descriptive seed IDs | `380000`–`380099` proposed; never generated; `280000`–`280099` reserved for population P1 | Keep the blocks distinct and descriptive seeds ungenerated | Acceptable in principle, not frozen | Accept or revise exact mapping | No |
| 2 | Normative instrument identity | Android verifier at `5291585` reported nine expected source SHA-256s matching candidate `29c63fe` | Bind immutable source commit/file hashes, case map, generator/draw order, schema and environment at future entrypoint | Candidate qualified for constructed scope | Approve instrument identity and entrypoint authority contract | No |
| 3 | C-NOISE / C-DEVICE | Three magnitude-probe repeats identical on reported Android; digest matches retained macOS report; Android archive retained locally | Constructed covariance-path repeats before freeze; decide transfer custody and verify digest/identity if transferred | Partial qualification; proposed probe not implemented or run | Approve probe and device evidence threshold | No |
| 4 | M16 trigger controls | Trigger answers above; independent repository engineering execution; C-METHCOMP study-specific and unrun | Keep C-INDEP scope and C-METHCOMP boundary explicit | Draft answers, pending review | Accept or revise trigger dispositions | No |
| 5 | Numerical, failure and evidence contracts | Existing constructed fail-closed tests; exact-float encoding; tiny-positive warning; five-level precedence | Separate P4 levels and enforce real decoder provenance, completeness and frozen identity in future study entrypoint | Well-motivated, not freeze-ready | Approve contracts and required entrypoint checks | No |
| 6 | Registration-only commit and protocol freeze | No approved registration or scientific run | Review corrected draft first; seek separate authorization for registration-only commit and freeze | HOLD | Explicitly authorize registration-only commit/freeze later; execution requires another decision | No |

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
