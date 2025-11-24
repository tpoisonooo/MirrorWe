#!/usr/bin/env python3
"""Test script to verify environment variable configuration loading."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(__file__).parent / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"Loaded environment variables from {dotenv_path}")
else:
    print(f"Warning: .env file not found at {dotenv_path}")

def test_wechat_env_config():
    """Test WeChat environment configuration."""
    print("\n=== Testing WeChat Environment Configuration ===")
    
    # Test WKTeam configuration
    wkteam_vars = [
        'WKTEAM_ACCOUNT',
        'WKTEAM_PASSWORD', 
        'WKTEAM_PROXY',
        'WKTEAM_DIR',
        'WKTEAM_CALLBACK_IP',
        'WKTEAM_CALLBACK_PORT'
    ]
    
    print("\nWKTeam Configuration:")
    for var in wkteam_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET")
    
    # Test Redis configuration
    redis_vars = ['REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD']
    
    print("\nRedis Configuration:")
    for var in redis_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET")
    
    # Test LLM configuration
    llm_vars = ['LLM_REMOTE_TYPE', 'LLM_REMOTE_API_KEY']
    
    print("\nLLM Configuration:")
    for var in llm_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET")
    
    # Test Group configuration
    print("\nGroup Configuration:")
    group_vars = [key for key in os.environ.keys() if key.startswith('GROUP_')]
    if group_vars:
        for var in sorted(group_vars):
            print(f"✓ {var}: {os.getenv(var)}")
    else:
        print("✗ No group configuration found")

def test_import_wechat_env():
    """Test importing the new wechat_env module."""
    print("\n=== Testing wechat_env Import ===")
    try:
        # Import the new module
        sys.path.insert(0, str(Path(__file__).parent))
        from wechat_env import WkteamManager, get_env_or_raise, get_env_with_default
        
        print("✓ Successfully imported wechat_env module")
        
        # Test environment variable helper functions
        print("\nTesting environment variable functions:")
        
        # Test get_env_or_raise (should work for required vars)
        try:
            account = get_env_or_raise('WKTEAM_ACCOUNT')
            print(f"✓ get_env_or_raise('WKTEAM_ACCOUNT'): {account}")
        except Exception as e:
            print(f"✗ get_env_or_raise failed: {e}")
        
        # Test get_env_with_default
        proxy = get_env_with_default('WKTEAM_PROXY', 1)
        print(f"✓ get_env_with_default('WKTEAM_PROXY', 1): {proxy}")
        
        # Test WkteamManager initialization
        try:
            manager = WkteamManager()
            print("✓ WkteamManager initialized successfully")
            print(f"  - Group whitelist loaded: {len(manager.group_whitelist)} groups")
            print(f"  - License path: {manager.license_path}")
            print(f"  - Record path: {manager.record_path}")
        except Exception as e:
            print(f"✗ WkteamManager initialization failed: {e}")
            
    except ImportError as e:
        print(f"✗ Failed to import wechat_env: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

if __name__ == "__main__":
    print("Environment Configuration Test")
    print("=" * 50)
    
    test_wechat_env_config()
    test_import_wechat_env()
    
    print("\n" + "=" * 50)
    print("Test completed!")