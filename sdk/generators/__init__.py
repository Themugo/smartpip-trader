"""
SDK Generators
==============

Code generators for projects, strategies, and plugins.
"""

import os
import json
from typing import Dict, Any, Optional


class ProjectGenerator:
    """Generate new SmartPip projects"""
    
    @staticmethod
    def generate(name: str, template: str = "default", **kwargs) -> Dict[str, Any]:
        """Generate a new project"""
        
        structure = {
            "project.json": {
                "name": name,
                "version": "0.1.0",
                "smartpip_version": ">=1.0.0",
            },
            "__init__.py": f'"""{name} package"""\n',
            "strategies/__init__.py": "",
            "plugins/__init__.py": "",
            "models/__init__.py": "",
            "tests/__init__.py": "",
            "config/default.json": json.dumps({
                "api_url": "http://localhost:8000",
                "log_level": "INFO",
            }, indent=2),
            "requirements.txt": "smartpip-sdk>=1.0.0\n",
            "README.md": f"# {name}\n\nA SmartPip trading project.\n",
        }
        
        if template == "basic":
            pass
        elif template == "advanced":
            structure.update({
                "strategies/base.py": "# Base strategy classes\n",
                "plugins/base.py": "# Base plugin classes\n",
                "data/raw/.gitkeep": "",
                "data/processed/.gitkeep": "",
            })
        
        return structure


class StrategyTemplateGenerator:
    """Generate strategy code from templates"""
    
    TEMPLATES = {
        "momentum": '''"""Momentum Strategy"""

from sdk.strategy import Strategy, Signal, OrderSide


class MomentumStrategy(Strategy):
    strategy_id = "{strategy_id}"
    strategy_name = "{strategy_name}"
    
    def on_init(self):
        self.configure({
            "lookback_period": 20,
            "entry_threshold": 0.02,
            "exit_threshold": 0.01,
        })
    
    def on_tick(self, tick, context):
        signals = []
        
        # Calculate momentum
        momentum = self.calculate_momentum(tick)
        
        if momentum > self.get_config("entry_threshold"):
            signals.append(Signal(
                symbol=tick["symbol"],
                side=OrderSide.BUY,
                strength=abs(momentum),
                confidence=0.8
            ))
        
        return signals
    
    def calculate_momentum(self, tick):
        # Implement momentum calculation
        return 0.0
''',
        "mean_reversion": '''"""Mean Reversion Strategy"""

from sdk.strategy import Strategy, Signal, OrderSide


class MeanReversionStrategy(Strategy):
    strategy_id = "{strategy_id}"
    strategy_name = "{strategy_name}"
    
    def on_init(self):
        self.configure({
            "window": 20,
            "std_multiplier": 2.0,
        })
    
    def on_tick(self, tick, context):
        signals = []
        
        # Calculate z-score
        z_score = self.calculate_z_score(tick)
        
        if z_score > self.get_config("std_multiplier"):
            signals.append(Signal(
                symbol=tick["symbol"],
                side=OrderSide.SELL,
                strength=abs(z_score),
                confidence=0.75
            ))
        elif z_score < -self.get_config("std_multiplier"):
            signals.append(Signal(
                symbol=tick["symbol"],
                side=OrderSide.BUY,
                strength=abs(z_score),
                confidence=0.75
            ))
        
        return signals
    
    def calculate_z_score(self, tick):
        # Implement z-score calculation
        return 0.0
''',
    }
    
    @classmethod
    def generate(cls, name: str, template: str = "momentum") -> str:
        """Generate strategy code"""
        template_code = cls.TEMPLATES.get(template, cls.TEMPLATES["momentum"])
        # Replace { } with {{ }} to escape format placeholders
        import re
        # Only escape {strategy_id} and {strategy_name}
        code = template_code.replace("{strategy_id}", name.lower().replace(" ", "_"))
        code = code.replace("{strategy_name}", name)
        return code


class PluginTemplateGenerator:
    """Generate plugin code from templates"""
    
    TEMPLATES = {
        "data_source": '''"""Data Source Plugin"""

from sdk.plugin import Plugin, PluginHook, create_plugin


@create_plugin(
    name="{plugin_name}",
    version="0.1.0",
    hooks=[PluginHook.ON_TICK],
    description="Custom data source"
)
class {class_name}Plugin(Plugin):
    
    def on_init(self):
        self.configure({
            "source_url": "wss://example.com",
            "symbols": ["BTC/USD", "ETH/USD"],
        })
    
    def on_start(self):
        # Connect to data source
        pass
    
    def on_tick(self, tick):
        # Process and forward tick data
        pass
    
    def on_stop(self):
        # Disconnect from data source
        pass
''',
    }
    
    @classmethod
    def generate(cls, name: str, template: str = "data_source") -> str:
        """Generate plugin code"""
        template_code = cls.TEMPLATES.get(template, "")
        class_name = name.replace("-", " ").title().replace(" ", "")
        return template_code.format(
            plugin_name=name,
            class_name=class_name
        )


class ConfigGenerator:
    """Generate configuration files"""
    
    @staticmethod
    def generate_strategy_profile(
        name: str,
        risk_level: str = "medium",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate strategy configuration profile"""
        
        profiles = {
            "conservative": {
                "max_position_size": 0.02,
                "max_daily_loss": 0.02,
                "stop_loss": 0.01,
                "take_profit": 0.02,
            },
            "medium": {
                "max_position_size": 0.05,
                "max_daily_loss": 0.05,
                "stop_loss": 0.02,
                "take_profit": 0.04,
            },
            "aggressive": {
                "max_position_size": 0.10,
                "max_daily_loss": 0.10,
                "stop_loss": 0.03,
                "take_profit": 0.06,
            },
        }
        
        return {
            "name": name,
            "risk_level": risk_level,
            **profiles.get(risk_level, profiles["medium"]),
            **kwargs
        }
    
    @staticmethod
    def generate_risk_config(
        max_position_size: float = 0.1,
        max_daily_loss: float = 0.05,
        max_drawdown: float = 0.15,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate risk configuration"""
        return {
            "limits": {
                "max_position_size": max_position_size,
                "max_daily_loss": max_daily_loss,
                "max_drawdown": max_drawdown,
                "max_leverage": 3.0,
            },
            **kwargs
        }


class TestGenerator:
    """Generate test files"""
    
    @staticmethod
    def generate_strategy_test(strategy_name: str) -> str:
        """Generate strategy test file"""
        return f'''"""Tests for {strategy_name}"""

import pytest
from sdk.testing import test, BacktestRunner


@test("test_strategy_initialization")
def test_initialization():
    """Test strategy initializes correctly"""
    pass


@test("test_strategy_on_tick")
def test_on_tick():
    """Test strategy processes ticks"""
    pass


@test("test_strategy_pnl")
def test_pnl():
    """Test strategy P&L is positive"""
    pass
'''
