"""Cryptographically-secure randomness, deterministic statistics, and stdlib-only
chi-square uniformity testing.

This exists because language models cannot generate genuine randomness: they
predict the next token from learned patterns, so "pick a random number" comes
back skewed toward whatever value is most common in training data (the
well-documented "27" phenomenon: several widely-used assistants asked for "a
random number between 1 and 50" all answered 27). Every function here is
backed by the `secrets` module (CSPRNG, drawn from the OS entropy source),
not by asking a model to imagine an output.

`verify_uniformity` is the proof mechanism: run N draws from a range through
the exact chi-square goodness-of-fit test and report a p-value, so a
uniformity claim about this tool's output is checkable rather than asserted.
Stdlib only (secrets, uuid, string, math, re) -- no third-party dependency,
no network, no account.
"""
from __future__ import annotations

import math
import re
import secrets
import string
import uuid

_DICE_RE = re.compile(r"^\s*(?P<count>\d*)d(?P<sides>\d+)(?P<mod>[+-]\d+)?\s*$", re.IGNORECASE)

_AMBIGUOUS = set("Il1O0")
_DEFAULT_SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?"

MAX_DICE_COUNT = 1000
MAX_DICE_SIDES = 1_000_000
MAX_UNIFORMITY_SAMPLES = 2_000_000


def roll_dice(notation: str) -> dict:
    """Roll dice given standard notation: 'NdM' with an optional '+K'/'-K' modifier.

    Examples: 'd20', '2d6', '4d6+2', '1d100-5'. N defaults to 1 if omitted.
    """
    m = _DICE_RE.match(notation or "")
    if not m:
        raise ValueError(
            f"invalid dice notation: {notation!r} (expected e.g. 'd20', '2d6', '4d6+2')"
        )
    count = int(m.group("count")) if m.group("count") else 1
    sides = int(m.group("sides"))
    modifier = int(m.group("mod")) if m.group("mod") else 0
    if not (1 <= count <= MAX_DICE_COUNT):
        raise ValueError(f"dice count must be between 1 and {MAX_DICE_COUNT}")
    if not (2 <= sides <= MAX_DICE_SIDES):
        raise ValueError(f"dice sides must be between 2 and {MAX_DICE_SIDES}")
    rolls = [secrets.randbelow(sides) + 1 for _ in range(count)]
    return {
        "notation": notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": sum(rolls) + modifier,
    }


def random_integers(low: int, high: int, count: int = 1) -> list[int]:
    """`count` independent, uniform, CSPRNG-backed integers in [low, high]."""
    if low > high:
        raise ValueError("low must be <= high")
    if not (1 <= count <= 100_000):
        raise ValueError("count must be between 1 and 100000")
    span = high - low + 1
    return [low + secrets.randbelow(span) for _ in range(count)]


def _random_unit_float() -> float:
    # Full 53-bit mantissa precision, same approach CPython's random.random()
    # uses -- but drawn from secrets.randbits (CSPRNG), not the Mersenne Twister.
    return secrets.randbits(53) / (1 << 53)


def random_floats(low: float = 0.0, high: float = 1.0, count: int = 1) -> list[float]:
    """`count` independent, uniform, CSPRNG-backed floats in [low, high)."""
    if low > high:
        raise ValueError("low must be <= high")
    if not (1 <= count <= 100_000):
        raise ValueError("count must be between 1 and 100000")
    return [low + (high - low) * _random_unit_float() for _ in range(count)]


def flip_coins(count: int = 1) -> dict:
    """Flip `count` fair coins."""
    if not (1 <= count <= 100_000):
        raise ValueError("count must be between 1 and 100000")
    results = ["heads" if secrets.randbelow(2) == 0 else "tails" for _ in range(count)]
    return {
        "results": results,
        "heads": results.count("heads"),
        "tails": results.count("tails"),
    }


def shuffle_list(items: list) -> list:
    """Return a CSPRNG Fisher-Yates shuffle of `items` (does not mutate the input)."""
    arr = list(items)
    for i in range(len(arr) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        arr[i], arr[j] = arr[j], arr[i]
    return arr


def _validate_weights(weights: list[float], n_items: int) -> None:
    if len(weights) != n_items:
        raise ValueError("weights must be the same length as items")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    if sum(weights) <= 0:
        raise ValueError("weights must sum to a positive number")


def _weighted_index(weights: list[float]) -> int:
    """Pick an index with probability proportional to `weights`, using CSPRNG-
    backed uniform floats (not the `random` module) for the draw.
    """
    total = sum(weights)
    target = _random_unit_float() * total
    cumulative = 0.0
    for i, w in enumerate(weights):
        cumulative += w
        if target < cumulative:
            return i
    return len(weights) - 1  # floating-point edge case: target == total


def pick_random(
    items: list, count: int = 1, unique: bool = True, weights: list[float] | None = None
) -> list:
    """Pick `count` items from `items`, with or without replacement.

    `weights` (optional) makes the selection biased instead of uniform: item i
    is picked with probability proportional to `weights[i]` (e.g. a raffle
    weighted by ticket count). Omit it for the original uniform behavior.
    """
    if not items:
        raise ValueError("items must be non-empty")
    if count < 1:
        raise ValueError("count must be >= 1")
    if weights is None:
        if unique:
            if count > len(items):
                raise ValueError("count exceeds number of items for a unique selection")
            return shuffle_list(items)[:count]
        return [items[secrets.randbelow(len(items))] for _ in range(count)]

    _validate_weights(weights, len(items))
    if not unique:
        return [items[_weighted_index(weights)] for _ in range(count)]

    if count > len(items):
        raise ValueError("count exceeds number of items for a unique selection")
    pool_items = list(items)
    pool_weights = list(weights)
    picked = []
    for _ in range(count):
        i = _weighted_index(pool_weights)
        picked.append(pool_items.pop(i))
        pool_weights.pop(i)
    return picked


def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> dict:
    """A CSPRNG password guaranteed to include every enabled character class."""
    pools = []
    if use_lower:
        pools.append(string.ascii_lowercase)
    if use_upper:
        pools.append(string.ascii_uppercase)
    if use_digits:
        pools.append(string.digits)
    if use_symbols:
        pools.append(_DEFAULT_SYMBOLS)
    if not pools:
        raise ValueError("at least one character class must be enabled")
    if exclude_ambiguous:
        pools = ["".join(c for c in pool if c not in _AMBIGUOUS) for pool in pools]
        pools = [pool for pool in pools if pool]
        if not pools:
            raise ValueError("excluding ambiguous characters left no usable character classes")
    if length < len(pools):
        raise ValueError(
            f"length must be >= number of enabled character classes ({len(pools)})"
        )
    alphabet = "".join(pools)
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice(alphabet) for _ in range(length - len(pools))]
    chars = shuffle_list(chars)
    entropy_bits = length * math.log2(len(alphabet))
    return {
        "password": "".join(chars),
        "length": length,
        "alphabet_size": len(alphabet),
        "entropy_bits": round(entropy_bits, 1),
    }


def generate_token(nbytes: int = 32, encoding: str = "hex") -> str:
    """A CSPRNG token of `nbytes` random bytes, as 'hex' or 'urlsafe' text."""
    if not (1 <= nbytes <= 1024):
        raise ValueError("nbytes must be between 1 and 1024")
    if encoding == "hex":
        return secrets.token_hex(nbytes)
    if encoding == "urlsafe":
        return secrets.token_urlsafe(nbytes)
    raise ValueError("encoding must be 'hex' or 'urlsafe'")


def generate_uuid4() -> str:
    """A random (version 4) UUID, drawn from os.urandom."""
    return str(uuid.uuid4())


# --- Chi-square goodness-of-fit, implemented from scratch (stdlib only, no
# scipy) so `verify_uniformity` below can turn "is this actually uniform?"
# into a checkable p-value instead of a claim. -----------------------------

def _lower_incomplete_gamma_series(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) via its series expansion.

    Valid (converges quickly) for x < a + 1.
    """
    if x == 0:
        return 0.0
    gln = math.lgamma(a)
    ap = a
    term = 1.0 / a
    total = term
    for _ in range(500):
        ap += 1
        term *= x / ap
        total += term
        if abs(term) < abs(total) * 1e-15:
            break
    return total * math.exp(-x + a * math.log(x) - gln)


def _upper_incomplete_gamma_cf(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) via a continued fraction.

    Valid (converges quickly) for x >= a + 1. (Lentz's algorithm.)
    """
    tiny = 1e-300
    gln = math.lgamma(a)
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def chi2_sf(x: float, df: int) -> float:
    """Survival function of the chi-square distribution: P(X > x) for `df` degrees
    of freedom -- i.e. the p-value for an observed chi-square statistic `x`.
    """
    if df < 1:
        raise ValueError("df must be >= 1")
    if x <= 0:
        return 1.0
    a = df / 2.0
    xx = x / 2.0
    if xx < a + 1:
        return 1.0 - _lower_incomplete_gamma_series(a, xx)
    return _upper_incomplete_gamma_cf(a, xx)


def _chi_square_fit(counts: list[int], expected: list[float]) -> tuple[float, int, float]:
    """Chi-square goodness-of-fit of `counts` against arbitrary `expected` counts.

    Returns (chi2_statistic, degrees_of_freedom, p_value). Shared by
    `_chi_square_uniform` (expected is a flat share) and
    `verify_weighted_distribution` (expected follows arbitrary weights).
    """
    if len(counts) != len(expected):
        raise ValueError("counts and expected must be the same length")
    if len(counts) < 2:
        raise ValueError("need at least 2 buckets")
    chi2 = sum((c - e) ** 2 / e for c, e in zip(counts, expected))
    df = len(counts) - 1
    return chi2, df, chi2_sf(chi2, df)


def _chi_square_uniform(counts: list[int]) -> tuple[float, int, float]:
    """Chi-square goodness-of-fit of `counts` against a uniform distribution.

    Pulled out from verify_uniformity so tests can feed it a synthetic
    histogram directly, without needing to bias the CSPRNG itself to prove
    the test catches bias.
    """
    n_buckets = len(counts)
    if n_buckets < 2:
        raise ValueError("need at least 2 buckets")
    samples = sum(counts)
    expected = [samples / n_buckets] * n_buckets
    return _chi_square_fit(counts, expected)


def verify_uniformity(low: int, high: int, samples: int = 10000) -> dict:
    """Draw `samples` CSPRNG integers from [low, high] and chi-square test them
    for uniformity -- proof, not assertion, that this tool's randomness doesn't
    cluster on a favorite value the way a language model's guesses do.
    """
    if low >= high:
        raise ValueError("high must be > low")
    n_buckets = high - low + 1
    if samples < n_buckets * 5:
        raise ValueError(f"need at least {n_buckets * 5} samples to test {n_buckets} buckets")
    if samples > MAX_UNIFORMITY_SAMPLES:
        raise ValueError(f"samples must be <= {MAX_UNIFORMITY_SAMPLES}")
    counts = [0] * n_buckets
    for _ in range(samples):
        counts[secrets.randbelow(n_buckets)] += 1
    chi2, df, p_value = _chi_square_uniform(counts)
    peak_index = max(range(n_buckets), key=lambda i: counts[i])
    return {
        "range": [low, high],
        "samples": samples,
        "buckets": n_buckets,
        "chi2_statistic": round(chi2, 3),
        "degrees_of_freedom": df,
        "p_value": round(p_value, 6),
        "uniform_at_0.05": p_value > 0.05,
        "most_sampled_value": low + peak_index,
        "most_sampled_share": round(counts[peak_index] / samples, 4),
        "expected_share": round(1 / n_buckets, 4),
    }


def verify_weighted_distribution(weights: list[float], samples: int = 10000) -> dict:
    """Draw `samples` CSPRNG weighted picks over `weights` and chi-square test the
    observed counts against the weight-proportional distribution they should
    follow -- the same proof-not-assertion pattern as `verify_uniformity`, applied
    to `pick_random`'s weighted mode so a claim like "item 2 comes up ~40% of the
    time" is checkable instead of just plausible-sounding.
    """
    n_buckets = len(weights)
    if n_buckets < 2:
        raise ValueError("need at least 2 weights")
    if any(w <= 0 for w in weights):
        raise ValueError("weights must be strictly positive (a zero-weight bucket has no expected count to test)")
    if samples < n_buckets * 5:
        raise ValueError(f"need at least {n_buckets * 5} samples to test {n_buckets} buckets")
    if samples > MAX_UNIFORMITY_SAMPLES:
        raise ValueError(f"samples must be <= {MAX_UNIFORMITY_SAMPLES}")
    total_weight = sum(weights)
    counts = [0] * n_buckets
    for _ in range(samples):
        counts[_weighted_index(weights)] += 1
    expected = [samples * w / total_weight for w in weights]
    chi2, df, p_value = _chi_square_fit(counts, expected)
    return {
        "weights": weights,
        "samples": samples,
        "buckets": n_buckets,
        "chi2_statistic": round(chi2, 3),
        "degrees_of_freedom": df,
        "p_value": round(p_value, 6),
        "matches_weights_at_0.05": p_value > 0.05,
        "observed_shares": [round(c / samples, 4) for c in counts],
        "expected_shares": [round(w / total_weight, 4) for w in weights],
    }
