# EGRR-DESC-001 corrected-wrapper macOS qualification — 2026-10-17

Status: self-tested constructed instrumentation evidence only.
Not Android evidence. Not post-freeze confirmation. No study seed was used.

The candidate package was copied into an isolated sparse clone of branch
`research/egrr-desc-001-draft` and committed there only so the wrapper could be
tested with a genuinely clean checkout. Temporary local verification commit:
`98bb6dacb5ba0b0710ec304309594553ac840a10`. It was not created on the working
branch and was not pushed.

Command executed from the clean clone:

```text
python3 reproducibility/egrr_desc_001_termux/termux_verify.py \
  --output-dir /Users/sunny/Downloads/principia-egrr-protocol/reproducibility/egrr_desc_001_termux/evidence/macos-2026-10-17
```

Observed wrapper process exit: `0`.

Recorded environment:

- macOS 27.0.1, ARM64
- Python 3.14.5
- NumPy 2.4.6
- pytest 9.1.1
- `checkout_clean=true`
- normative instrument source identity: matched

Recorded checks:

| Check | Actual exit | Result |
|---|---:|---|
| sabotage oracle rejects unrelated exception | 0 | condition met |
| malformed registration fail-closed regression | 0 | condition met |
| full EGRR regression suite, 111 tests | 0 | condition met |
| four real EGR2 integration tests | 0 | condition met |
| registered 64×32/K=128 benign fixture | 0 | condition met |
| planted CRC corruption with exact message | 1 | condition met |
| positive/zero/negative reporting gate | 0 | condition met |
| planted reporting deletion with exact message | 1 | condition met |
| C-NOISE repeat 1 | 0 | condition met |
| C-NOISE repeat 2 | 0 | condition met |
| C-NOISE repeat 3 | 0 | condition met |
| exact equality of all three repeat outputs | 0 | no variation observed |

All three C-NOISE stdout files have SHA-256
`7f06becf77c6daeb806ec2833f6123e9c777e407f1cac1e089fc664fae901afc`.

Top-level evidence SHA-256:

```text
22591c0951fed15fa3f6350aeff7dae3171d7d247df9d56f68a35484a7617a90  termux-verification.json
b45e07058d1b5796f0927c5d249041fbfa9d3c41e574b3baef0d00dd77c02896  termux_verify.stdout.txt
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  termux_verify.stderr.txt
```

The JSON contains every individual command, expected and actual exit,
stdout/stderr path and digest, platform/version field, package-file digest and
normative source digest. Raw files are retained under `raw/`.

Limit: no corrected-wrapper Android Termux run or device-transfer MD5 manifest
was produced. Chad Holland's earlier Android report covers seven targeted tests
at instrument commit `29c63fe`, not this wrapper invocation.
