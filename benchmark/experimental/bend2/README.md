# Bend 2 controller experiment

This is an incomplete, offline port of the attempt-sequence decision logic and Docker create argument construction from
`benchmark/run.py`. It does not launch attempts, manage Docker sandboxes, access
providers, collect artifacts, render, or score. It must not be used for a real
campaign. Python remains the authoritative controller.

The experiment checks first-success versus independent-repetition decisions, compares
synthetic sandbox create arguments with Python, and checks
the three account/provider failures that leave later slots reserved. Validate
with Bend 2 and compare its output to `expected.txt`:

```sh
bend benchmark/experimental/bend2/sequence.bend > /tmp/keygen-bend2-sequence.txt
diff -u benchmark/experimental/bend2/expected.txt /tmp/keygen-bend2-sequence.txt
```

The current Bend 2 `Process.run` timeout does not kill descendants, and the JS
backend blocks during child execution. Neither behavior is equivalent to the
existing controller without additional work. Do not replace the production
sandbox or make performance claims based on this experiment.

Compare Docker create arguments with the current Python controller without starting
Docker (the arguments after `test_parity.py` invoke the Bend compiler):

```sh
python benchmark/experimental/bend2/test_parity.py bend
```

The compiler tested for this experiment was Bend 2.0.40 from
`bendlang/bend` revision `d18110b6d6e9a70bb8814b2a8d8db092e301e540`.
No Docker daemon or provider inference was exercised.
