# EGRR-DESC-001 — Fixed-Seed Descriptive Study

Status: DRAFT — DESIGN ONLY.
NOT FROZEN. NOT APPROVED FOR EXECUTION.

Originating investigator: sunny-kavixo.
Related: Issue #28, PR #37.
Original population P1: UNRESOLVED / NOT APPROVED.
Statistical-feasibility record: e930358.

## 1. Research scope

Describe the outcomes of exactly 100 predetermined synthetic
linear-layer cases without statistical population inference.

This is a finite-set descriptive exercise, not a test of
E[r] > 0.10 over the generating population.

No significance test, alpha claim, population confidence
interval, or population P1 success verdict is proposed.

## 2. Proposed case identities

Case IDs: 000 through 099.
Proposed descriptive seeds: 380000 through 380099, inclusive.

The original population-P1 proposed seeds 280000 through
280099 remain RESERVED and will NOT be generated, inspected,
or reused for this descriptive study.

For each case use NumPy default_rng(case_seed), PCG64.

Proposed draw order, from the same generator:
1. W = rng.normal(size=(64, 32))
2. X_cal = rng.normal(size=(256, 64))
3. X_eval = rng.normal(size=(1024, 64))

Use float64 arrays, sequential draws, and no seed substitution.
Random correction arm uses default_rng(case_seed + 1000000).

All evaluation inputs remain inaccessible to selectors.

The descriptive seed block is disjoint from the original
population-P1 proposal. Once any descriptive seed is executed,
that seed is consumed and cannot serve as untouched future
confirmation data. The final block and execution identity
require maintainer review before freeze.

No cases have been generated for this draft.

## 3. Inspected environment and implementation identity

Python: 3.14.5
NumPy: 2.4.6
Default generator: PCG64
Platform: macOS-27.0.1-arm64-arm-64bit-Mach-O
Reference Git HEAD: e93035809897b10f6895168b51021f76e3fa79c3
METHOD.md Git blob:
6e4247ced1f2eef8b3c9917624d17d46d5bb80aa

Source SHA256:
egrr.py:
a1057838af2384f37029189e74ad59ce1a9d6f5d84b62ece9ae22b482992cd29
covariance_float16.py:
51389fda50ee09034806e6a4b12bb395de14de6ce8e29830ef12d64bbc8d5b6c
storage.py:
1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1
primary_scoring.py:
10adfc9b3b13e58389e513ceab7a5f416dc062a5db9962b7b96c90a587fa3717

These are inspected reference identities, not frozen
execution identities. All hashes must be re-pinned
after any approved implementation changes.

## 4. Proposed parameters and storage

Weights: 64 x 32.
Calibration inputs: 256 x 64.
Evaluation inputs: 1024 x 64.
Quantization: symmetric per-tensor, 3 bits.
Corrected arms: K=128.
Serializer: EGR2 v1, 27-byte header, CRC32.
Store signed dense codes and float16 residual corrections.
Use actual serialized bytes, not modeled_bits(), for reporting.

## 5. Comparison arms

Primary descriptive pair:
- Float16-aware covariance greedy selection
- Largest original-residual magnitude selection

Additional arms:
- Input-RMS sensitivity
- Seeded random selection
- Uncorrected quantization
- Smallest-abs(R) diagnostic, implemented and locally tested

Magnitude ranks abs(R); RMS ranks abs(R)*input_rms.
Covariance uses float16-rounded A for greedy marginal gains.
This is an intentional comparison of distinct selection rules.
Every corrected arm stores and decodes float16 corrections.
A constructed R-versus-A ranking fixture is locally tested.
Ties are resolved by stable flattened index where specified.

Same-byte equality is required for corrected arms.
Runtime, temporary memory and covariance computation
cost are separate resources, not proved equivalent.

## 6. Descriptive outputs

For each of the 100 cases, retain:
- Seed, case ID, dimensions and implementation identity
- Actual serialized bytes per arm
- Successful decoding and integrity status
- Decoded reconstruction and calibration output MSE
- Decoded reconstruction and evaluation output MSE
- Paired r = 1 - MSE_cov / MSE_magnitude, if defined
- Zero and negative improvements
- Negative-gain selection count
- Diagnostic-arm outcomes
- Numerical and implementation failure categories

When all 100 paired ratios are valid:
report the exact finite-set arithmetic mean, minimum,
maximum, distribution and number of nonpositive cases.

If any ratio is undefined, the full 100-case arithmetic
mean is UNDEFINED. Preserve all case records and failures.

If an instrument or integrity gate fails, report
INSTRUMENT_FAILED; never omit or regenerate cases.

Descriptive ratio policy: require finite nonnegative MSEs and
MSE_magnitude > 0. Tiny positive baselines are flagged, not
censored. Undefined/nonfinite ratios remain visible, and any
undefined case makes the full 100-case mean UNDEFINED.
No extra denominator tolerance is adopted in this draft.
The aggregate consistency check compares a reported paired ratio
with the ratio recomputed from its canonical arm MSEs using
`math.isclose(rel_tol=1e-12, abs_tol=1e-15)`. This tolerance is
only a tamper/consistency check; it does not change, censor or
round the authoritative float64 ratio.

## 7. Numbered draft observational predictions

D1: Corrected arms should have equal EGR2 byte counts
under the specified dimensions, bit width and K.
Expected reference-container size: 1311 bytes.
A mismatch is an instrument failure, not hidden.

D2: Valid serialized payloads must decode to exactly
the recorded float16-rounded reconstructions.

D3: Benign structural gate must return GATE: PASS
and exit 0. Corrupted-CRC sabotage must return
GATE: FAIL and a nonzero exit.

D4: All generated cases must receive a visible
record or explicit failure category. No filtering.

D5: Constructed MSE pairs (0.8,1), (1,1), (1.2,1)
must retain improvements +0.2, 0, -0.2 respectively,
within absolute tolerance 1e-12. A planted deletion of
the negative record must produce GATE: FAIL and exit 1.
No positive compression improvement is predicted.

These are proposed observations/instrument expectations,
not a registered population-improvement prediction.

## 8. Outstanding instrumentation

- Optional negative/zero/positive selected-gain diagnostics
  are implemented and locally tested; exactly-K preserved.
- Smallest-abs(R) diagnostic is implemented and locally tested.
- Calibration MSE uses float64:
  mean((X_cal @ (W - W_hat_decoded))**2).
- Evaluation MSE uses float64:
  mean((X_eval @ (W - W_hat_decoded))**2).
- Both use serialized, decoded reconstructions.
- Reject empty/nonfinite inputs and invalid results.
- Report calibration and evaluation failures separately.
- R-versus-A ranking is resolved for this draft:
  magnitude and RMS use original R; covariance uses
  float16-rounded A. Constructed tie fixtures pass.
- Define structured per-case failure and verdict codes.
- Add benign and planted-sabotage cases for each
  applicable guard, including numerical failures.
- Pin source, exact commands, data formats, digests
  and resource definitions before any execution.

## 8A. Planned result format and failure policy

This section specifies a proposed future output contract.
No 100-case result files currently exist.

After explicit authorization, a future instrument should
produce one structured JSON record for every case ID
`"000"` through `"099"`, ordered lexicographically by the exact
three-character string (which is also numeric order for this fixed domain).

Draft schema identifier: `EGRR-DESC-001-DRAFT-1`.
Case IDs are exact three-digit strings (`"000"` through `"099"`);
legacy integer case IDs are not accepted by this envelope.
The failure manifest uses this same lexicographic case-ID order;
entries without a registered case ID follow registered entries.

Each immutable case envelope groups:

- `identity`: study ID, case ID, seed, source commit,
  environment, generator/draw order and per-input hashes;
- `arms`: exactly `covariance`, `magnitude`, `input_rms`,
  `random`, `uncorrected`, and `smallest_residual`, each with
  status/error code, correction metadata, actual serialized byte
  count, payload SHA-256, decode result, and both MSEs;
- `pair`: the named covariance-versus-magnitude comparison,
  status, ratio or null, error code and tiny-denominator warning;
- `case_status` and append-only `errors`: every observed failure
  with case ID supplied by the enclosing record, stage, arm,
  error code and status.

The uncorrected arm has zero corrections. Every corrected arm has
exactly K=128 unique, nonnegative correction indices. Payload
integrity requires actual bytes: a well-formed digest string alone
does not establish byte count or SHA-256 agreement. `decode_ok`
records an instrument result and is not a claim that a separate
decoder independently reproduced reconstruction quality.

Proposed per-case status vocabulary:

VALID: all required operations and values are valid.

UNDEFINED_RATIO: magnitude MSE is zero, or the ratio
or improvement cannot be represented as a finite value.

INVALID_NUMERIC: a required input, reconstruction or MSE
is invalid, negative, nonfinite or encounters a rejected
floating-point arithmetic condition.

SERIALIZATION_ERROR: payload construction, decoding,
checksum, index validation or round-trip integrity fails.

INSTRUMENT_FAILED: a required gate, output-completeness
check or other instrument invariant fails.

All cases must retain their original case IDs. No failed
case may be replaced, skipped or silently regenerated.

If any case has an undefined improvement, the complete
100-case arithmetic mean is reported UNDEFINED. A partial
mean must not be substituted for the full-set statistic.

A structural/instrument failure prevents a passing
instrument verdict, regardless of other measurements.

Future evidence files should include raw per-case records,
a complete failure manifest, exact commands, stdout/stderr,
exit codes, environment details and source identities.

Proposed canonical JSON and digest policy (REVIEW ONLY):

- Output encoding: UTF-8, without BOM.
- JSON key order: lexicographic ascending using sort_keys=True.
- Separators: comma and colon without additional spaces.
- NaN/Infinity JSON literals are prohibited (allow_nan=False).
- Undefined numerical fields use JSON null plus an explicit
  failure category and case ID; never substitute zero.
- Preserve case records ordered lexicographically by the exact
  three-digit string case ID (`"000"` through `"099"`).
- No extra trailing newline in the hashed canonical payload.
- Hash SHA-256 over the exact UTF-8 canonical JSON bytes.
- Encode every authoritative finite float64 as the exact
  big-endian IEEE-754 bit pattern: 16 lowercase hexadecimal
  characters from `struct.pack(">d", value).hex()`.
- Preserve signed zero. Optional decimal previews are
  non-authoritative and must not replace the hexadecimal evidence.
- This stabilizes serialization, not floating-point arithmetic;
  no cross-platform byte-identical result is claimed.

The draft implementation exports each case envelope to this exact
float representation before applying the canonical JSON encoder.

Store the resulting SHA-256 digest alongside raw records,
the software environment, source identities and exact
future execution command. Never invent missing hashes.

This specification is a draft proposal, NOT FROZEN.
No study result file or digest has been produced.

No population p-value, confidence interval or hypothesis
success verdict is part of this descriptive result contract.

## 9. M16 triggered-control assessment — DRAFT

C-FEAS: No — no finite external eligibility pool.
C-NOISE: Yes — floating-point/BLAS reproducibility may
  vary. A constructed covariance fixture was evaluated three
  times on one macOS ARM64 environment. All three returned
  indices (1,2), 41 serialized bytes, MSE 0.029296875,
  and SHA256 prefix 29da0954767ac6f5.
  Observed within-fixture spread: zero.
  Cross-platform reproducibility remains unverified.
C-STAT: No population estimation or inferential verdict
  is proposed. The 100 named cases form the descriptive
  target itself; no p-value, confidence claim or alpha
  decision is authorized. Reassess if inference is added.
C-EVID: No — evidence quality is not the outcome.
C-INDEP: No independent replication is claimed.
C-EXT: Yes — external prior art and reviews used.
C-DEVICE: No — this study makes no device-performance
  comparison or platform advantage claim. The macOS ARM64
  runtime is recorded for reproducibility only. Reassess
  if files move between machines or device claims arise.
C-BUILD: Yes — instrument returns fail-closed verdicts.
C-EXPLORE: Yes — prior exploratory work informed design.
C-METHCOMP: Yes — methods are compared. The referenced
  methodology-comparison experiment is specific to its own
  separate study, not a reusable generic procedure. This
  study requires its own W2 registration and controls.

All unresolved triggers must be resolved before freeze.
The canonical methodology is unchanged.

## 10. Provenance and prior research

Original investigator: sunny-kavixo.
AI assistance: OpenAI ChatGPT GPT-6, drafting/design.
Human review: investigator output checks and maintainer
direction-level review, not independent reproduction.

Preserve prior v0.4/v0.5 history, F-003 exploration,
unverified historical identities and negative findings.
Do not retrospectively describe exploratory outcomes
as held-out confirmation.

## 11. Freeze-and-run authorization gate

1. Submit this standalone DRAFT for review.
2. Resolve all open selector, failure and control rules.
3. Commit a separate freeze-ready registration.
4. Await explicit subsequent maintainer authorization.
5. Only then consider running the fixed study.

No descriptive 100-seed run or confirmatory P1 run
is authorized by the current review.

## 12. Next unrun checkpoint

Review the proposed descriptive case matrix and the
remaining control and instrumentation validation before
any research cases are generated.

Status remains DESIGN ONLY / NOT RUN.
