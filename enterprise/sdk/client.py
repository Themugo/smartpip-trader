"""
Python SDK Client

Official Python SDK for SmartPip Trader Enterprise API.
"""

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

import requests


@dataclass
class SmartPipConfig:
    """SDK Configuration"""
    api_key: str
    api_secret: str
    base_url: str = "https://api.smartpip.io/v1"
    timeout: int = 30
    max_retries: int = 3
    organization_id: Optional[str] = None


class SmartPipError(Exception):
    """SDK Error"""
    def __init__(self, message: str, code: str = "", status_code: int = 0):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class SmartPipClient:
    """
    Main SDK client for SmartPip Trader API.
    
    Example usage:
    
    ```python
    from smartpip import SmartPipClient
    
    client = SmartPipClient(
        api_key="your_api_key",
        api_secret="your_api_secret",
        organization_id="org_123"
    )
    
    # List strategies
    strategies = client.strategies.list()
    
    # Create strategy
    strategy = client.strategies.create(
        name="My Strategy",
        type="reversal",
        parameters={"rsi_period": 14}
    )
    
    # Run backtest
    backtest = client.backtests.run(
        strategy_id=strategy["id"],
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
    
    # Get results
    results = client.backtests.get_results(backtest["id"])
    ```
    """
    
    def __init__(self, config: SmartPipConfig):
        self._config = config
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "X-Organization-ID": config.organization_id or "",
        })
        
        # Initialize sub-clients
        self.strategies = StrategyClient(self)
        self.backtests = BacktestClient(self)
        self.reports = ReportClient(self)
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make API request with retry logic"""
        url = f"{self._config.base_url}{endpoint}"
        
        for attempt in range(self._config.max_retries):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=self._config.timeout,
                )
                
                if response.status_code == 429:
                    # Rate limited, wait and retry
                    time.sleep(2 ** attempt)
                    continue
                
                if response.status_code >= 400:
                    raise SmartPipError(
                        message=response.json().get("error", "Request failed"),
                        code=response.json().get("error_code", ""),
                        status_code=response.status_code,
                    )
                
                return response.json()
                
            except requests.exceptions.Timeout:
                if attempt == self._config.max_retries - 1:
                    raise SmartPipError("Request timed out")
            except requests.exceptions.ConnectionError:
                if attempt == self._config.max_retries - 1:
                    raise SmartPipError("Connection failed")
        
        raise SmartPipError("Max retries exceeded")
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request"""
        return self._request("GET", endpoint, params=params)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST request"""
        return self._request("POST", endpoint, data=data)
    
    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """PUT request"""
        return self._request("PUT", endpoint, data=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request"""
        return self._request("DELETE", endpoint)
    
    def stream(
        self,
        endpoint: str,
        callback: callable,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Stream response with callback"""
        url = f"{self._config.base_url}{endpoint}"
        
        with self._session.get(url, params=params, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    callback(data)


class StrategyClient:
    """Client for strategy operations"""
    
    def __init__(self, client: SmartPipClient):
        self._client = client
    
    def list(
        self,
        workspace_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List strategies"""
        params = {"limit": limit, "offset": offset}
        if workspace_id:
            params["workspace_id"] = workspace_id
        if status:
            params["status"] = status
        
        return self._client.get("/strategies", params=params).get("strategies", [])
    
    def get(self, strategy_id: str) -> Dict[str, Any]:
        """Get strategy details"""
        return self._client.get(f"/strategies/{strategy_id}")
    
    def create(
        self,
        name: str,
        type: str,
        parameters: Dict[str, Any],
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new strategy"""
        data = {
            "name": name,
            "type": type,
            "parameters": parameters,
        }
        if workspace_id:
            data["workspace_id"] = workspace_id
        
        return self._client.post("/strategies", data=data)
    
    def update(
        self,
        strategy_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update strategy"""
        return self._client.put(f"/strategies/{strategy_id}", data=updates)
    
    def delete(self, strategy_id: str) -> Dict[str, Any]:
        """Delete strategy"""
        return self._client.delete(f"/strategies/{strategy_id}")
    
    def execute(
        self,
        strategy_id: str,
        market: str,
        amount: float = 10.0,
    ) -> Dict[str, Any]:
        """Execute strategy"""
        return self._client.post(f"/strategies/{strategy_id}/execute", data={
            "market": market,
            "amount": amount,
        })
    
    def backtest(
        self,
        strategy_id: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Run backtest on strategy"""
        return self._client.post(f"/strategies/{strategy_id}/backtest", data={
            "start_date": start_date,
            "end_date": end_date,
        })


class BacktestClient:
    """Client for backtest operations"""
    
    def __init__(self, client: SmartPipClient):
        self._client = client
    
    def list(
        self,
        strategy_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List backtests"""
        params = {"limit": limit}
        if strategy_id:
            params["strategy_id"] = strategy_id
        
        return self._client.get("/backtests", params=params).get("backtests", [])
    
    def get(self, backtest_id: str) -> Dict[str, Any]:
        """Get backtest details"""
        return self._client.get(f"/backtests/{backtest_id}")
    
    def get_results(self, backtest_id: str) -> Dict[str, Any]:
        """Get backtest results"""
        return self._client.get(f"/backtests/{backtest_id}/results")
    
    def cancel(self, backtest_id: str) -> Dict[str, Any]:
        """Cancel running backtest"""
        return self._client.post(f"/backtests/{backtest_id}/cancel")


class ReportClient:
    """Client for report operations"""
    
    def __init__(self, client: SmartPipClient):
        self._client = client
    
    def list(
        self,
        report_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List reports"""
        params = {"limit": limit}
        if report_type:
            params["type"] = report_type
        
        return self._client.get("/reports", params=params).get("reports", [])
    
    def generate(
        self,
        report_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        format: str = "pdf",
    ) -> Dict[str, Any]:
        """Generate a report"""
        data = {
            "type": report_type,
            "format": format,
        }
        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date
        
        return self._client.post("/reports", data=data)
    
    def get(self, report_id: str) -> Dict[str, Any]:
        """Get report details"""
        return self._client.get(f"/reports/{report_id}")
    
    def download(self, report_id: str, format: Optional[str] = None) -> bytes:
        """Download report file"""
        endpoint = f"/reports/{report_id}/download"
        if format:
            endpoint += f"?format={format}"
        
        response = self._client._session.get(
            f"{self._client._config.base_url}{endpoint}",
            headers=self._client._session.headers,
        )
        return response.content
