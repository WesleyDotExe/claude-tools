# discrete-probability

An MCP server for exact discrete-probability calculations — the birthday
paradox, dice-sum distributions, drawing without replacement, binomial
trials, Bayes' theorem, and a generalized Monty Hall problem — plus
statistically rigorous comparison of two observed proportions (e.g. two win
rates), instead of asking a language model to reason a probability word
problem, or eyeball a rate gap, out in its head.

## What it solves

Language models are well-documented to be unreliable at discrete
probability, and specifically *worse* on the "counterintuitive" cases: a
2026 study on counterintuitive discrete-probability problems
([arxiv.org/pdf/2606.07516](https://arxiv.org/pdf/2606.07516)) found models
average 0.96 accuracy on standard problems but only 0.59 on counterintuitive
ones, and the widely-discussed
["LLMs Can't Do Probability"](https://brainsteam.co.uk/2024/05/01/llms-cant-do-probability/)
writeup documents the same failure informally. The birthday paradox and the
Monty Hall problem are the canonical examples of this: both have a single
correct answer that both humans and models reliably get wrong by intuiting
it instead of calculating it.

Existing calculator-style MCP servers expose raw combinatorics primitives
(`nCr`, `nPr`, factorial) but not these pre-composed, word-problem-shaped
scenarios — and none found combine them with a built-in Monte Carlo
cross-check. Every function here:

1. Returns an **exact** answer, computed with `fractions.Fraction` (not
   floating-point rounding) wherever the inputs are exact.
2. Optionally (`verify=true`) **proves** that answer by actually playing the
   scenario out `verify_trials` times using CSPRNG draws (`secrets`, the
   same randomness source [`tools/secure-random`](../secure-random) uses —
   this tool builds on that one's pattern rather than re-deciding how to
   draw unbiased randomness), and reports whether the empirical frequency
   falls inside a 95% Wilson confidence interval around the exact answer.
   That turns "the exact answer is 2/3" from an assertion into something
   you can watch play out.

## Tools exposed

| Tool | Purpose |
|---|---|
| `birthday_collision` | Exact probability that ≥2 of `n` items drawn from `categories` possible values collide (the birthday paradox, generalized past 365 days). |
| `dice_sum_distribution` | Exact probability distribution over the sum of `num_dice` fair `sides`-sided dice, or the probability of a specific sum/range. |
| `hypergeometric_probability` | Exact probability of `k` successes drawn without replacement (cards, defective-parts sampling, urn problems). |
| `binomial_probability` | Probability of `k` successes in `n` independent trials — exact if `prob_success` is a fraction string (e.g. `'1/6'`), otherwise float. |
| `bayes_update` | Exact posterior `P(H\|E)` via Bayes' theorem given a prior and two likelihoods — the general mechanism behind Monty-Hall-style "the intuitive answer is wrong" problems once reduced to explicit probabilities. |
| `monty_hall` | Exact win probability for staying vs. switching in a generalized Monty Hall problem (any door/car/reveal count), not just the classic 3-door case. |
| `compare_two_proportions` | Is the gap between two observed proportions (e.g. two win rates, two conversion rates) statistically significant, or plausibly noise? A two-proportion z-test p-value, a Wilson CI per group, a Newcombe CI for the difference, and a plain verdict. |

Every tool accepts `verify: bool = false` and `verify_trials: int = 20000`
(100 to 500,000) to run the Monte Carlo cross-check described above.
`compare_two_proportions`'s `verify` runs a CSPRNG permutation
(label-reshuffling) test instead — see below.

### `compare_two_proportions` in more detail

Built for exactly the "is a 62% vs 55% win-rate gap over 300 games real, or
noise?" question — comparing two observed proportions from finite samples
without hand-rolling the statistics. Given `successes_a`/`trials_a` and
`successes_b`/`trials_b`:

- Each group's own proportion, with a Wilson score confidence interval.
- A **Newcombe (1998) hybrid-score interval** for the *difference* between
  the two proportions — built directly from each side's own Wilson interval
  rather than a naive pooled-standard-error interval, which stays
  well-behaved even when a proportion is near 0% or 100% (the naive version
  can misbehave there).
- A standard pooled-variance **two-proportion z-test** p-value and a plain
  verdict ("statistically significant" / "plausibly noise") at the requested
  `confidence` (default 0.95).
- With `verify=true`: an independent **CSPRNG-backed permutation
  (randomization) test** — pool every outcome from both groups, reshuffle
  which outcomes "belong" to which group `verify_trials` times, and count how
  often a random relabeling produces a gap at least as extreme as the one
  observed. This makes no normal-theory assumption at all, unlike the z-test.
  The two p-values are **not expected to match exactly** even when both are
  correct — the z-test is a large-sample normal approximation, the
  permutation test's empirical value is a Monte Carlo estimate of the exact
  permutation-null p-value — so the response reports whether they *agree on
  the significance call* (`agrees_on_significance_call`), which is what
  matters in practice, rather than asserting numeric equality. (Verified
  during development against a hand-derived exact hypergeometric-tail
  calculation, independent of this tool's own code — see
  `tests/test_probkit.py`'s `_exact_permutation_p_value`.) The permutation
  test's cost scales with `verify_trials * min(trials_a, trials_b)`, capped
  at 10,000,000 (raises instead of running unboundedly long for large
  samples with a large `verify_trials`).

## What it doesn't do

It does not parse a word problem into these parameters — like
[`time-arithmetic`](../time-arithmetic), it computes once the inputs are
already unambiguous ("3 doors, 1 car, the host reveals 1"), not from prose
("I'm on a game show and..."). `dice_sum_distribution` caps `sides **
num_dice` at 10^8 so results stay exact and the output stays a reasonable
size — use `at_least`/`at_most`/`target` instead of the full distribution
for larger dice pools. `binomial_probability`'s exact-fraction path only
applies when `prob_success` is given as an int (0 or 1) or a fraction
string; a plain float like `0.3` is kept as a float on purpose, since it
isn't exactly representable as a "nice" fraction and laundering it into one
would be a false precision claim. `compare_two_proportions` assumes the two
groups are independent (e.g. two separate strategies/cohorts) — it is not
the right tool for paired/matched data (the same subjects measured twice),
which needs McNemar's test instead, not built here.

## Files

- `probkit.py` — the actual logic: exact combinatorics (`fractions.
  Fraction`, `math.comb`), the seven scenario functions above, a
  from-scratch Wilson score confidence interval and inverse-normal-CDF
  (Acklam's rational approximation, no `scipy`), and the CSPRNG-backed
  simulators used by `verify=true`. Stdlib only (`fractions`, `math`,
  `secrets`). Usable standalone.
- `server.py` — a thin MCP server (stdio transport) wrapping `probkit.py`'s
  functions as tools. Requires the `mcp` package (see below).
- `tests/test_probkit.py` — 56 unit tests: known textbook values (birthday-23
  ≈ 50.7%, Monty Hall 1/3 vs 2/3, 2d6-sums-to-7 = 1/6, ≥2 aces in a 5-card
  hand ≈ 4.17%), input validation, `bayes_update` cross-checked against
  `monty_hall`'s independently-derived switch probability (two different
  formulas landing on the same fraction), a "does the check have teeth"
  test proving the confidence-interval logic actually flags a wrong claim,
  not just passes a correct one, `compare_two_proportions`'s z-test checked
  by hand against the standard pooled-variance formula, and its permutation
  test checked against a hand-derived exact hypergeometric-tail calculation
  on a small case (`_exact_permutation_p_value`, independent of `probkit.py`'s
  own code).
- `proof/run_2026-09-24.txt` — the full test run plus a live MCP client
  session over stdio: `list_tools` and `compare_two_proportions` called for
  real (the wishlist's own 186/300-vs-165/300 worked example, both with and
  without `verify=true`; a clear real gap; identical proportions correctly
  called not-significant; an invalid `successes_a > trials_a` input and an
  oversized permutation-test budget both coming back as real MCP tool
  errors), plus `monty_hall` confirmed still working unchanged. See
  `proof/run_2026-09-16.txt` for the original six-tool proof session.

## Try it without MCP

```
python3 -c "
import probkit
print(probkit.birthday_collision(23, 365))
print(probkit.monty_hall(verify=True, verify_trials=20000))
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
    "discrete-probability": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/discrete-probability/server.py"]
    }
  }
}
```
