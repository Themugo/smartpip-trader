from enum import Enum


class MarketType(Enum):
    VOLATILITY = "volatility"
    RISE_FALL = "rise_fall"
    EVEN_ODD = "even_odd"
    OVER_UNDER = "over_under"
    MATCH_DIFF = "match_diff"
    DIGITS = "digits"
