"""
Shared ELO rating math.
Canonical formula from mlb-daily-elo-compute: K=20, HFA=55, log-based MOV.
"""
import math
from mlb_common.config import ELO_K, ELO_HFA, MOV_MULTIPLIER, MOV_CAP


def expected_score(elo_a, elo_b, hfa=0):
    """
    Calculate expected win probability for team A.

    Args:
        elo_a: ELO rating of team A
        elo_b: ELO rating of team B
        hfa: Home field advantage added to team A's rating (0 if neutral)

    Returns:
        Probability of team A winning (0.0 to 1.0)
    """
    return 1 / (1 + 10 ** ((elo_b - (elo_a + hfa)) / 400))


def margin_of_victory_mult(score_diff, elo_diff):
    """
    Margin of victory multiplier using log formula.

    Scales the K-factor based on how lopsided the game was, dampened
    by the pre-game ELO difference (blowouts by favorites count less).

    Args:
        score_diff: Absolute run differential
        elo_diff: ELO difference (home - away, before HFA adjustment)

    Returns:
        Multiplier (typically 0.5 to 2.5)
    """
    raw = math.log(abs(score_diff) + 1) * (MOV_MULTIPLIER / (0.001 * abs(elo_diff) + MOV_MULTIPLIER))
    return min(raw, MOV_CAP)


def update_elo(elo, expected, actual, k=ELO_K, mov_mult=1.0):
    """
    Calculate new ELO rating after a game.

    Args:
        elo: Current ELO rating
        expected: Expected win probability (from expected_score)
        actual: Actual result (1.0 for win, 0.0 for loss)
        k: K-factor (default from config)
        mov_mult: Margin of victory multiplier

    Returns:
        ELO shift (add to winner, subtract from loser)
    """
    return k * mov_mult * (actual - expected)
