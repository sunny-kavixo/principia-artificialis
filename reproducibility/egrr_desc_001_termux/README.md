# EGRR-DESC-001 constructed verification package

Status: constructed instrumentation verification only. This package does not
generate or evaluate seeds `380000`–`380099` or `280000`–`280099`, and it does
not execute either scientific study.

## Separated identities

Normative candidate instrument commit:
`29c63fe399fa1cbc45974717b8de14a1cd989401`.

Verification-package base commit:
`4fd0e25416673e7d75f9dd61f9fe396e043e4fe4`. The corrected wrapper and
its two bounded fixtures are a pending draft revision on top of that commit;
their exact per-file hashes are recorded by every run until a reviewed package
commit exists. The wrapper does not require checkout HEAD to equal the older
instrument commit. It verifies the normative implementation files themselves
before executing any check.

Normative instrument source SHA-256:

```text
c5de9fb5b42b6d6fd103f75b0020bd82195e6f667bf788b9b7237f5a463e9ceb  experiments/egrr_issue28/canonical_evidence.py
bcb4c5289c75a571446a90a35cc021129a49b7d241ece51a5caae2582526fbd5  experiments/egrr_issue28/case_envelope.py
623fac46c82edff9373e4f17f17e4809b5fcc47daf1a0c9bb5ac7af2bae707e4  experiments/egrr_issue28/covariance_float16.py
522168fb522e40dbe00e5f4659fd5022c123122c5f74b1d02f8ae39a67f5f189  experiments/egrr_issue28/descriptive_case_record.py
79b1140dfeb1c0ad717ca3de735a3986285dc0c3b56704211369c83861abae04  experiments/egrr_issue28/descriptive_scoring.py
a73f6b6d8e970995cf2c89d6f6c417d11a27e8776a7a42acbdf121b1dd17e756  experiments/egrr_issue28/egrr.py
c1fa507ab1ec4b7e493ed5e388bdf31a9bc8a235e8ca5aaaab082ddb36f44097  experiments/egrr_issue28/packing.py
1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1  experiments/egrr_issue28/storage.py
3384fe449c3482b1e86af321674c8ac119714e0cdaf1f95246a013eadbacb69b  experiments/egrr_issue28/verified_aggregate.py
```

## Minimal environment

- Android Termux
- Python 3.14.6 (the requested confirmation environment)
- Git
- `numpy==2.4.4`
- `pytest==9.1.1`

From a clean checkout of the future commit containing this corrected package:

```sh
python -m pip install -r reproducibility/egrr_desc_001_termux/requirements-termux.txt
python reproducibility/egrr_desc_001_termux/termux_verify.py
printf 'verification_exit=%s\n' "$?"
```

The verifier refuses normative source-identity drift before executing tests.
It records checkout/package identities separately, executes constructed-only
checks, and writes raw stdout/stderr files under
`reproducibility/egrr_desc_001_termux/raw/` plus the structured summary
`termux-verification.json`. Use `--output-dir` to keep an evidence run outside
the checkout.

Expected individual exit codes:

| Check | Expected exit |
|---|---:|
| sabotage-oracle control: unrelated exit 1 is rejected | 0 |
| malformed registration (`expected_seeds=None` included) | 0 |
| full EGRR regression suite (111 tests) | 0 |
| all four real EGR2 integration tests | 0 |
| registered 64×32, K=128, 1,311-byte fixture | 0 |
| registered fixture planted CRC sabotage, exact message | 1 |
| positive/zero/negative reporting gate | 0 |
| planted reporting deletion, exact message | 1 |
| same-input noise probe, three repeats | 0 each; exact stdout equal |

The package command exits `0` only when all normative source hashes match and
every exit/message condition passes. In particular, exit 1 alone cannot satisfy
CRC sabotage: stdout must equal the registered CRC-failure message and stderr
must be empty. Its stdout is one JSON object with schema
`EGRR-DESC-001-VERIFY-2`. The same bytes are retained as
`termux_verify.stdout.txt`; expected wrapper stderr is retained as an empty
`termux_verify.stderr.txt`.

The 64×32 fixture uses constructed seed 901 and the C-NOISE probe uses
constructed seed 902. Neither belongs to a reserved research range. Three
same-process repeats must be byte-identical. This is a within-environment
repeatability observation, not cross-platform numerical equivalence.

## macOS versus Android evidence

A run on macOS must be labelled macOS. It may establish that the package and
source-identity boundary work in a clean macOS checkout; it is not Android
evidence. Android C-DEVICE evidence requires a fresh Android run with the JSON,
raw output, versions, platform and transfer hashes retained. After transferring
an evidence directory, run `md5sum` on Android and `md5` on macOS and retain the
manifests; matching file lists and MD5 values are the required transfer check.

## Attributed external verification

Chad Holland independently reported targeted verification at the pinned commit
on Android Termux with Python 3.14.6 and NumPy 2.4.4: seven targeted tests
passed in 1.901 seconds with process exit 0. He reported matching SHA-256
identities for `verified_aggregate.py` and `test_egr2_integration.py`, successful
constructed EGR2 serializer/repository-decoder checks, and the malformed-
registration defect as corrected. Review record:
https://github.com/sunny-kavixo/principia-artificialis/pull/1#pullrequestreview-5546391205

That report predates this corrected wrapper and does not state that it produced
`termux-verification.json` and raw stdout/stderr files. It also does not use an
independently implemented decoder or validate the scientific hypothesis. Those
limits must remain explicit when citing the Android result.
