import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import hashlib


class MarketLock:
    """Lock all market configurations to prevent unauthorized changes"""
    
    def __init__(self):
        self.locked = False
        self.lock_hash = None
        self.lock_timestamp = None
        self.authorized_keys = set(os.getenv("AUTHORIZED_KEYS", "").split(","))
        self.production_mode = os.getenv("PRODUCTION_MODE", "false").lower() == "true"
        
        # Locked market configuration
        self.locked_markets = {
            "R_10": {"enabled": True, "type": "tick", "min_confidence": 85},
            "R_25": {"enabled": True, "type": "tick", "min_confidence": 85},
            "R_50": {"enabled": True, "type": "tick", "min_confidence": 85},
            "R_75": {"enabled": True, "type": "tick", "min_confidence": 85},
            "R_100": {"enabled": True, "type": "tick", "min_confidence": 85},
            "R_10_10S": {"enabled": True, "type": "short", "min_confidence": 90},
            "R_25_10S": {"enabled": True, "type": "short", "min_confidence": 90},
            "R_50_10S": {"enabled": True, "type": "short", "min_confidence": 90},
            "R_75_10S": {"enabled": True, "type": "short", "min_confidence": 90},
            "R_100_10S": {"enabled": True, "type": "short", "min_confidence": 90},
            "R_100_25S": {"enabled": True, "type": "short", "min_confidence": 90},
            "R_100_50S": {"enabled": True, "type": "short", "min_confidence": 90}
        }
        
        # Locked analysis configuration
        self.locked_analyzers = {
            "even_odd": {"enabled": True, "weight": 0.15},
            "rise_fall": {"enabled": True, "weight": 0.20},
            "over_under": {"enabled": True, "weight": 0.20},
            "match_diff": {"enabled": True, "weight": 0.15},
            "technical": {"enabled": True, "weight": 0.20},
            "ml": {"enabled": True, "weight": 0.10}
        }
        
        # Locked strategy configuration
        self.locked_strategies = {
            "sniper": {"enabled": True, "min_confidence": 85},
            "hft": {"enabled": True, "min_confidence": 80},
            "unified": {"enabled": True, "min_confidence": 80}
        }
        
        # Load lock state if exists
        self._load_lock_state()
    
    def lock(self, auth_key: str) -> bool:
        """Lock all market configurations"""
        if not self._is_authorized(auth_key):
            return False
        
        if self.locked:
            return False  # Already locked
        
        # Generate lock hash
        config_hash = self._generate_config_hash()
        self.lock_hash = config_hash
        self.lock_timestamp = datetime.now().isoformat()
        self.locked = True
        
        # Save lock state
        self._save_lock_state()
        
        return True
    
    def unlock(self, auth_key: str) -> bool:
        """Unlock market configurations (only in non-production)"""
        if self.production_mode:
            return False  # Cannot unlock in production
        
        if not self._is_authorized(auth_key):
            return False
        
        if not self.locked:
            return False  # Already unlocked
        
        # Verify lock hash hasn't changed
        current_hash = self._generate_config_hash()
        if current_hash != self.lock_hash:
            return False  # Configuration has been tampered with
        
        self.locked = False
        self.lock_hash = None
        self.lock_timestamp = None
        
        # Save lock state
        self._save_lock_state()
        
        return True
    
    def is_locked(self) -> bool:
        """Check if system is locked"""
        return self.locked
    
    def verify_integrity(self) -> bool:
        """Verify configuration integrity"""
        if not self.locked:
            return True
        
        current_hash = self._generate_config_hash()
        return current_hash == self.lock_hash
    
    def get_market_config(self, market: str) -> Optional[Dict[str, Any]]:
        """Get locked market configuration"""
        if self.locked:
            return self.locked_markets.get(market)
        return None
    
    def get_analyzer_config(self, analyzer: str) -> Optional[Dict[str, Any]]:
        """Get locked analyzer configuration"""
        if self.locked:
            return self.locked_analyzers.get(analyzer)
        return None
    
    def get_strategy_config(self, strategy: str) -> Optional[Dict[str, Any]]:
        """Get locked strategy configuration"""
        if self.locked:
            return self.locked_strategies.get(strategy)
        return None
    
    def _is_authorized(self, auth_key: str) -> bool:
        """Check if authorization key is valid"""
        return auth_key in self.authorized_keys
    
    def _generate_config_hash(self) -> str:
        """Generate hash of current configuration"""
        config_data = {
            "markets": self.locked_markets,
            "analyzers": self.locked_analyzers,
            "strategies": self.locked_strategies
        }
        config_str = json.dumps(config_data, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    def _save_lock_state(self):
        """Save lock state to file"""
        lock_state = {
            "locked": self.locked,
            "lock_hash": self.lock_hash,
            "lock_timestamp": self.lock_timestamp,
            "production_mode": self.production_mode
        }
        
        with open("config/market_lock.json", "w") as f:
            json.dump(lock_state, f, indent=2)
    
    def _load_lock_state(self):
        """Load lock state from file"""
        try:
            with open("config/market_lock.json", "r") as f:
                lock_state = json.load(f)
                self.locked = lock_state.get("locked", False)
                self.lock_hash = lock_state.get("lock_hash")
                self.lock_timestamp = lock_state.get("lock_timestamp")
                self.production_mode = lock_state.get("production_mode", False)
        except FileNotFoundError:
            pass
    
    def get_lock_status(self) -> Dict[str, Any]:
        """Get current lock status"""
        return {
            "locked": self.locked,
            "lock_timestamp": self.lock_timestamp,
            "production_mode": self.production_mode,
            "integrity_verified": self.verify_integrity(),
            "markets_count": len(self.locked_markets),
            "analyzers_count": len(self.locked_analyzers),
            "strategies_count": len(self.locked_strategies)
        }
