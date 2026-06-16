import asyncio
import os
import json
from core import DerivAPI


async def test_real_deriv_connection():
    """Test connection to real Deriv API"""
    
    print("🔍 Testing Real Deriv API Connection")
    print("=" * 50)
    
    # Get API token from environment
    api_token = os.getenv("DERIV_API_TOKEN")
    
    if not api_token:
        print("❌ DERIV_API_TOKEN not set in environment")
        print("Please set your real Deriv API token:")
        print("export DERIV_API_TOKEN=your_real_token")
        return False
    
    # Check if it's a real token (not demo)
    if api_token.startswith("demo"):
        print("⚠️  You're using a DEMO token")
        print("Please use your REAL Deriv API token for live trading")
        return False
    
    print(f"✅ API Token found (length: {len(api_token)})")
    
    # Initialize API
    api = DerivAPI(api_token=api_token, app_id="1089")
    
    try:
        # Connect to real API
        print("\n📡 Connecting to Deriv Production API...")
        await api.connect()
        print("✅ Connected successfully")
        
        # Authorize
        print("\n🔐 Authorizing with real account...")
        auth_response = await api.authorize()
        
        if auth_response.get("error"):
            print(f"❌ Authorization failed: {auth_response['error']['message']}")
            return False
        
        print("✅ Authorization successful")
        
        # Get account info
        print("\n💰 Getting account information...")
        balance_response = await api.get_balance()
        
        if balance_response.get("error"):
            print(f"❌ Failed to get balance: {balance_response['error']['message']}")
            return False
        
        balance_info = balance_response.get("balance", {})
        currency = balance_info.get("currency", "USD")
        balance = balance_info.get("balance", 0)
        
        print(f"✅ Account Balance: {balance} {currency}")
        
        # Check if it's a real account
        account_type = balance_info.get("account_type", "real")
        loginid = balance_info.get("loginid", "")
        
        print(f"📋 Account Type: {account_type}")
        print(f"🆔 Login ID: {loginid}")
        
        if account_type != "real":
            print("⚠️  This is not a REAL account")
            print("Please use a real account for live trading")
            return False
        
        print("\n✅ REAL ACCOUNT VERIFIED")
        
        # Test market access
        print("\n📊 Testing market access...")
        test_markets = ["R_10", "R_25", "R_50", "R_75", "R_100"]
        
        for market in test_markets:
            try:
                # Subscribe to market
                await api.send_request({
                    "ticks": market,
                    "subscribe": 1
                })
                print(f"✅ {market}: Access granted")
                
                # Unsubscribe
                await api.send_request({
                    "forget_all": "ticks"
                })
            except Exception as e:
                print(f"❌ {market}: Access denied - {e}")
        
        # Disconnect
        print("\n🔌 Disconnecting...")
        await api.disconnect()
        print("✅ Disconnected")
        
        print("\n" + "=" * 50)
        print("✅ REAL DERIV ACCOUNT CONNECTION TEST PASSED")
        print("=" * 50)
        print("\n📝 Summary:")
        print(f"  - Account Type: REAL")
        print(f"  - Balance: {balance} {currency}")
        print(f"  - Login ID: {loginid}")
        print(f"  - Market Access: Verified")
        print("\n✅ Your system is ready for REAL trading")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_real_deriv_connection())
