import requests
from typing import Dict, Any, Optional
import os
from datetime import datetime, timedelta
from collections import deque


class CurrencyConverter:
    """Currency conversion for Kenyan market (USD/KES)"""
    
    def __init__(self):
        self.cache = deque(maxlen=100)
        self.cache_ttl = 3600  # 1 hour
        self.base_currency = "KES"
        self.target_currency = "USD"
        self.exchange_rate = 130.0  # Default USD/KES rate
        self.last_update = None
    
    def get_exchange_rate(self, from_currency: str = "USD", 
                         to_currency: str = "KES") -> float:
        """
        Get current exchange rate
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Exchange rate
        """
        # Check cache
        cache_key = f"{from_currency}_{to_currency}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Fetch from API
        try:
            rate = self._fetch_rate_from_api(from_currency, to_currency)
            self._cache_rate(cache_key, rate)
            return rate
        except Exception as e:
            # Use cached rate or default
            if from_currency == "USD" and to_currency == "KES":
                return self.exchange_rate
            elif from_currency == "KES" and to_currency == "USD":
                return 1.0 / self.exchange_rate
            return 1.0
    
    def _fetch_rate_from_api(self, from_currency: str, to_currency: str) -> float:
        """Fetch exchange rate from API"""
        # Using a free exchange rate API
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            rate = data["rates"].get(to_currency, 1.0)
            
            # Update default rate if USD/KES
            if from_currency == "USD" and to_currency == "KES":
                self.exchange_rate = rate
                self.last_update = datetime.now()
            
            return rate
        
        raise Exception("Failed to fetch exchange rate")
    
    def _get_from_cache(self, key: str) -> Optional[float]:
        """Get rate from cache"""
        for cached in self.cache:
            if cached["key"] == key:
                # Check if still valid
                if datetime.now() - cached["timestamp"] < timedelta(seconds=self.cache_ttl):
                    return cached["rate"]
        return None
    
    def _cache_rate(self, key: str, rate: float):
        """Cache exchange rate"""
        self.cache.append({
            "key": key,
            "rate": rate,
            "timestamp": datetime.now()
        })
    
    def convert(self, amount: float, from_currency: str = "USD", 
                to_currency: str = "KES") -> float:
        """
        Convert amount between currencies
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount
        
        rate = self.get_exchange_rate(from_currency, to_currency)
        return amount * rate
    
    def usd_to_kes(self, amount_usd: float) -> float:
        """Convert USD to KES"""
        return self.convert(amount_usd, "USD", "KES")
    
    def kes_to_usd(self, amount_kes: float) -> float:
        """Convert KES to USD"""
        return self.convert(amount_kes, "KES", "USD")
    
    def format_currency(self, amount: float, currency: str = "KES") -> str:
        """Format amount with currency symbol"""
        if currency == "KES":
            return f"KES {amount:,.2f}"
        elif currency == "USD":
            return f"${amount:,.2f}"
        return f"{amount:,.2f} {currency}"
