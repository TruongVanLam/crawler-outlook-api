#!/usr/bin/env python3
"""
Script test endpoint sync_emails
"""

import requests
import json

def test_sync_emails():
    """Test endpoint sync_emails"""
    
    # URL của API
    base_url = "http://localhost:8000"
    
    print("🚀 Testing sync_emails endpoint...")
    
    # Test 1: Kiểm tra server có chạy không
    try:
        response = requests.get(f"{base_url}/accounts")
        print(f"✅ Server is running: {response.status_code}")
        
        if response.status_code == 200:
            accounts = response.json()
            print(f"📋 Found {accounts.get('total', 0)} accounts")
            
            if accounts.get('total', 0) > 0:
                account_id = accounts['accounts'][0]['id']
                print(f"🔍 Using account_id: {account_id}")
                
                # Test 2: Test sync_emails endpoint
                sync_url = f"{base_url}/mails/sync/?account_id={account_id}&top=5"
                print(f"🔗 Calling: {sync_url}")
                
                response = requests.get(sync_url)
                print(f"📊 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Sync successful: {result}")
                else:
                    print(f"❌ Sync failed: {response.text}")
            else:
                print("❌ No accounts found. Please login first.")
                
        else:
            print(f"❌ Server error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_login():
    """Test login endpoint"""
    
    base_url = "http://localhost:8000"
    
    print("\n🔐 Testing login endpoint...")
    
    try:
        response = requests.get(f"{base_url}/login")
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Login URL: {result.get('login_url', 'Not found')}")
            print(f"📝 Message: {result.get('message', 'Not found')}")
        else:
            print(f"❌ Login failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main function"""
    print("🧪 Testing Mail API endpoints...")
    print("=" * 50)
    
    # Test login
    test_login()
    
    print("-" * 50)
    
    # Test sync_emails
    test_sync_emails()
    
    print("=" * 50)
    print("✅ Testing completed!")

if __name__ == "__main__":
    main() 