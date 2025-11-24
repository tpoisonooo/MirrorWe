#!/usr/bin/env python3
"""
Example usage of the new environment-based WeChat configuration.

This shows how to use the new wechat_env module instead of the old wechat.py
with .toml configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(__file__).parent / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Now import and use the new wechat_env module
from wechat_env import WkteamManager

def main():
    print("=== WeChat Environment Configuration Example ===\n")
    
    # Initialize the manager with environment variables
    try:
        manager = WkteamManager()
        print("✓ WkteamManager initialized successfully!")
        print(f"  - Loaded {len(manager.group_whitelist)} groups from environment")
        print(f"  - License will be saved to: {manager.license_path}")
        print(f"  - Records will be saved to: {manager.record_path}")
        
        # Show loaded groups
        print("\nLoaded groups from environment:")
        for group_id, group_name in manager.group_whitelist.items():
            print(f"  - {group_id}: {group_name}")
        
        print("\n=== Configuration Summary ===")
        print(f"Account: {os.getenv('WKTEAM_ACCOUNT')}")
        print(f"Proxy: {os.getenv('WKTEAM_PROXY')}")
        print(f"Callback IP: {os.getenv('WKTEAM_CALLBACK_IP')}:{os.getenv('WKTEAM_CALLBACK_PORT')}")
        print(f"Redis: {os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}")
        print(f"LLM Type: {os.getenv('LLM_REMOTE_TYPE')}")
        
        # You can now use the manager for login and message handling
        # Example (uncomment to use):
        # manager.login()
        # manager.serve(forward=True)
        
    except Exception as e:
        print(f"✗ Error initializing WkteamManager: {e}")
        print("\nPlease ensure all required environment variables are set:")
        required_vars = [
            'WKTEAM_ACCOUNT',
            'WKTEAM_PASSWORD',
            'WKTEAM_PROXY',
            'WKTEAM_DIR',
            'WKTEAM_CALLBACK_IP',
            'WKTEAM_CALLBACK_PORT',
            'REDIS_HOST',
            'REDIS_PORT',
            'REDIS_PASSWORD',
            'LLM_REMOTE_TYPE',
            'LLM_REMOTE_API_KEY'
        ]
        for var in required_vars:
            value = os.getenv(var)
            status = "✓" if value else "✗"
            print(f"  {status} {var}: {value if value else 'NOT SET'}")

if __name__ == "__main__":
    main()