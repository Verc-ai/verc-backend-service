#!/usr/bin/env python
"""
Model Audit Script
Compares Django models to actual PostgreSQL schema
"""
import os
import sys
import django

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.core.models import Call, Company, Transcript, TranscriptEvent
from apps.core.models.membership import CompanyMembership
from apps.core.models.system_prompt import SummarySystemPrompt, ScorecardSystemPrompt

def get_table_info(schema, table_name):
    """Get column info, indexes, constraints for a table"""
    with connection.cursor() as cursor:
        # Get columns
        cursor.execute('''
            SELECT 
                column_name, 
                data_type,
                udt_name,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
        ''', [schema, table_name])
        rows = cursor.fetchall()
        columns = {row[0]: {
            'data_type': row[1],
            'udt_name': row[2],
            'nullable': row[3] == 'YES',
            'default': row[4]
        } for row in rows}
        
        # Get indexes (excluding PK)
        try:
            cursor.execute('''
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = %s AND tablename = %s
                AND indexname NOT LIKE %s;
            ''', [schema, table_name, '%_pkey'])
            index_rows = cursor.fetchall()
            indexes = {row[0]: row[1] for row in index_rows if len(row) >= 2}
        except Exception as e:
            print(f"      Warning: Could not get indexes: {e}")
            indexes = {}
        
        # Get unique constraints
        try:
            cursor.execute('''
                SELECT
                    tc.constraint_name,
                    string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) AS columns
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                  AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type = 'UNIQUE'
                  AND tc.table_schema = %s
                  AND tc.table_name = %s
                GROUP BY tc.constraint_name;
            ''', [schema, table_name])
            unique_rows = cursor.fetchall()
            unique_constraints = {row[0]: row[1] for row in unique_rows if len(row) >= 2}
        except Exception as e:
            print(f"      Warning: Could not get unique constraints: {e}")
            unique_constraints = {}
        
        return {
            'columns': columns,
            'indexes': indexes,
            'unique_constraints': unique_constraints
        }

def audit_model(model_class, schema='app'):
    """Audit a single model"""
    model_name = model_class.__name__
    db_table = model_class._meta.db_table
    
    print(f"\n{'='*60}")
    print(f"Auditing {model_name}")
    print(f"{'='*60}")
    
    # Check db_table (Django uses search_path so schema prefix not needed)
    print(f"\n1. db_table:")
    print(f"   Model: {db_table}")
    print(f"   Schema: {schema} (handled by search_path)")
    
    # Get DB info
    try:
        db_info = get_table_info(schema, db_table)
        if not db_info['columns']:
            print(f"   ❌ ERROR: Table '{schema}.{db_table}' not found in database")
            return
    except Exception as e:
        print(f"   ❌ ERROR: Could not get table info: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check managed
    print(f"\n2. managed:")
    is_managed = model_class._meta.managed
    print(f"   Model: {is_managed}")
    if is_managed:
        print(f"   ❌ ISSUE: Should be False (table exists in DB)")
    
    # Check fields
    print(f"\n3. Fields:")
    model_fields = {f.name: f for f in model_class._meta.get_fields() if hasattr(f, 'column')}
    db_columns = db_info['columns']
    
    for field_name, field in model_fields.items():
        db_col_name = getattr(field, 'column', field_name)
        if db_col_name in db_columns:
            db_col = db_columns[db_col_name]
            # Check null/blank
            field_null = field.null if hasattr(field, 'null') else False
            db_null = db_col['nullable']
            if field_null != db_null:
                print(f"   ❌ {db_col_name}: null mismatch (model: {field_null}, DB: {db_null})")
            # Check type (basic check)
            db_type = db_col['udt_name']
            if 'UUIDField' in str(type(field)) and db_type != 'uuid':
                print(f"   ⚠️  {db_col_name}: type check needed (model: UUIDField, DB: {db_type})")
            elif 'TextField' in str(type(field)) and db_type not in ['text', 'varchar']:
                print(f"   ⚠️  {db_col_name}: type check needed (model: TextField, DB: {db_type})")
            elif 'JSONField' in str(type(field)) and db_type != 'jsonb':
                print(f"   ❌ {db_col_name}: type mismatch (model: JSONField, DB: {db_type})")
        else:
            print(f"   ❌ {field_name}: field not found in DB as {db_col_name}")
    
    # Check indexes
    print(f"\n4. Indexes:")
    model_indexes = set()
    for index in model_class._meta.indexes:
        fields = ','.join(sorted(index.fields))
        model_indexes.add(fields)
    
    print(f"   Model indexes: {len(model_class._meta.indexes)}")
    print(f"   DB indexes: {len(db_info['indexes'])}")
    # Note: We're not checking exact match since DB has composite indexes
    
    # Check unique constraints
    print(f"\n5. Unique Constraints:")
    # Map model field names to DB column names
    field_to_column = {}
    for field in model_class._meta.get_fields():
        if hasattr(field, 'column'):
            field_to_column[field.name] = field.column
        elif hasattr(field, 'db_column'):
            field_to_column[field.name] = getattr(field, 'db_column', None) or field.name
    
    model_unique_cols = set()
    # Check Meta.constraints
    for constraint in model_class._meta.constraints:
        if hasattr(constraint, 'fields'):
            # Convert field names to column names
            db_cols = [field_to_column.get(f, f) for f in constraint.fields]
            db_cols_str = ','.join(sorted(db_cols))
            model_unique_cols.add(db_cols_str)
    
    # Check field-level unique=True constraints
    for field in model_class._meta.get_fields():
        if hasattr(field, 'unique') and field.unique:
            col_name = field_to_column.get(field.name, field.name)
            model_unique_cols.add(col_name)
    
    # Normalize DB constraints to sorted column names for comparison
    db_unique_cols_normalized = set()
    db_constraint_map = {}
    for name, columns in db_info['unique_constraints'].items():
        cols_list = [c.strip() for c in columns.split(',')]
        cols_sorted = ','.join(sorted(cols_list))
        db_unique_cols_normalized.add(cols_sorted)
        db_constraint_map[cols_sorted] = (name, columns)
    
    print(f"   Model unique constraints: {len(model_unique_cols)}")
    print(f"   DB unique constraints: {len(db_unique_cols_normalized)}")
    
    # Check DB constraints against model
    for cols_sorted, (name, original_cols) in db_constraint_map.items():
        if cols_sorted not in model_unique_cols:
            print(f"   ❌ Missing in model: {name} ({original_cols})")

# Run audits
models_to_audit = [
    (Company, 'app'),
    (Call, 'app'),
    (Transcript, 'app'),
    (TranscriptEvent, 'app'),
    (CompanyMembership, 'app'),
    (SummarySystemPrompt, 'app'),
    (ScorecardSystemPrompt, 'app'),
]

print("="*60)
print("MODEL AUDIT")
print("="*60)

for model_class, schema in models_to_audit:
    try:
        audit_model(model_class, schema)
    except Exception as e:
        print(f"\n❌ Error auditing {model_class.__name__}: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*60}")
print("Audit complete")
print(f"{'='*60}")

