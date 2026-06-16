from typing import Dict, Any, List, Optional
from datetime import datetime
from .email_notifier import EmailNotifier
from .telegram_notifier import TelegramNotifier
from .discord_notifier import DiscordNotifier


class NotificationManager:
    """Manages multiple notification channels"""
    
    def __init__(self):
        self.notifiers = {}
        self.enabled_channels = set()
    
    def add_notifier(self, name: str, notifier):
        """Add a notification channel"""
        self.notifiers[name] = notifier
    
    def enable_channel(self, channel: str):
        """Enable a notification channel"""
        self.enabled_channels.add(channel)
    
    def disable_channel(self, channel: str):
        """Disable a notification channel"""
        self.enabled_channels.discard(channel)
    
    def send(self, message: str, channels: Optional[List[str]] = None, **kwargs) -> Dict[str, bool]:
        """
        Send notification through specified channels
        
        Args:
            message: Message to send
            channels: List of channels to use (if None, uses enabled channels)
            **kwargs: Additional parameters for notifiers
            
        Returns:
            Dictionary of channel -> success status
        """
        if channels is None:
            channels = list(self.enabled_channels)
        
        results = {}
        
        for channel in channels:
            if channel in self.notifiers:
                try:
                    success = self.notifiers[channel].send(message, **kwargs)
                    results[channel] = success
                except Exception as e:
                    results[channel] = False
            else:
                results[channel] = False
        
        return results
    
    def send_trade_notification(self, trade_data: Dict[str, Any]) -> Dict[str, bool]:
        """Send trade execution notification"""
        message = self._format_trade_message(trade_data)
        return self.send(message, title="Trade Executed")
    
    def send_profit_notification(self, profit: float, trade_data: Dict[str, Any]) -> Dict[str, bool]:
        """Send profit/loss notification"""
        emoji = "📈" if profit > 0 else "📉"
        message = f"{emoji} Trade {'Profit' if profit > 0 else 'Loss'}: ${profit:.2f}"
        return self.send(message, title="Trade Result")
    
    def send_alert_notification(self, alert_type: str, message: str) -> Dict[str, bool]:
        """Send alert notification"""
        return self.send(message, title=f"Alert: {alert_type}")
    
    def _format_trade_message(self, trade_data: Dict[str, Any]) -> str:
        """Format trade data into message"""
        return (
            f"Trade Executed\n"
            f"Market: {trade_data.get('market')}\n"
            f"Type: {trade_data.get('type')}\n"
            f"Direction: {trade_data.get('direction')}\n"
            f"Amount: ${trade_data.get('amount')}\n"
            f"Confidence: {trade_data.get('confidence')}%\n"
            f"Entry Price: {trade_data.get('entry_price')}"
        )
