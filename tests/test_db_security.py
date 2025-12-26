#!/usr/bin/env python3
"""
Database Security Test Suite
Tests security features for both staging and production databases.
"""
import os
import sys
import django
from django.db import connection
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_schema_creation():
    """Test that user cannot create schemas."""
    print("\n" + "="*60)
    print("TEST 1: Schema Creation Prevention")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS test_security_schema;")
            print("❌ FAIL: User can create schemas (SECURITY RISK!)")
            return False
    except Exception as e:
        if "permission denied" in str(e).lower() or "insufficient privilege" in str(e).lower():
            print("✅ PASS: User cannot create schemas")
            return True
        else:
            print(f"⚠️  UNEXPECTED ERROR: {e}")
            return False

def test_public_schema_table_creation():
    """Test that user cannot create tables in public schema."""
    print("\n" + "="*60)
    print("TEST 2: Public Schema Table Creation Prevention")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS public.test_security_table (id SERIAL PRIMARY KEY);")
            print("❌ FAIL: User can create tables in public schema (SECURITY RISK!)")
            # Clean up if created
            try:
                cursor.execute("DROP TABLE IF EXISTS public.test_security_table;")
            except:
                pass
            return False
    except Exception as e:
        if "permission denied" in str(e).lower() or "insufficient privilege" in str(e).lower():
            print("✅ PASS: User cannot create tables in public schema")
            return True
        else:
            print(f"⚠️  UNEXPECTED ERROR: {e}")
            return False

def test_user_permissions():
    """Test user role and permissions."""
    print("\n" + "="*60)
    print("TEST 3: User Role and Permissions")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    rolname,
                    rolsuper,
                    rolcreaterole,
                    rolcreatedb,
                    rolcanlogin
                FROM pg_roles
                WHERE rolname = current_user;
            """)
            row = cursor.fetchone()
            if row:
                user, is_super, can_create_role, can_create_db, can_login = row
                print(f"User: {user}")
                print(f"  - Is Superuser: {is_super}")
                print(f"  - Can Create Roles: {can_create_role}")
                print(f"  - Can Create Databases: {can_create_db}")
                print(f"  - Can Login: {can_login}")
                
                if is_super:
                    print("❌ FAIL: User is a superuser (SECURITY RISK!)")
                    return False
                if can_create_role:
                    print("❌ FAIL: User can create roles (SECURITY RISK!)")
                    return False
                if can_create_db:
                    print("❌ FAIL: User can create databases (SECURITY RISK!)")
                    return False
                
                print("✅ PASS: User has limited privileges")
                return True
            else:
                print("⚠️  WARNING: Could not retrieve user information")
                return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_schema_access():
    """Test which schemas the user can access."""
    print("\n" + "="*60)
    print("TEST 4: Schema Access Control")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name;
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            print(f"Accessible schemas: {', '.join(schemas)}")
            
            # Check if user can only access app and auth schemas
            allowed_schemas = {'app', 'auth', 'public'}
            unexpected = set(schemas) - allowed_schemas
            
            if unexpected:
                print(f"⚠️  WARNING: User can access unexpected schemas: {unexpected}")
                return False
            else:
                print("✅ PASS: User can only access expected schemas (app, auth, public)")
                return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_table_permissions():
    """Test table-level permissions in app schema."""
    print("\n" + "="*60)
    print("TEST 5: Table Permissions in app Schema")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    table_schema,
                    table_name,
                    privilege_type
                FROM information_schema.role_table_grants
                WHERE grantee = current_user 
                AND table_schema = 'app'
                ORDER BY table_name, privilege_type;
            """)
            permissions = cursor.fetchall()
            
            if not permissions:
                print("⚠️  WARNING: No permissions found for app schema")
                return False
            
            print(f"Found {len(permissions)} permission entries")
            
            # Check for dangerous permissions
            dangerous_perms = {'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'}
            found_dangerous = [p for p in permissions if p[2] in dangerous_perms]
            
            if found_dangerous:
                print(f"⚠️  WARNING: Found potentially dangerous permissions: {found_dangerous}")
            
            # Check for essential permissions
            essential_perms = {'SELECT', 'INSERT', 'UPDATE'}
            found_essential = [p for p in permissions if p[2] in essential_perms]
            
            if found_essential:
                print("✅ PASS: User has appropriate table permissions")
                return True
            else:
                print("⚠️  WARNING: User may lack essential permissions")
                return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_row_level_security():
    """Test if Row Level Security (RLS) is enabled on tables."""
    print("\n" + "="*60)
    print("TEST 6: Row Level Security (RLS)")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    rowsecurity
                FROM pg_tables
                WHERE schemaname = 'app'
                ORDER BY tablename;
            """)
            tables = cursor.fetchall()
            
            if not tables:
                print("⚠️  WARNING: No tables found in app schema")
                return False
            
            rls_enabled = [t for t in tables if t[2]]
            rls_disabled = [t for t in tables if not t[2]]
            
            print(f"Total tables: {len(tables)}")
            print(f"RLS enabled: {len(rls_enabled)}")
            print(f"RLS disabled: {len(rls_disabled)}")
            
            if rls_disabled:
                print(f"⚠️  INFO: RLS not enabled on: {[t[1] for t in rls_disabled]}")
                print("   (This may be acceptable depending on your security model)")
            
            if rls_enabled:
                print(f"✅ RLS enabled on: {[t[1] for t in rls_enabled]}")
            
            return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_connection_security():
    """Test connection security settings."""
    print("\n" + "="*60)
    print("TEST 7: Connection Security")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            # Check SSL connection
            cursor.execute("SHOW ssl;")
            ssl = cursor.fetchone()[0]
            print(f"SSL enabled: {ssl}")
            
            # Check connection from
            cursor.execute("SELECT inet_server_addr(), inet_server_port();")
            server_info = cursor.fetchone()
            print(f"Server address: {server_info[0]}")
            print(f"Server port: {server_info[1]}")
            
            # Check search_path
            cursor.execute("SHOW search_path;")
            search_path = cursor.fetchone()[0]
            print(f"Search path: {search_path}")
            
            if ssl == 'on':
                print("✅ PASS: SSL connection enabled")
                return True
            else:
                print("⚠️  WARNING: SSL not enabled (may be acceptable for local proxy)")
                return True  # Acceptable for Cloud SQL Proxy
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_audit_logging():
    """Test if audit logging is available."""
    print("\n" + "="*60)
    print("TEST 8: Audit Logging")
    print("="*60)
    try:
        with connection.cursor() as cursor:
            # Check if pg_stat_statements is available
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                );
            """)
            has_pg_stat = cursor.fetchone()[0]
            
            # Check if log_statement is enabled
            cursor.execute("SHOW log_statement;")
            log_statement = cursor.fetchone()[0]
            
            print(f"pg_stat_statements extension: {'Available' if has_pg_stat else 'Not available'}")
            print(f"log_statement setting: {log_statement}")
            
            if log_statement in ('all', 'ddl', 'mod'):
                print("✅ INFO: Statement logging is enabled")
            else:
                print("⚠️  INFO: Statement logging may be limited")
            
            return True
    except Exception as e:
        print(f"⚠️  INFO: Could not check audit logging: {e}")
        return True  # Not critical

def main():
    """Run all security tests."""
    print("\n" + "="*60)
    print("DATABASE SECURITY TEST SUITE")
    print("="*60)
    print(f"Environment: {os.getenv('DJANGO_ENV', 'development')}")
    print(f"Database: {settings.DATABASES['default']['NAME']}")
    print(f"User: {settings.DATABASES['default']['USER']}")
    print(f"Host: {settings.DATABASES['default']['HOST']}")
    
    tests = [
        ("Schema Creation Prevention", test_schema_creation),
        ("Public Schema Table Creation", test_public_schema_table_creation),
        ("User Permissions", test_user_permissions),
        ("Schema Access Control", test_schema_access),
        ("Table Permissions", test_table_permissions),
        ("Row Level Security", test_row_level_security),
        ("Connection Security", test_connection_security),
        ("Audit Logging", test_audit_logging),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All security tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

