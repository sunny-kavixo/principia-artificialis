# EGRR-DESC-001 Android Termux verification package

Status: constructed instrumentation verification only. This package does not
generate or evaluate seeds `380000`–`380099` or `280000`–`280099`, and it does
not execute either scientific study.

## Pinned identity

Commit:
`29c63fe399fa1cbc45974717b8de14a1cd989401`

Source SHA-256:

```text
3384fe449c3482b1e86af321674c8ac119714e0cdaf1f95246a013eadbacb69b  experiments/egrr_issue28/verified_aggregate.py
8f46b13e9ced0e354b954781fc7321fc97c0a49c2874c39a183cb79029491f03  experiments/egrr_issue28/test_verified_aggregate.py
5f8fad442bd2c144358bba6001cb9fc7ff505608209e71c707cfeaed61100987  experiments/egrr_issue28/test_egr2_integration.py
1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1  experiments/egrr_issue28/storage.py
```

## Minimal environment

- Android Termux
- Python 3.14.6 (the requested confirmation environment)
- Git
- `numpy==2.4.4`
- `pytest==9.1.1`

From a clean checkout of the pinned commit:

```sh
python -m pip install -r reproducibility/egrr_desc_001_termux/requirements-termux.txt
python reproducibility/egrr_desc_001_termux/termux_verify.py
printf 'verification_exit=%s\n' "$?"
```

The verifier refuses source-identity drift. It executes four constructed-only
checks and writes raw stdout/stderr files under
`reproducibility/egrr_desc_001_termux/raw/` plus the structured summary
`termux-verification.json`.

Expected individual exit codes:

| Check | Expected exit |
|---|---:|
| malformed registration (`expected_seeds=None` included) | 0 |
| benign real EGR2 corrected/uncorrected round trip | 0 |
| benign structural gate | 0 |
| planted CRC sabotage gate | 1 |

The package command itself exits `0` only when the Git/source identities match
and every individual check returns its expected code. Its stdout is one JSON
object with schema `EGRR-DESC-001-TERMUX-VERIFY-1`; stderr is empty unless the
runtime itself reports an error.

## Attributed external verification

Chad Holland independently reported targeted verification at the pinned commit
on Android Termux with Python 3.14.6 and NumPy 2.4.4: seven targeted tests
passed in 1.901 seconds with process exit 0. He reported matching SHA-256
identities for `verified_aggregate.py` and `test_egr2_integration.py`, successful
constructed EGR2 serializer/repository-decoder checks, and the malformed-
registration defect as corrected. Review record:
https://github.com/sunny-kavixo/principia-artificialis/pull/1#pullrequestreview-5546391205

That report does not state that this wrapper command produced or returned its
`termux-verification.json` and raw stdout/stderr files. It also does not use an
independently implemented decoder or validate the scientific hypothesis. Those
limits must remain explicit when citing the Android result.
