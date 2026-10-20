# EGRR constructed engineering qualification — frozen local specification

**Scope:** engineering fixtures only. EGRR-DESC-001 is DRAFT / NOT FROZEN / NOT RUN; population P1 is UNRESOLVED / NOT APPROVED. This document is frozen by its SHA-256 before any qualification command is executed. No registration or research-study execution is implied.

## Identity and sources

- Contributor fork branch at inspection: `research/egrr-desc-001-draft`; full HEAD `c9517b61f3652938bb79c0dc60d89b0dbe86490c`. Work occurs on local isolated branch `local/egrr-qualification-20261020` from that commit.
- Runtime inspected: Python 3.14.5, NumPy 2.4.6, macOS arm64 (record complete output at execution).
- Normative source SHA-256: `METHOD.md` `10dbfdf1286bee932dc83e3fb40998a4f8db74fcbe2bde54acd4ff02cb78b365`; `WORKFLOW.md` `92703c31492680fc67a98d66eab2c883ec23e6d25a1177e3d87faf2e5b3afeb6`; `CONTROLS.md` `66acda3ba8c547f6d80f164da6c099228320772e33da20b0790cb93473dba716`.
- Instrument SHA-256 at inspection: `covariance_float16.py` `623fac46c82edff9373e4f17f17e4809b5fcc47daf1a0c9bb5ac7af2bae707e4`; `egrr.py` `a73f6b6d8e970995cf2c89d6f6c417d11a27e8776a7a42acbdf121b1dd17e756`; `storage.py` `1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1`; `verified_aggregate.py` `3384fe449c3482b1e86af321674c8ac119714e0cdaf1f95246a013eadbacb69b`.

## Fixture COV-LOCAL-001: covariance path

Use literal float64 arrays only, no RNG or study seeds:

`W = [[0.25,-0.75,1.50,-1.00],[0.50,1.00,-0.25,-1.50]]`; `X_cal = [[1,0],[0,1],[1,1],[-1,2]]`; `X_eval = [[2,-1],[1,2],[-2,1]]`; `bits=3`, `K=2`. This 2×4 fixture is outside both reserved seed blocks `380000–380099` and `280000–280099` because it uses no seed.

Command from repository root: `python3 experiments/egrr_issue28/qualification_covariance_gate.py --case benign`; run as three independent processes, capturing complete stdout, stderr and exit code for each. Negative commands: same path with `--case drift`, `--case corrupt`, and `--case malformed`. The script imports real `quantize_symmetric`, `select_covariance_float16`, `serialize`, `deserialize`, `reconstruct`, and `heldout_mse`. It must perform actual candidate selection; serialize the selected corrections; decode; score decoded reconstruction on both `X_cal` and `X_eval`; and emit a canonical one-line JSON record with selected indices, selected gain diagnostics, decoded payload SHA-256, calibration/evaluation MSE and input hashes.

**Success:** exit 0, empty stderr, `status=PASS`; exactly two selected and decoded indices; decoded quantized values equal original; decoded corrections equal float16-round-tripped selected values exactly; finite nonnegative scores; independent explicit float64 scoring formula agrees with `heldout_mse` at `rel_tol=1e-12`, `abs_tol=1e-15`. Three benign stdout byte streams must be identical and their SHA-256 equal, with all three exit codes 0. Exact same-process equality is required because fixed arrays and deterministic code are used; cross-platform bit identity is not claimed. The observed SHA-256 and values are recorded only after execution, not prewritten as expected research results.

**Failure:** `drift` changes the evaluation input after the frozen literal fixture is identified and must exit 1 with `FIXTURE_INPUT_DRIFT`; `corrupt` flips a serialized byte and must exit 1 with `CRC32 checksum mismatch`; `malformed` supplies invalid calibration shape and must exit 1 with `invalid calibration shape`. Each failure emits one JSON record with `status=FAIL`, case, reason, and evidence; stderr is empty unless an unexpected exception occurs. Any skipped decoder/selection/scoring, missing raw stream, numerical mismatch, nondeterministic benign output, wrong exit/reason, or exception is FAIL or BLOCKED with preserved evidence.

## Fixture EGR2-PROV-LOCAL-001: decoder provenance

Use the same literal `W`, 3-bit quantizer, exactly two literal correction indices `[1,6]` and values `[0.1,-0.3333]`. These are constructed engineering bytes, not scientific observations. The local verifier imports the real `storage.deserialize` and checks the decoded shape, indices, float16-rounded values, actual bytes/hash, and reconstruction. Its verdict must be derived from decoding, never `decode_ok` metadata alone.

Command from repository root: `python3 experiments/egrr_issue28/qualification_decoder_gate.py --case CASE` for CASE in `benign`, `corrupt`, `non-egr2`, `forged`, and `aggregate-bypass`. Capture raw stdout/stderr/exit for each. The benign case provides genuine `serialize` output and truthful metadata; expect exit 0, `status=ACCEPTED`, `reason=EGR2_DECODE_VERIFIED`. `corrupt` flips a payload byte without refreshing CRC; expect exit 1, `status=REJECTED`, `reason=CRC32 checksum mismatch`. `non-egr2` supplies same-length non-EGR2 bytes; expect exit 1 and a decoder rejection reason. `forged` supplies non-EGR2 bytes plus recomputed plausible length/SHA metadata and `decode_ok=true`; expect exit 1, `status=REJECTED`, `reason` rooted in actual decoder rejection. The `aggregate-bypass` diagnostic must call the existing `verified_aggregate` on its existing constructed 100-record stand-ins and report that it accepts forged `decode_ok=true` with non-EGR2 payloads if observed. This diagnostic is an expected **limitation**, not a successful trusted-path result; it must exit 0 only when it detects and explicitly labels the bypass, otherwise exit 1 with a changed-behavior reason. It must not generate reserved scientific seeds.

The isolated decoder verifier is a proposed boundary for later review, not a change to canonical `verified_aggregate.py` and not an independent decoder. Valid bytes accepted by the isolated verifier show only that this narrow trusted path calls the real decoder. Existing aggregator acceptance of self-reported stand-ins, if observed, remains an unresolved entrypoint limitation.

## Evidence, verdicts, and regression scope

Raw run evidence goes in `qualification_evidence/` outside the Git checkout, one `.stdout`, `.stderr`, `.exit` per command plus SHA-256 manifest. Record `python3 --version`, NumPy version, platform, complete source and artifact hashes. Run only the minimal existing tests `test_egr2_integration.py`, `test_verified_aggregate.py`, `test_covariance_safety.py`, `test_gain_diagnostics.py`, `test_matched_bytes.py`, plus new local gate tests if added. Do not run the 111-test or Android suite without a new concrete reason.

- **PASS, covariance:** all three true benign runs and all three negatives meet the frozen contract.
- **PASS, decoder qualified boundary:** benign actual decode accepted; corrupted, non-EGR2 and forged bytes rejected by actual decode with reasons/evidence. Report `verified_aggregate` bypass separately as a limitation; the *canonical aggregation entrypoint* is not qualified until a mandatory decoder-attestation boundary is approved and enforced.
- **FAIL:** any contract predicate contradicted by observed execution, with raw evidence retained.
- **BLOCKED:** source/runtime unavailable, test not executed, or incomplete evidence; never convert to PASS.

AI assistance: OpenAI Codex drafted this local engineering fixture/specification; human review of resulting source and outputs is pending. Putluru Sandeep is the documented originating EGRR investigator; Chad Holland retains PA maintainer authority.
