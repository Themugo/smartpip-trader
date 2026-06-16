import requests
from typing import Dict, Any, Optional
import os
from datetime import datetime
import base64


class MpesaPayment:
    """M-Pesa payment integration for Kenyan market"""
    
    def __init__(self):
        self.consumer_key = os.getenv("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
        self.shortcode = os.getenv("MPESA_SHORTCODE")
        self.passkey = os.getenv("MPESA_PASSKEY")
        self.environment = os.getenv("MPESA_ENVIRONMENT", "sandbox")
        self.access_token = None
        self.token_expiry = None
        
        if self.environment == "production":
            self.base_url = "https://api.safaricom.co.ke"
        else:
            self.base_url = "https://sandbox.safaricom.co.ke"
    
    def get_access_token(self) -> str:
        """Get M-Pesa API access token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.token_expiry = datetime.fromtimestamp(data["expires_in"])
            return self.access_token
        
        raise Exception("Failed to get M-Pesa access token")
    
    def stk_push(self, phone_number: str, amount: float, 
                 account_reference: str = "SmartPip Trading") -> Dict[str, Any]:
        """
        Initiate STK Push for customer payment
        
        Args:
            phone_number: Phone number (format: 254XXXXXXXXX)
            amount: Amount in KES
            account_reference: Reference for the transaction
            
        Returns:
            Response from M-Pesa API
        """
        token = self.get_access_token()
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generate password
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": "https://smartpip.co.ke/mpesa/callback",
            "AccountReference": account_reference,
            "TransactionDesc": "SmartPip Trading Deposit"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        return response.json()
    
    def b2c_payment(self, phone_number: str, amount: float, 
                   remarks: str = "Withdrawal") -> Dict[str, Any]:
        """
        Initiate B2C payment for withdrawals
        
        Args:
            phone_number: Phone number (format: 254XXXXXXXXX)
            amount: Amount in KES
            remarks: Transaction remarks
            
        Returns:
            Response from M-Pesa API
        """
        token = self.get_access_token()
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generate password
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        url = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "InitiatorName": os.getenv("MPESA_INITIATOR_NAME"),
            "SecurityCredential": password,
            "CommandID": "BusinessPayment",
            "Amount": amount,
            "PartyA": self.shortcode,
            "PartyB": phone_number,
            "Remarks": remarks,
            "QueueTimeOutURL": "https://smartpip.co.ke/mpesa/timeout",
            "ResultURL": "https://smartpip.co.ke/mpesa/result",
            "Occasion": "Withdrawal"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        return response.json()
    
    def check_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check transaction status
        
        Args:
            transaction_id: M-Pesa transaction ID
            
        Returns:
            Transaction status
        """
        token = self.get_access_token()
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generate password
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        url = f"{self.base_url}/mpesa/transactionstatus/v1/query"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": transaction_id,
            "OriginatorConversationID": transaction_id,
            "TransactionID": transaction_id
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        return response.json()
    
    def account_balance(self) -> Dict[str, Any]:
        """
        Check M-Pesa account balance
        
        Returns:
            Account balance
        """
        token = self.get_access_token()
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generate password
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        url = f"{self.base_url}/mpesa/accountbalance/v1/query"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "Initiator": os.getenv("MPESA_INITIATOR_NAME"),
            "SecurityCredential": password,
            "CommandID": "AccountBalance",
            "PartyA": self.shortcode,
            "IdentifierType": "4",
            "Remarks": "Check balance",
            "QueueTimeOutURL": "https://smartpip.co.ke/mpesa/timeout",
            "ResultURL": "https://smartpip.co.ke/mpesa/result"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        return response.json()
