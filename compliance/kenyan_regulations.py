from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)


class KenyanRegulations:
    """Kenyan market regulations compliance (CMA, CBK, GDPR)"""
    
    def __init__(self):
        self.cma_license = os.getenv("CMA_LICENSE_NUMBER")
        self.cbk_approved = os.getenv("CBK_APPROVED", "false").lower() == "true"
        self.tax_rate = 0.20  # 20% capital gains tax
        self.kyc_required = True
        self.aml_required = True
        self.data_retention_days = 365
        self.max_daily_transaction = 1000000  # 1M KES
        self.max_monthly_transaction = 10000000  # 10M KES
    
    def validate_transaction(self, transaction: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate transaction against Kenyan regulations
        
        Args:
            transaction: Transaction details
            
        Returns:
            (is_valid, reason)
        """
        # Check daily limit
        if transaction.get("amount", 0) > self.max_daily_transaction:
            return False, f"Exceeds daily limit of {self.max_daily_transaction} KES"
        
        # Check KYC
        if self.kyc_required and not self._check_kyc(transaction.get("user_id")):
            return False, "KYC verification required"
        
        # Check AML
        if self.aml_required and self._check_aml(transaction):
            return False, "AML flag triggered"
        
        # Check business hours (if applicable)
        if not self._check_business_hours():
            return False, "Outside business hours"
        
        return True, "Transaction valid"
    
    def _check_kyc(self, user_id: Optional[str]) -> bool:
        """Check if user has completed KYC"""
        # In production, this would check against a KYC database
        # For now, assume all users are KYC verified
        return True
    
    def _check_aml(self, transaction: Dict[str, Any]) -> bool:
        """Check for AML flags"""
        # In production, this would check against AML databases
        # For now, basic checks
        amount = transaction.get("amount", 0)
        
        # Flag large transactions
        if amount > 500000:  # 500K KES
            return True
        
        # Flag frequent transactions
        # (would need transaction history)
        
        return False
    
    def _check_business_hours(self) -> bool:
        """Check if current time is within business hours"""
        # Kenyan market hours: 9:00 AM - 3:00 PM EAT
        current_time = datetime.now().hour
        return 9 <= current_time < 15
    
    def calculate_tax(self, profit: float) -> float:
        """
        Calculate capital gains tax
        
        Args:
            profit: Trading profit
            
        Returns:
            Tax amount
        """
        return profit * self.tax_rate
    
    def generate_tax_report(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate tax report for KRA
        
        Args:
            transactions: List of transactions
            
        Returns:
            Tax report
        """
        total_profit = sum(t.get("profit", 0) for t in transactions if t.get("profit", 0) > 0)
        total_loss = sum(abs(t.get("profit", 0)) for t in transactions if t.get("profit", 0) < 0)
        net_profit = total_profit - total_loss
        tax_amount = self.calculate_tax(net_profit)
        
        return {
            "period": f"{datetime.now().strftime('%Y-%m')}",
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_profit": net_profit,
            "tax_rate": self.tax_rate,
            "tax_amount": tax_amount,
            "net_after_tax": net_profit - tax_amount,
            "transaction_count": len(transactions),
            "generated_at": datetime.now().isoformat()
        }
    
    def log_transaction(self, transaction: Dict[str, Any]):
        """
        Log transaction for audit purposes
        
        Args:
            transaction: Transaction details
        """
        # In production, this would log to a secure database
        log_entry = {
            "transaction_id": transaction.get("id"),
            "user_id": transaction.get("user_id"),
            "amount": transaction.get("amount"),
            "currency": transaction.get("currency", "KES"),
            "timestamp": datetime.now().isoformat(),
            "type": transaction.get("type"),
            "status": transaction.get("status"),
            "compliance_check": "passed"
        }
        
        # Save to audit log
        self._save_audit_log(log_entry)
    
    def _save_audit_log(self, log_entry: Dict[str, Any]):
        """Save audit log entry"""
        # In production, save to secure database
        # For now, log to structured logger
        logger.info(f"AUDIT LOG: {json.dumps(log_entry)}")
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get current compliance status"""
        return {
            "cma_licensed": bool(self.cma_license),
            "cma_license_number": self.cma_license,
            "cbk_approved": self.cbk_approved,
            "kyc_required": self.kyc_required,
            "aml_required": self.aml_required,
            "tax_rate": self.tax_rate,
            "max_daily_transaction": self.max_daily_transaction,
            "max_monthly_transaction": self.max_monthly_transaction,
            "data_retention_days": self.data_retention_days,
            "compliance_status": "compliant" if self.cma_license and self.cbk_approved else "non-compliant"
        }
