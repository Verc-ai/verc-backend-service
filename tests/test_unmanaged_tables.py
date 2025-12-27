#!/usr/bin/env python
"""
Guardrail Test: Ensure all app schema tables are represented in Django models.
Prevents situations where tables exist in DB but don't have corresponding models.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.apps import apps


def test_no_unmanaged_tables_missing_models():
    """
    Ensures all app schema tables are represented in Django models.
    Excludes views and tables that don't need Django models.
    """
    # Tables that don't need Django models
    # Django's built-in tables and test tables are excluded
    EXCLUDED_TABLES = {
        # Django built-in tables (managed by Django framework)
        'django_migrations',
        'auth_group_permissions',
        'auth_user_groups',
        'auth_user_user_permissions',
        # Test tables (typically prefixed with _)
        '_ddl_test',
        # Add any other tables that don't need Django models here
        # Example: 'audit_log', 'reporting_cache'
    }
    
    # Get all tables in the 'app' schema (exclude views)
    with connection.cursor() as cursor:
        # Get regular tables
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'app'
            ORDER BY tablename
        """)
        db_tables = {row[0] for row in cursor.fetchall()}
        
        # Get views to exclude them (views typically don't need Django models)
        cursor.execute("""
            SELECT viewname
            FROM pg_views
            WHERE schemaname = 'app'
            ORDER BY viewname
        """)
        views = {row[0] for row in cursor.fetchall()}
        
        # Get materialized views to exclude them too
        cursor.execute("""
            SELECT matviewname
            FROM pg_matviews
            WHERE schemaname = 'app'
            ORDER BY matviewname
        """)
        materialized_views = {row[0] for row in cursor.fetchall()}
    
    # Remove views from consideration
    all_views = views | materialized_views
    db_tables = db_tables - all_views - EXCLUDED_TABLES
    
    if views:
        print(f"Excluding {len(views)} regular view(s): {sorted(views)}")
    if materialized_views:
        print(f"Excluding {len(materialized_views)} materialized view(s): {sorted(materialized_views)}")
    if EXCLUDED_TABLES:
        print(f"Excluding {len(EXCLUDED_TABLES)} configured table(s): {sorted(EXCLUDED_TABLES)}")
    
    if not db_tables:
        print("⚠️  No tables found in 'app' schema (excluding views and configured exclusions)")
        return
    
    print(f"\nFound {len(db_tables)} tables in 'app' schema: {sorted(db_tables)}")
    
    # Get all Django model db_table names
    django_tables = set()
    for model in apps.get_models():
        if hasattr(model, '_meta') and hasattr(model._meta, 'db_table'):
            db_table = model._meta.db_table
            # Handle schema-prefixed tables (e.g., "app.calls" -> "calls")
            # or just plain table names (e.g., "calls" -> "calls")
            table_name = db_table.split('.')[-1]
            django_tables.add(table_name)
    
    print(f"Found {len(django_tables)} Django models with db_table: {sorted(django_tables)}")
    
    # Find tables that exist in DB but don't have models
    missing_models = db_tables - django_tables
    
    if missing_models:
        print(f"\n❌ FAILED: {len(missing_models)} table(s) in DB without Django models:")
        for table in sorted(missing_models):
            print(f"   - {table}")
        print("\n💡 If any of these tables don't need Django models, add them to EXCLUDED_TABLES")
        assert False, f"Tables without models: {missing_models}"
    else:
        print(f"\n✅ All {len(db_tables)} table(s) in 'app' schema have corresponding Django models")


if __name__ == '__main__':
    test_no_unmanaged_tables_missing_models()

