# maturity_ratings.py: Caclulate maturity ratings (ELO) for players

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def expected_score(rating1: float, rating2: float) -> float:
    """Calculate expected score for player with rating1 against player with rating2."""
    return 1 / (1 + 10 ** ((rating2 - rating1) / 400))