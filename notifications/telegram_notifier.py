import requests
from typing import Optional
import os


class TelegramNotifier:
    """Telegram notification handler"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send(self, message: str, title: str = "Notification", **kwargs) -> bool:
        """Send Telegram notification"""
        if not self.bot_token or not self.chat_id:
            return False
        
        try:
            full_message = f"*{title}*\n\n{message}"
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": full_message,
                    "parse_mode": "Markdown"
                }
            )
            
            return response.status_code == 200
        except Exception as e:
            return False
