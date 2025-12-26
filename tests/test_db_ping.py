#!/usr/bin/env python
"""
DB Ping Test
Simple database connectivity test - runs SELECT 1 query.
"""

import os
import sys
import django
import time

# Setup Django
# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def main():
    """Run DB ping test"""
    print("=" * 60)
    print("  DB PING TEST")
    print("=" * 60)
    print("\nTesting database connectivity with SELECT 1...\n")
    
    try:
        django.setup()
        
        from django.db import connection
        
        print("Connecting to database...")
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        elapsed = time.time() - start_time
        
        if result and result[0] == 1:
            print(f"✓ Database ping successful! (took {elapsed:.3f}s)")
            print(f"  Database: {connection.settings_dict.get('NAME', 'unknown')}")
            print(f"  Host: {connection.settings_dict.get('HOST', 'unknown')}")
            print(f"  Port: {connection.settings_dict.get('PORT', 'unknown')}")
            return 0
        else:
            print(f"✗ Database ping returned unexpected result: {result}")
            return 1
            
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Database ping failed: {e}")
        
        if 'password authentication failed' in error_msg.lower():
            print("\n  Error: Authentication failed - check DB_PASSWORD")
        elif 'could not connect' in error_msg.lower() or 'connection refused' in error_msg.lower():
            print("\n  Error: Connection refused")
            print("  Hint: Make sure Cloud SQL Proxy is running (for local)")
            print("        or Cloud Run has proper Cloud SQL connector configured")
        elif 'timeout' in error_msg.lower():
            print("\n  Error: Connection timeout")
            print("  Hint: Database may be unreachable or firewall blocking connection")
        
        return 1

if __name__ == '__main__':
    sys.exit(main())

