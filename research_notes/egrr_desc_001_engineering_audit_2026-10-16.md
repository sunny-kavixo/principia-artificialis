# EGRR-DESC-001 bounded engineering audit — 2026-10-16

## Scope and safety boundary

This audit covers fail-closed registration validation, constructed EGR2
serializer/decoder integration, Section 8A ordering, and existing D1–D5/M16
instrument safeguards. It does not execute either scientific study, generate
or evaluate seeds 380000–380099 or 280000–280099, alter historical
population-P1 evidence, freeze W2, or make scientific-performance claims.
`whitepapers/VOLUME_I_FOUNDATIONS.md` had pre-existing working-tree changes
and was not edited, restored, staged, or committed during this work.

Starting revision: `f96cb12bd9f8f95c007abd73b52c4b6435c97289`.

## Root cause and correction

`verified_aggregate` correctly classified a non-dictionary `expected_seeds`
as an invalid fixed registration, but continued into record verification and
evaluated membership against the original value. For `None`, Python raised
an unhandled `TypeError` before a structured result could be returned.

Registration values are now type-checked and normalized before membership,
indexing, aggregation, or manifest sorting. Invalid seed registrations use an
empty internal mapping only for safe exhaustive verification; they never
become valid. Non-string or unhashable case identifiers are reported without
using them as dictionary/set keys. Failures returned by the lower aggregation
layer are normalized before final sorting. Valid case identities retain the
fixed lexicographic `"000"`–`"099"` order.

Regression coverage includes `None`, strings, invalid mappings, missing and
extra seed keys, invalid seed values, non-string case IDs, malformed records,
invalid top-level containers, mismatched seed identities, and ordering of
multiple identity mismatches. Independently observable failures remain in the
manifest; invalid inputs do not produce an aggregate or manufactured validity.

## EGR2 constructed integration coverage

`test_egr2_integration.py` calls the repository's real `storage.serialize`
and `storage.deserialize` functions on small, fixed arrays. It covers:

- corrected and uncorrected representations;
- exact byte counts (42 and 34 bytes for the two small fixtures);
- pinned payload SHA-256 values;
- float16 residual rounding and reconstructed-array equality;
- CRC corruption;
- forged incorrect K with a recomputed CRC;
- duplicate and out-of-range indices with recomputed CRCs; and
- quantized-weight and correction shape errors.

This demonstrates execution of the repository decoder. It is not an
independent decoder implementation or an independent scientific replication.

Pinned constructed payload identities:

- uncorrected: `125e4edc06c33d87f87ae7956e13bf397c2916dc533a1f9380a0f052e059ee1a`
- corrected: `99c775222e3da23ac8a29d5a31a0a079b7c113aa7d46e22f08c2106b67320aec`

## Exact verification evidence

Environment:

```text
Python 3.14.5
numpy 2.4.6
pytest 9.1.1
macOS-27.0.1-arm64-arm-64bit-Mach-O
```

Targeted new regressions:

```text
command: python3 -m pytest -q test_verified_aggregate.py::VerifiedAggregateTests::test_invalid_registration_inputs_fail_closed test_verified_aggregate.py::VerifiedAggregateTests::test_invalid_top_level_containers_fail_closed test_verified_aggregate.py::VerifiedAggregateTests::test_malformed_records_and_non_string_ids_fail_closed test_egr2_integration.py
working directory: experiments/egrr_issue28
expected exit: 0
actual exit: 0
stdout:
.......                                           [100%]
7 passed, 23 subtests passed in 2.94s
stderr: empty
```

Full repository regression suite:

```text
command: python3 -m pytest -q
working directory: repository root
expected exit: 0
actual exit: 0
stdout:
..................................................................................... [ 53%]
...........................................................................                      [100%]
160 passed, 107 subtests passed in 7.20s
stderr: empty
```

Structural benign gate:

```text
command: python3 structural_gate.py
working directory: experiments/egrr_issue28
expected exit: 0
actual exit: 0
stdout: GATE: PASS — benign payload
stderr: empty
```

Structural CRC sabotage:

```text
command: python3 structural_gate.py --sabotage
working directory: experiments/egrr_issue28
expected exit: 1
actual exit: 1
stdout: GATE: FAIL — planted corruption detected
stderr: empty
```

Reporting benign gate:

```text
command: python3 descriptive_reporting_gate.py
working directory: experiments/egrr_issue28
expected exit: 0
actual exit: 0
stdout: GATE: PASS — all positive/zero/negative cases retained
stderr: empty
```

Reporting deletion sabotage:

```text
command: python3 descriptive_reporting_gate.py --sabotage
working directory: experiments/egrr_issue28
expected exit: 1
actual exit: 1
stdout: GATE: FAIL — reporting completeness failure
stderr: empty
```

Changed-file whitespace check:

```text
command: git diff --check -- docs/EGRR-DESC-001_DRAFT.md experiments/egrr_issue28/verified_aggregate.py experiments/egrr_issue28/test_verified_aggregate.py experiments/egrr_issue28/test_egr2_integration.py
expected exit: 0
actual exit: 0
stdout: empty
stderr: empty
```

## Source identities

```text
3384fe449c3482b1e86af321674c8ac119714e0cdaf1f95246a013eadbacb69b  experiments/egrr_issue28/verified_aggregate.py
8f46b13e9ced0e354b954781fc7321fc97c0a49c2874c39a183cb79029491f03  experiments/egrr_issue28/test_verified_aggregate.py
5f8fad442bd2c144358bba6001cb9fc7ff505608209e71c707cfeaed61100987  experiments/egrr_issue28/test_egr2_integration.py
1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1  experiments/egrr_issue28/storage.py
91a6c871fd01616e9e8e6363de5207f4d9d35fccba09933377011fb59d90c440  experiments/egrr_issue28/structural_gate.py
5492a13d6ddb75e73e95f83c7e848174797d43af27ce5bf703b4e436c6c1a526  experiments/egrr_issue28/descriptive_reporting_gate.py
48e4f8f45a297d07cb8b814fcfc7b542784e8a964d537b7032e4e11bb045ee43  docs/EGRR-DESC-001_DRAFT.md
```

## D1–D5 and M16 safeguard assessment

- D1: verified by existing 1311-byte equal-size coverage and the new exact
  byte-count checks on small corrected/uncorrected fixtures.
- D2: verified for constructed fixtures by actual serializer and decoder
  execution, including exact float16-rounded reconstruction. This is not an
  independent decoder.
- D3: benign gate exited 0; planted CRC corruption exited 1 with the registered
  fail verdict.
- D4: registration/container/malformed-record regressions demonstrate visible
  structured failures and no survivor-only aggregate. Scientific case
  generation was not run.
- D5: benign positive/zero/negative reporting gate exited 0; deletion sabotage
  exited 1.
- M16 C-BUILD: supported by fail-closed regressions and both sabotage gates.
  C-NOISE cross-platform evidence remains incomplete. C-EXT, C-EXPLORE, and
  C-METHCOMP remain governance triggers described by the draft, not resolved by
  these engineering tests. No independent replication is claimed.

## Remaining gaps and risks

- Chad Holland's Python 3.14.6 Android Termux reproduction was not rerun here;
  local verification used Python 3.14.5 on macOS ARM64.
- The EGR2 checks exercise the repository's serializer and decoder, so they do
  not establish independent decoding or cross-implementation compatibility.
- CRC32 detects accidental corruption but is not an authenticity mechanism.
- No authorized study outputs exist, and no scientific or population-level
  conclusion follows from these constructed tests.
- W2 remains unfrozen and unresolved M16 controls remain open as documented.

## Next checkpoint

Have a maintainer review the fail-closed contract and run the targeted command
unchanged on Python 3.14.6 Android Termux, recording its exact environment,
exit code, stdout/stderr, and source identities before any freeze discussion.
