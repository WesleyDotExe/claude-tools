# secure-random

An MCP server that generates randomness by drawing from the OS's
cryptographically-secure RNG instead of asking a language model to imagine
an output. This is a real, well-documented gap: models predict the next
token from learned patterns, not by sampling a distribution, so "pick a
random number" comes back skewed toward whatever value is most common in
training data.

## What it solves

- **The "27 phenomenon".** Asked for "a random number between 1 and 50",
  several widely-used assistants (independently, across different vendors)
  all answered 27 — the value is disproportionately represented in training
  data, so it's the most *predictable* answer, not a random one. The same
  bias shows up in dice rolls, coin flips, shuffled lists, and "randomly"
  picked items.
- **Secrets that need to actually be unpredictable.** A password or token a
  model writes out in text is not drawn from real entropy and shouldn't be
  trusted as one; `generate_password`/`generate_token`/`generate_uuid4` here
  are.
- **The claim of unbiasedness needs to be checkable, not asserted.**
  `verify_uniformity` runs real draws from a range through an exact
  chi-square goodness-of-fit test and returns a p-value, so "this tool isn't
  biased toward 27" is something you can verify per range and sample size
  instead of taking on faith.

Every generator here is backed by Python's `secrets` module (CSPRNG, from
the OS entropy source) — never `random`'s default Mersenne Twister, and
never the model's own guess.

## Files

- `randkit.py` — the actual logic: dice, integers, floats, coin flips,
  Fisher-Yates shuffling, sampling, password/token/UUID generation, and a
  chi-square uniformity test with its own hand-rolled regularized
  incomplete-gamma implementation (no `scipy` dependency). Stdlib only
  (`secrets`, `uuid`, `string`, `math`, `re`). Usable standalone.
- `server.py` — a thin MCP server (stdio transport) wrapping `randkit.py`'s
  functions as tools. Requires the `mcp` package (see below).
- `tests/test_randkit.py` — 34 unit tests, including the chi-square
  implementation checked against textbook critical values, and a synthetic
  "one bucket takes 90% of the draws" histogram confirming the test actually
  *catches* bias rather than just passing real randomness.
- `proof/run_2026-09-14.txt` — the full test run plus a live MCP client
  session over stdio: `list_tools` and ten real tool calls, including
  `verify_uniformity` run on the exact "1 to 50" range from the documented
  bias, coming back uniform (p ≈ 0.3, nowhere close to flagging 27 or any
  other value as a favorite).

## Try it without MCP

```
python3 -c "
import randkit
print(randkit.roll_dice('2d6+3'))
print(randkit.verify_uniformity(1, 50, samples=20000))
"
```

## Run the tests

```
python3 -m unittest discover -s tests -v
```

## Run as an MCP server

```
pip install -r requirements.txt
python3 server.py
```

Point an MCP client at it, e.g. in Claude Desktop/Code's MCP config:

```json
{
  "mcpServers": {
    "secure-random": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/secure-random/server.py"]
    }
  }
}
```

## Tools exposed

| Tool | Purpose |
|---|---|
| `roll_dice` | Roll dice in standard notation (`2d6+3`, `d20`, ...). |
| `random_integers` | `count` uniform CSPRNG integers in an inclusive range. |
| `random_floats` | `count` uniform CSPRNG floats in `[low, high)`. |
| `flip_coins` | Flip `count` fair coins. |
| `shuffle_list` | CSPRNG Fisher-Yates shuffle of a list. |
| `pick_random` | Pick `count` items from a list, with or without replacement. |
| `generate_password` | A CSPRNG password guaranteeing every enabled character class, with its entropy in bits. |
| `generate_token` | A CSPRNG token (`hex`/`urlsafe`) for API keys, session IDs, etc. |
| `generate_uuid4` | A random (version 4) UUID. |
| `verify_uniformity` | Chi-square-test `samples` draws from a range and report a p-value — proof the output isn't biased. |

## What it doesn't do

No weighted/biased sampling by design (every draw is uniform unless you're
supplying already-weighted items to `pick_random` yourself), no seeding for
reproducibility (the whole point is CSPRNG output, which is deliberately
not reproducible), and `verify_uniformity` is capped at 2,000,000 samples
and requires at least 5 samples per bucket for the chi-square test to be
statistically meaningful — it will raise rather than return a misleading
result for undersized inputs.
