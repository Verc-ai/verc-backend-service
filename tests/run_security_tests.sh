#!/bin/bash
# Database Security Test Runner
# Usage: ./run_security_tests.sh [staging|production]

set -e

ENV=${1:-staging}

if [ "$ENV" != "staging" ] && [ "$ENV" != "production" ]; then
    echo "❌ Error: Environment must be 'staging' or 'production'"
    echo "Usage: ./run_security_tests.sh [staging|production]"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "Running Security Tests for: $ENV"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || . venv/bin/activate
else
    echo "⚠️  Warning: Virtual environment not found"
fi

# Set Django environment
export DJANGO_ENV=$ENV

# Try to run tests using Django shell (more reliable)
echo "Running security tests via Django shell..."
echo ""

python manage.py shell << 'PYTHON_EOF'
import sys
from django.db import connection

print("="*60)
print("DATABASE SECURITY TESTS")
print("="*60)
print(f"Database: {connection.settings_dict['NAME']}")
print(f"User: {connection.settings_dict['USER']}")
print(f"Host: {connection.settings_dict['HOST']}")
print()

# Test 1: Schema Creation
print("TEST 1: Schema Creation Prevention")
try:
    with connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS test_security_schema;")
        print("❌ FAIL: User can create schemas")
        sys.exit(1)
except Exception as e:
    if "permission" in str(e).lower() or "privilege" in str(e).lower():
        print("✅ PASS: User cannot create schemas")
    else:
        print(f"⚠️  Error: {e}")

# Test 2: User Permissions
print("\nTEST 2: User Role and Permissions")
try:
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin
            FROM pg_roles WHERE rolname = current_user;
        """)
        row = cursor.fetchone()
        if row:
            user, is_super, can_create_role, can_create_db, can_login = row
            print(f"User: {user}")
            print(f"  Superuser: {is_super}")
            print(f"  Can Create Role: {can_create_role}")
            print(f"  Can Create DB: {can_create_db}")
            print(f"  Can Login: {can_login}")
            
            if not is_super and not can_create_role and not can_create_db:
                print("✅ PASS: User has limited privileges")
            else:
                print("❌ FAIL: User has excessive privileges")
                sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 3: Schema Access
print("\nTEST 3: Schema Access Control")
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
        
        allowed = {'app', 'auth', 'public'}
        unexpected = set(schemas) - allowed
        
        if unexpected:
            print(f"⚠️  WARNING: Unexpected schemas: {unexpected}")
        else:
            print("✅ PASS: User can only access expected schemas")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 4: Table Permissions
print("\nTEST 4: Table Permissions in app Schema")
try:
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = current_user AND table_schema = 'app'
            ORDER BY table_name, privilege_type
            LIMIT 20;
        """)
        perms = cursor.fetchall()
        
        if perms:
            print(f"Found {len(perms)} permission entries")
            dangerous = {'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'}
            found_dangerous = [p for _, p in perms if p in dangerous]
            
            if found_dangerous:
                print(f"⚠️  WARNING: Found dangerous permissions: {set(found_dangerous)}")
            else:
                print("✅ PASS: No dangerous permissions found")
        else:
            print("⚠️  WARNING: No permissions found")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 5: RLS Status
print("\nTEST 5: Row Level Security (RLS)")
try:
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT tablename, rowsecurity
            FROM pg_tables
            WHERE schemaname = 'app'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()
        
        if tables:
            rls_enabled = [t[0] for t in tables if t[1]]
            rls_disabled = [t[0] for t in tables if not t[1]]
            
            print(f"Total tables: {len(tables)}")
            print(f"RLS enabled: {len(rls_enabled)}")
            print(f"RLS disabled: {len(rls_disabled)}")
            
            if rls_enabled:
                print("✅ INFO: RLS is enabled on some tables")
            else:
                print("⚠️  INFO: RLS not enabled (may be acceptable)")
        else:
            print("⚠️  WARNING: No tables found")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
print("✅ All critical tests passed!")
print("="*60)
PYTHON_EOF

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Security tests completed successfully!"
else
    echo ""
    echo "❌ Some security tests failed. Review the output above."
fi

exit $EXIT_CODE

