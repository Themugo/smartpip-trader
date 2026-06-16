import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os


class EmailNotifier:
    """Email notification handler"""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = os.getenv("NOTIFICATION_EMAIL")
        self.password = os.getenv("NOTIFICATION_EMAIL_PASSWORD")
    
    def send(self, message: str, title: str = "Notification", **kwargs) -> bool:
        """Send email notification"""
        if not self.email or not self.password:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = self.email
            msg['Subject'] = title
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            return False
