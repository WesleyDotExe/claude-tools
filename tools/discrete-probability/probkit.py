"""Exact discrete-probability calculations, each checkable against a Monte
Carlo simulation instead of trusted on faith.

This exists because language models are demonstrably unreliable at discrete
probability, and *especially* bad at the "counterintuitive" cases: a 2026
study on counterintuitive discrete-probability problems found models average
0.96 accuracy on standard problems but only 0.59 on counterintuitive ones
(arxiv.org/pdf/2606.07516), and the well-known "LLMs Can't Do Probability"
writeup (brainsteam.co.uk/2024/05/01) documents the same failure informally.
The birthday paradox and the Monty Hall problem are the canonical examples:
both have a single correct answer that is easy to compute exactly and easy
for a model (or a person) to reason about wrong.

Every function here returns an *exact* answer -- computed with `fractions.
Fraction`, not floating-point approximation, wherever the inputs are exact
(counts, discrete outcomes) -- plus, optionally (`verify=True`), a Monte
Carlo cross-check: it actually plays out the scenario `verify_trials` times
using CSPRNG draws (the `secrets` module, the same source of randomness
`tools/secure-random` uses, not `random`'s Mersenne Twister) and reports
whether the empirical frequency lands inside a 95% confidence interval
around the exact answer. That turns "the exact answer is 2/3" from an
assertion into something you can watch play out.

Stdlib only (fractions, math, secrets) -- no dependency beyond `mcp` for the
server wrapper, no network, no account.
"""
from __future__ import annotations

import math
import secrets
from fractions import Fraction

MAX_VERIFY_TRIALS = 500_000
MIN_VERIFY_TRIALS = 100
MAX_DICE_SPACE = 10**8  # cap on sides ** num_dice so results stay exact and printable


def _fraction_to_dict(f: Fraction) -> dict:
    return {"fraction": f"{f.numerator}/{f.denominator}", "decimal": round(float(f), 10)}


def _wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score confidence interval for a binomial proportion.

    Used instead of the naive normal approximation because it stays inside
    [0, 1] and is well-behaved even when the observed proportion is near 0
    or 1 -- exactly where a naive interval misbehaves, and exactly the range
    many of these scenarios (e.g. a rare collision) can land in.
    """
    if trials <= 0:
        raise ValueError("trials must be positive")
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    half_width = (z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))) / denom
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def _check_verify_trials(verify_trials: int) -> None:
    if not (MIN_VERIFY_TRIALS <= verify_trials <= MAX_VERIFY_TRIALS):
        raise ValueError(
            f"verify_trials must be between {MIN_VERIFY_TRIALS} and {MAX_VERIFY_TRIALS}"
        )


def _simulation_report(successes: int, trials: int, exact: Fraction) -> dict:
    lo, hi = _wilson_interval(successes, trials)
    exact_f = float(exact)
    return {
        "trials": trials,
        "successes": successes,
        "observed_frequency": round(successes / trials, 6),
        "exact_probability": round(exact_f, 6),
        "confidence_interval_95": [round(lo, 6), round(hi, 6)],
        "exact_within_confidence_interval": lo <= exact_f <= hi,
    }


# --------------------------------------------------------------------------
# 1. Birthday paradox / collision probability
# --------------------------------------------------------------------------

def birthday_collision(n: int, categories: int = 365, verify: bool = False, verify_trials: int = 20000) -> dict:
    """Exact probability that >=2 of `n` items, each independently and
    uniformly drawn from `categories` possible values (with replacement),
    collide -- the birthday paradox, generalized beyond 365 days.

    P(no collision) = categories! / ((categories-n)! * categories^n), so
    P(collision) = 1 - that product, computed exactly term by term.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if categories < 1:
        raise ValueError("categories must be >= 1")
    if n > categories:
        no_collision = Fraction(0)
    elif n <= 1:
        no_collision = Fraction(1)
    else:
        no_collision = Fraction(1)
        for i in range(n):
            no_collision *= Fraction(categories - i, categories)
    p_collision = 1 - no_collision
    result = {
        "n": n,
        "categories": categories,
        "probability_of_collision": _fraction_to_dict(p_collision),
    }
    if verify:
        _check_verify_trials(verify_trials)
        successes = 0
        for _ in range(verify_trials):
            seen = set()
            collided = False
            for _ in range(n):
                v = secrets.randbelow(categories)
                if v in seen:
                    collided = True
                    break
                seen.add(v)
            if collided:
                successes += 1
        result["simulation"] = _simulation_report(successes, verify_trials, p_collision)
    return result


# --------------------------------------------------------------------------
# 2. Dice-sum distribution
# --------------------------------------------------------------------------

def _dice_sum_counts(num_dice: int, sides: int) -> list[int]:
    """counts[s - num_dice] = number of ways `num_dice` fair `sides`-sided dice
    can sum to `s`, via DP convolution (exact integer counts, no rounding).
    """
    counts = [1]  # ways to reach each sum for 0 dice so far, offset 0 (sum=0)
    for _ in range(num_dice):
        new_len = len(counts) + sides - 1
        new_counts = [0] * new_len
        for offset, ways in enumerate(counts):
            for face in range(1, sides + 1):
                new_counts[offset + face - 1] += ways
        counts = new_counts
    return counts


def dice_sum_distribution(
    num_dice: int,
    sides: int = 6,
    target: int | None = None,
    at_least: int | None = None,
    at_most: int | None = None,
    verify: bool = False,
    verify_trials: int = 20000,
) -> dict:
    """Exact probability distribution over the sum of `num_dice` fair
    `sides`-sided dice. With no range arguments, returns the full
    distribution; `target` / `at_least` / `at_most` (any combination) also
    return the probability of that specific event.
    """
    if num_dice < 1:
        raise ValueError("num_dice must be >= 1")
    if sides < 2:
        raise ValueError("sides must be >= 2")
    space = sides ** num_dice
    if space > MAX_DICE_SPACE:
        raise ValueError(
            f"sides**num_dice ({space}) exceeds the cap of {MAX_DICE_SPACE}; "
            "use fewer dice or fewer sides"
        )
    counts = _dice_sum_counts(num_dice, sides)
    min_sum = num_dice
    distribution = {min_sum + i: Fraction(c, space) for i, c in enumerate(counts)}

    result = {
        "num_dice": num_dice,
        "sides": sides,
        "min_sum": min_sum,
        "max_sum": num_dice * sides,
        "distribution": {str(s): _fraction_to_dict(p) for s, p in distribution.items()},
    }

    if target is not None or at_least is not None or at_most is not None:
        lo = at_least if at_least is not None else min_sum
        hi = at_most if at_most is not None else num_dice * sides
        if target is not None:
            lo = hi = target
        event_prob = sum((p for s, p in distribution.items() if lo <= s <= hi), Fraction(0))
        result["event"] = {"at_least": lo, "at_most": hi}
        result["event_probability"] = _fraction_to_dict(event_prob)

        if verify:
            _check_verify_trials(verify_trials)
            successes = 0
            for _ in range(verify_trials):
                total = sum(secrets.randbelow(sides) + 1 for _ in range(num_dice))
                if lo <= total <= hi:
                    successes += 1
            result["simulation"] = _simulation_report(successes, verify_trials, event_prob)

    return result


# --------------------------------------------------------------------------
# 3. Hypergeometric probability (sampling without replacement)
# --------------------------------------------------------------------------

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
    """Exact probability of drawing `k` successes when `sample_size` items
    are drawn without replacement from a population of `population_size`
    containing `success_states` "successes" (e.g. aces in a deck, defective
    parts in a batch). At least one of `exactly` / `at_least` / `at_most`
    must be given.
    """
    if population_size < 1:
        raise ValueError("population_size must be >= 1")
    if not (0 <= success_states <= population_size):
        raise ValueError("success_states must be between 0 and population_size")
    if not (0 <= sample_size <= population_size):
        raise ValueError("sample_size must be between 0 and population_size")
    if exactly is None and at_least is None and at_most is None:
        raise ValueError("must give at least one of exactly, at_least, at_most")

    lo_k = max(0, sample_size - (population_size - success_states))
    hi_k = min(sample_size, success_states)

    def p_exact(k: int) -> Fraction:
        if k < lo_k or k > hi_k:
            return Fraction(0)
        return Fraction(
            math.comb(success_states, k) * math.comb(population_size - success_states, sample_size - k),
            math.comb(population_size, sample_size),
        )

    if exactly is not None:
        lo, hi = exactly, exactly
    else:
        lo = at_least if at_least is not None else lo_k
        hi = at_most if at_most is not None else hi_k

    event_prob = sum((p_exact(k) for k in range(max(lo, 0), min(hi, sample_size) + 1)), Fraction(0))

    result = {
        "population_size": population_size,
        "success_states": success_states,
        "sample_size": sample_size,
        "event": {"at_least": lo, "at_most": hi},
        "event_probability": _fraction_to_dict(event_prob),
    }

    if verify:
        _check_verify_trials(verify_trials)
        population = [1] * success_states + [0] * (population_size - success_states)
        successes = 0
        for _ in range(verify_trials):
            pool = population.copy()
            drawn_successes = 0
            n = population_size
            for _ in range(sample_size):
                i = secrets.randbelow(n)
                drawn_successes += pool[i]
                pool[i] = pool[n - 1]
                pool.pop()
                n -= 1
            if lo <= drawn_successes <= hi:
                successes += 1
        result["simulation"] = _simulation_report(successes, verify_trials, event_prob)

    return result


# --------------------------------------------------------------------------
# 4. Binomial probability
# --------------------------------------------------------------------------

def _parse_probability(p) -> Fraction | float:
    """Accept a float in [0, 1], an int (0 or 1), or a fraction string like '1/6'.
    Strings and ints stay exact (as a Fraction); floats stay float, since a
    literal like 0.1 is not exactly representable and shouldn't be laundered
    into a falsely-precise fraction.
    """
    if isinstance(p, str):
        frac = Fraction(p)
    elif isinstance(p, int) and not isinstance(p, bool):
        frac = Fraction(p)
    else:
        if not (0 <= p <= 1):
            raise ValueError("probability must be between 0 and 1")
        return p
    if not (0 <= frac <= 1):
        raise ValueError("probability must be between 0 and 1")
    return frac


def binomial_probability(
    n: int,
    prob_success,
    exactly: int | None = None,
    at_least: int | None = None,
    at_most: int | None = None,
    verify: bool = False,
    verify_trials: int = 20000,
) -> dict:
    """Exact-where-possible probability of `k` successes in `n` independent
    trials with per-trial success probability `prob_success` (a float, or a
    fraction string like '1/6' to keep the arithmetic exact). At least one
    of `exactly` / `at_least` / `at_most` must be given.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if exactly is None and at_least is None and at_most is None:
        raise ValueError("must give at least one of exactly, at_least, at_most")
    p = _parse_probability(prob_success)
    exact_arith = isinstance(p, Fraction)

    def p_exact(k: int):
        if not (0 <= k <= n):
            return Fraction(0) if exact_arith else 0.0
        return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))

    if exactly is not None:
        lo, hi = exactly, exactly
    else:
        lo = at_least if at_least is not None else 0
        hi = at_most if at_most is not None else n

    zero = Fraction(0) if exact_arith else 0.0
    event_prob = sum((p_exact(k) for k in range(max(lo, 0), min(hi, n) + 1)), zero)

    result = {
        "n": n,
        "prob_success": f"{p.numerator}/{p.denominator}" if exact_arith else p,
        "event": {"at_least": lo, "at_most": hi},
        "event_probability": (
            _fraction_to_dict(event_prob) if exact_arith else {"decimal": round(event_prob, 10)}
        ),
    }

    if verify:
        _check_verify_trials(verify_trials)
        # Draw against p using an exact CSPRNG comparison: represent p as a
        # fraction (converting a float via limit_denominator keeps the draw
        # exact rather than reintroducing float rounding into the coin flip).
        p_frac = p if exact_arith else Fraction(p).limit_denominator(10**9)
        successes = 0
        for _ in range(verify_trials):
            k = sum(
                1 for _ in range(n)
                if secrets.randbelow(p_frac.denominator) < p_frac.numerator
            )
            if lo <= k <= hi:
                successes += 1
        exact_for_ci = event_prob if exact_arith else Fraction(event_prob).limit_denominator(10**9)
        result["simulation"] = _simulation_report(successes, verify_trials, exact_for_ci)

    return result


# --------------------------------------------------------------------------
# 5. Bayes' theorem update
# --------------------------------------------------------------------------

def bayes_update(
    prior,
    likelihood_given_true,
    likelihood_given_false,
    verify: bool = False,
    verify_trials: int = 20000,
) -> dict:
    """Exact posterior P(H|E) via Bayes' theorem, given P(H) (`prior`),
    P(E|H) (`likelihood_given_true`) and P(E|not H) (`likelihood_given_false`).
    Inputs may be floats or fraction strings like '1/3'; the arithmetic
    stays exact if every input is exact.

    This is the general mechanism behind Monty-Hall-style "the answer is
    less obvious than it looks" problems once the scenario has been reduced
    to explicit probabilities -- like `time-arithmetic`, this tool computes
    once the inputs are unambiguous; it does not parse a word problem into
    those inputs for you.
    """
    prior_f = _parse_probability(prior)
    lt_f = _parse_probability(likelihood_given_true)
    lf_f = _parse_probability(likelihood_given_false)
    exact_arith = isinstance(prior_f, Fraction) and isinstance(lt_f, Fraction) and isinstance(lf_f, Fraction)
    if not exact_arith:
        prior_f, lt_f, lf_f = float(prior_f), float(lt_f), float(lf_f)

    evidence = prior_f * lt_f + (1 - prior_f) * lf_f
    if evidence == 0:
        raise ValueError("P(E) is zero (evidence is impossible given the supplied likelihoods); posterior is undefined")
    posterior = (prior_f * lt_f) / evidence

    result = {
        "prior": _fraction_to_dict(prior_f) if exact_arith else round(prior_f, 10),
        "likelihood_given_true": _fraction_to_dict(lt_f) if exact_arith else round(lt_f, 10),
        "likelihood_given_false": _fraction_to_dict(lf_f) if exact_arith else round(lf_f, 10),
        "evidence": _fraction_to_dict(evidence) if exact_arith else round(evidence, 10),
        "posterior": _fraction_to_dict(posterior) if exact_arith else round(posterior, 10),
    }

    if verify:
        _check_verify_trials(verify_trials)
        pr = prior_f if exact_arith else Fraction(prior_f).limit_denominator(10**9)
        lt = lt_f if exact_arith else Fraction(lt_f).limit_denominator(10**9)
        lf = lf_f if exact_arith else Fraction(lf_f).limit_denominator(10**9)
        h_true_and_e = 0
        e_count = 0
        for _ in range(verify_trials):
            h = secrets.randbelow(pr.denominator) < pr.numerator
            like = lt if h else lf
            e = secrets.randbelow(like.denominator) < like.numerator
            if e:
                e_count += 1
                if h:
                    h_true_and_e += 1
        exact_for_ci = posterior if exact_arith else Fraction(posterior).limit_denominator(10**9)
        if e_count == 0:
            result["simulation"] = {
                "trials": verify_trials,
                "note": "evidence E never occurred in this many simulated trials; "
                "increase verify_trials or check the likelihoods aren't both near zero",
            }
        else:
            result["simulation"] = _simulation_report(h_true_and_e, e_count, exact_for_ci)
            result["simulation"]["trials_where_evidence_occurred"] = e_count

    return result


# --------------------------------------------------------------------------
# 6. Monty Hall (generalized)
# --------------------------------------------------------------------------

def monty_hall(doors: int = 3, cars: int = 1, reveal: int = 1, verify: bool = False, verify_trials: int = 20000) -> dict:
    """Exact win probability for staying vs. switching in a generalized Monty
    Hall problem: `doors` total doors, `cars` of which hide a prize, the
    contestant picks one uniformly at random, the host then opens `reveal`
    other doors known to hide no prize, and "switch" means picking uniformly
    at random among the still-closed doors other than the original pick.

    Derivation (see README): P(win|stay) = cars/doors, and
    P(win|switch) = cars*(doors-1) / (doors*(doors-1-reveal)) -- which
    reduces to the classic 1/3 vs 2/3 at doors=3, cars=1, reveal=1.
    """
    if doors < 3:
        raise ValueError("doors must be >= 3")
    if not (1 <= cars < doors):
        raise ValueError("cars must be between 1 and doors-1")
    max_reveal = doors - cars - 1
    if not (0 <= reveal <= max_reveal):
        raise ValueError(
            f"reveal must be between 0 and doors-cars-1 ({max_reveal}) so the host can "
            "always find that many non-prize, non-chosen doors to open regardless of "
            "whether the contestant's initial pick was a prize door"
        )

    p_stay = Fraction(cars, doors)
    p_switch = Fraction(cars * (doors - 1), doors * (doors - 1 - reveal))

    result = {
        "doors": doors,
        "cars": cars,
        "reveal": reveal,
        "win_probability_if_stay": _fraction_to_dict(p_stay),
        "win_probability_if_switch": _fraction_to_dict(p_switch),
        "switching_is_better": p_switch > p_stay,
    }

    if verify:
        _check_verify_trials(verify_trials)
        stay_wins = 0
        switch_wins = 0
        door_ids = list(range(doors))
        for _ in range(verify_trials):
            car_doors = set()
            pool = door_ids.copy()
            n = doors
            for _ in range(cars):
                i = secrets.randbelow(n)
                car_doors.add(pool[i])
                pool[i] = pool[n - 1]
                pool.pop()
                n -= 1
            pick = door_ids[secrets.randbelow(doors)]
            if pick in car_doors:
                stay_wins += 1

            # Host reveals `reveal` doors, drawn without replacement from the
            # goats among the doors other than the contestant's pick.
            goat_pool = [d for d in door_ids if d != pick and d not in car_doors]
            revealed = set()
            for _ in range(reveal):
                idx = secrets.randbelow(len(goat_pool))
                revealed.add(goat_pool.pop(idx))

            switch_choice_pool = [d for d in door_ids if d != pick and d not in revealed]
            switch_pick = switch_choice_pool[secrets.randbelow(len(switch_choice_pool))]
            if switch_pick in car_doors:
                switch_wins += 1

        result["simulation"] = {
            "trials": verify_trials,
            "stay": _simulation_report(stay_wins, verify_trials, p_stay),
            "switch": _simulation_report(switch_wins, verify_trials, p_switch),
        }

    return result
