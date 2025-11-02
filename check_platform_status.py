#!/usr/bin/env python3
"""
Quick script to analyze platform failures and suggest which platforms to disable.
Run this after a few job search runs to see which platforms are consistently failing.
"""
import json
import os
from datetime import datetime

FAILURES_FILE = ".platform_failures.json"
THRESHOLD = 5  # Recommend disabling after this many consecutive failures

def analyze_platform_status():
    """Analyze platform failures and provide recommendations."""
    
    if not os.path.exists(FAILURES_FILE):
        print("No platform failure data found. Run the job search agent first.")
        return
    
    with open(FAILURES_FILE, 'r') as f:
        data = json.load(f)
    
    if not data:
        print("No platform failure data available yet.")
        return
    
    print("=" * 70)
    print("Platform Status Analysis")
    print("=" * 70)
    print()
    
    platforms_to_disable = []
    platforms_working = []
    
    for platform, stats in sorted(data.items()):
        consecutive = stats.get('consecutive_failures', 0)
        total = stats.get('total_failures', 0)
        last_failure = stats.get('last_failure', 'Unknown')
        
        status = "❌ FAILING" if consecutive >= THRESHOLD else "⚠️  WARNING" if consecutive > 0 else "✅ WORKING"
        
        print(f"{status} - {platform}:")
        print(f"  Consecutive failures: {consecutive}")
        print(f"  Total failures: {total}")
        print(f"  Last failure: {last_failure}")
        
        if consecutive >= THRESHOLD:
            platforms_to_disable.append(platform)
        elif consecutive == 0:
            platforms_working.append(platform)
        
        print()
    
    print("=" * 70)
    print("Recommendations:")
    print("=" * 70)
    print()
    
    if platforms_to_disable:
        print("⚠️  DISABLE these platforms (they're consistently failing):")
        print()
        for platform in platforms_to_disable:
            env_key = platform.upper().replace(' ', '_') + "_ENABLED"
            print(f"  {env_key}=false")
        print()
        print("Add these to your .env file to save time on future runs.")
        print()
    else:
        print("✅ All platforms are working or have minimal failures.")
        print()
    
    if platforms_working:
        print("✅ These platforms are working well:")
        for platform in platforms_working:
            print(f"  - {platform}")
        print()

if __name__ == "__main__":
    analyze_platform_status()
