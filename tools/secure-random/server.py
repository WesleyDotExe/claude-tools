"""MCP server exposing randkit's CSPRNG-backed randomness functions.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet.
"""
from typing import Any

from mcp.server.mcpserver import MCPServer

import randkit

server = MCPServer(
    name="secure-random",
    instructions=(
        "Cryptographically-secure randomness. Use these tools instead of "
        "picking a number, shuffling, flipping a coin, or generating a "
        "password yourself in text -- language models predict a plausible-"
        "looking output rather than sampling one, which is why they "
        "reliably favor certain values (e.g. answering 27 to 'a random "
        "number between 1 and 50'). Every draw here comes from the OS "
        "CSPRNG via Python's secrets module, and verify_uniformity can "
        "prove a given range isn't biased."
    ),
)


@server.tool()
def roll_dice(notation: str) -> dict:
    """Roll dice in standard notation: 'NdM' with optional '+K'/'-K', e.g. '2d6+3'."""
    return randkit.roll_dice(notation)


@server.tool()
def random_integers(low: int, high: int, count: int = 1) -> list[int]:
    """`count` independent, uniform, CSPRNG integers in the inclusive range [low, high]."""
    return randkit.random_integers(low, high, count)


@server.tool()
def random_floats(low: float = 0.0, high: float = 1.0, count: int = 1) -> list[float]:
    """`count` independent, uniform, CSPRNG floats in [low, high)."""
    return randkit.random_floats(low, high, count)


@server.tool()
def flip_coins(count: int = 1) -> dict:
    """Flip `count` fair coins; returns each result plus heads/tails totals."""
    return randkit.flip_coins(count)


@server.tool()
def shuffle_list(items: list[Any]) -> list[Any]:
    """Return a CSPRNG-shuffled copy of `items` (Fisher-Yates)."""
    return randkit.shuffle_list(items)


@server.tool()
def pick_random(items: list[Any], count: int = 1, unique: bool = True) -> list[Any]:
    """Pick `count` items from `items`; without replacement by default (unique=True)."""
    return randkit.pick_random(items, count, unique)


@server.tool()
def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> dict:
    """A CSPRNG password guaranteed to include every enabled character class, with its entropy in bits."""
    return randkit.generate_password(
        length, use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous
    )


@server.tool()
def generate_token(nbytes: int = 32, encoding: str = "hex") -> str:
    """A CSPRNG token of `nbytes` random bytes, as 'hex' or 'urlsafe' text."""
    return randkit.generate_token(nbytes, encoding)


@server.tool()
def generate_uuid4() -> str:
    """A random (version 4) UUID."""
    return randkit.generate_uuid4()


@server.tool()
def verify_uniformity(low: int, high: int, samples: int = 10000) -> dict:
    """Chi-square-test `samples` draws from [low, high] for uniformity and report a p-value --
    proof that this tool's output doesn't cluster on a favorite value the way a language
    model's own guesses do.
    """
    return randkit.verify_uniformity(low, high, samples)


if __name__ == "__main__":
    server.run(transport="stdio")
