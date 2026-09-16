"""Research package: canonical historical laboratory plus existing research APIs."""
try:
    from .lab import ResearchLab
except Exception:
    ResearchLab = None
try:
    from .tracking import *
except Exception:
    pass
from .historical_opportunity_engine import HistoricalOpportunityEngine, HistoricalTick, load_ticks
