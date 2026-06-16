import requests
from typing import Optional
import os


class DiscordNotifier:
    """Discord notification handler"""
    
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    def send(self, message: str, title: str = "Notification", **kwargs) -> bool:
        """Send Discord notification"""
        if not self.webhook_url:
            return False
        
        try:
            payload = {
                "content": f"**{title}**\n\n{message}"
            }
            
            response = requests.post(self.webhook_url, json=payload)
            
            return response.status_code == 204
        except Exception as e:
            return False
