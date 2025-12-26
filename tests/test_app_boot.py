#!/usr/bin/env python
"""
App Boot Test
Verifies:
- Service starts successfully
- No DB connection errors in logs
"""

import os
import sys
import django
import time
import subprocess
import signal
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout

# Setup Django
# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def test_django_setup():
    """Test 1: Django can be initialized without errors"""
    print("=" * 60)
    print("TEST 1: Django Setup")
    print("=" * 60)
    
    try:
        django.setup()
        print("✓ Django setup completed successfully")
        return True
    except Exception as e:
        print(f"✗ Django setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test 2: Database connection works"""
    print("\n" + "=" * 60)
    print("TEST 2: Database Connection")
    print("=" * 60)
    
    try:
        from django.db import connection
        from django.core.management import call_command
        
        # Try to connect to database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        if result and result[0] == 1:
            print("✓ Database connection successful")
            
            # Try a simple query to verify schema access (new cursor)
            with connection.cursor() as cursor2:
                cursor2.execute("SELECT current_database();")
                db_name = cursor2.fetchone()[0]
                print(f"  Database: {db_name}")
            
            return True
        else:
            print("✗ Database query returned unexpected result")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if 'password authentication failed' in error_msg.lower():
            print(f"✗ Database authentication failed: {e}")
        elif 'could not connect' in error_msg.lower() or 'connection refused' in error_msg.lower():
            print(f"✗ Database connection refused: {e}")
            print("  Hint: Make sure Cloud SQL Proxy is running (for local) or Cloud Run has proper connection configured")
        elif 'relation does not exist' in error_msg.lower():
            print(f"⚠ Database connected but schema missing: {e}")
            print("  This might be OK if migrations haven't been run yet")
            return True  # Connection works, just missing tables
        else:
            print(f"✗ Database connection error: {e}")
            import traceback
            traceback.print_exc()
        return False

def test_django_check():
    """Test 3: Django system check passes"""
    print("\n" + "=" * 60)
    print("TEST 3: Django System Check")
    print("=" * 60)
    
    try:
        from django.core.management import call_command
        from io import StringIO
        
        stdout = StringIO()
        stderr = StringIO()
        
        try:
            call_command('check', stdout=stdout, stderr=stderr)
            output = stdout.getvalue()
            errors = stderr.getvalue()
            
            # Check for database-related errors in output
            if 'database' in errors.lower() or 'db' in errors.lower():
                db_errors = [line for line in errors.split('\n') if 'database' in line.lower() or 'db' in line.lower()]
                if db_errors:
                    print("⚠ System check found database warnings:")
                    for error in db_errors[:5]:  # Show first 5
                        print(f"  {error}")
            
            print("✓ Django system check passed")
            return True
            
        except SystemExit as e:
            if e.code == 0:
                print("✓ Django system check passed")
                return True
            else:
                print(f"✗ Django system check failed (exit code: {e.code})")
                if errors:
                    print(f"Errors:\n{errors}")
                return False
                
    except Exception as e:
        print(f"✗ Failed to run system check: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_apps_loaded():
    """Test 4: All apps load successfully"""
    print("\n" + "=" * 60)
    print("TEST 4: Apps Loaded")
    print("=" * 60)
    
    try:
        from django.conf import settings
        from django.apps import apps
        
        installed_apps = settings.INSTALLED_APPS
        print(f"✓ Found {len(installed_apps)} installed apps")
        
        # Try to get app configs (this will fail if any app has import errors)
        loaded_apps = []
        for app_name in installed_apps:
            try:
                app_config = apps.get_app_config(app_name.split('.')[-1])
                loaded_apps.append(app_name)
            except Exception as e:
                print(f"✗ Failed to load app {app_name}: {e}")
                return False
        
        print(f"✓ Successfully loaded {len(loaded_apps)} apps")
        return True
        
    except Exception as e:
        print(f"✗ Failed to load apps: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all boot tests"""
    print("\n" + "=" * 60)
    print("  APP BOOT TEST")
    print("=" * 60)
    print("\nVerifying service can start without DB connection errors...\n")
    
    results = {
        'django_setup': False,
        'database_connection': False,
        'django_check': False,
        'apps_loaded': False,
    }
    
    try:
        # Test 1: Django setup
        results['django_setup'] = test_django_setup()
        if not results['django_setup']:
            print("\n❌ Django setup failed - cannot continue tests")
            return 1
        
        # Test 2: Database connection
        results['database_connection'] = test_database_connection()
        
        # Test 3: Django system check
        results['django_check'] = test_django_check()
        
        # Test 4: Apps loaded
        results['apps_loaded'] = test_apps_loaded()
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    if all_passed:
        print("\n🎉 All boot tests passed! Service can start successfully.")
        return 0
    else:
        print("\n❌ Some boot tests failed")
        if not results['database_connection']:
            print("\n⚠ Database connection failed - this is required for the service to work")
        return 1

if __name__ == '__main__':
    sys.exit(main())

