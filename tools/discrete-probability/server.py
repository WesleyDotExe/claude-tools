"""MCP server exposing probkit's exact discrete-probability functions.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet.
"""
from typing import Any

from mcp.server.mcpserver import MCPServer

import probkit

server = MCPServer(
    name="discrete-probability",
    instructions=(
        "Exact discrete-probability calculations -- birthday-paradox "
        "collisions, dice-sum distributions, drawing without replacement "
        "(cards, defective parts), binomial trials, Bayes' theorem updates, "
        "and the generalized Monty Hall problem. Use these instead of "
        "reasoning a probability word problem out by hand: language models "
        "are well-documented to do fine on standard probability questions "
        "but drop sharply on 'counterintuitive' ones (a 2026 study found "
        "0.96 vs 0.59 accuracy) -- these are exactly that class of problem. "
        "Every tool returns an exact fraction, and passing verify=true runs "
        "a real CSPRNG-backed Monte Carlo simulation of the scenario and "
        "reports whether the exact answer falls inside the simulation's "
        "95% confidence interval, so the answer is checkable, not just "
        "asserted."
    ),
)


@server.tool()
def birthday_collision(n: int, categories: int = 365, verify: bool = False, verify_trials: int = 20000) -> dict:
    """Exact probability that >=2 of `n` items drawn uniformly (with replacement)
    from `categories` possible values collide -- the birthday paradox, generalized
    beyond 365 days (e.g. n=23, categories=365 gives the classic ~50.7%).
    """
    return probkit.birthday_collision(n, categories, verify, verify_trials)


@server.tool()
def dice_sum_distribution(
    num_dice: int,
    sides: int = 6,
    target: int | None = None,
    at_least: int | None = None,
    at_most: int | None = None,
    verify: bool = False,
    verify_trials: int = 20000,
) -> dict:
    """Exact probability distribution over the sum of `num_dice` fair `sides`-sided
    dice. With no range given, returns the full distribution; `target` (an exact
    sum) or `at_least`/`at_most` (a range, either or both) also return that event's
    probability.
    """
    return probkit.dice_sum_distribution(num_dice, sides, target, at_least, at_most, verify, verify_trials)


@server.tool()
def hypergeometric_probability(
    population_size: int,
    success_states: int,
    sample_size: int,
    exactly: int | None = None,
    at_least: int | None = None,
    at_most: int | None = None,
    verify: bool = False,
    verify_trials: int = 20000,
) -> dict:
    """Exact probability of drawing `k` successes when `sample_size` items are drawn
    without replacement from a population of `population_size` containing
    `success_states` successes -- e.g. "at least 2 aces in a 5-card hand" is
    population_size=52, success_states=4, sample_size=5, at_least=2.
    """
    return probkit.hypergeometric_probability(
        population_size, success_states, sample_size, exactly, at_least, at_most, verify, verify_trials
    )


@server.tool()
def binomial_probability(
    n: int,
    prob_success: Any,
    exactly: int | None = None,
    at_least: int | None = None,
    at_most: int | None = None,
    verify: bool = False,
    verify_trials: int = 20000,
) -> dict:
    """Probability of `k` successes in `n` independent trials with per-trial success
    probability `prob_success` (a float in [0,1], or a fraction string like '1/6' to
    keep the arithmetic exact). At least one of `exactly`/`at_least`/`at_most` is
    required.
    """
    return probkit.binomial_probability(n, prob_success, exactly, at_least, at_most, verify, verify_trials)


@server.tool()
def bayes_update(
    prior: Any,
    likelihood_given_true: Any,
    likelihood_given_false: Any,
    verify: bool = False,
    verify_trials: int = 20000,
) -> dict:
    """Exact posterior P(H|E) via Bayes' theorem given P(H) (`prior`), P(E|H)
    (`likelihood_given_true`) and P(E|not H) (`likelihood_given_false`). Inputs may
    be floats or fraction strings ('1/3'). This is the general mechanism behind
    Monty-Hall-style problems once reduced to explicit probabilities -- it computes
    the answer, it does not parse a word problem into these inputs for you.
    """
    return probkit.bayes_update(prior, likelihood_given_true, likelihood_given_false, verify, verify_trials)


@server.tool()
def monty_hall(doors: int = 3, cars: int = 1, reveal: int = 1, verify: bool = False, verify_trials: int = 20000) -> dict:
    """Exact win probability for staying vs. switching in a generalized Monty Hall
    problem: `doors` total doors, `cars` of which hide a prize, the host opens
    `reveal` other non-prize doors after your pick, and switching means picking
    uniformly among the doors still closed. Defaults to the classic 3-door,
    1-car, 1-reveal version (stay 1/3, switch 2/3).
    """
    return probkit.monty_hall(doors, cars, reveal, verify, verify_trials)


if __name__ == "__main__":
    server.run(transport="stdio")
