#!/usr/bin/env python
"""
Create pbx-monitor feature flag in Supabase.

Usage:
    python create-pbx-monitor-flag.py
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.services.supabase import get_supabase_client
from django.conf import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_pbx_monitor_flag():
    """Create pbx-monitor feature flag in Supabase."""

    logger.info("Connecting to Supabase...")
    supabase = get_supabase_client()

    if not supabase:
        logger.error("❌ Failed to connect to Supabase. Check your configuration.")
        return False

    config = settings.APP_SETTINGS.supabase
    table_name = config.feature_flags_table

    logger.info(f"Using table: {table_name}")

    # Check if flag already exists
    try:
        result = supabase.table(table_name).select('*').eq('flag_key', 'pbx-monitor').execute()

        if result.data and len(result.data) > 0:
            existing_flag = result.data[0]
            logger.info(f"✅ Flag 'pbx-monitor' already exists:")
            logger.info(f"   ID: {existing_flag.get('id')}")
            logger.info(f"   Name: {existing_flag.get('name')}")
            logger.info(f"   Enabled: {existing_flag.get('enabled')}")
            logger.info(f"   Description: {existing_flag.get('description')}")
            return True
    except Exception as e:
        logger.error(f"❌ Error checking existing flag: {e}", exc_info=True)
        return False

    # Create new flag
    logger.info("Creating new 'pbx-monitor' feature flag...")

    flag_data = {
        'flag_key': 'pbx-monitor',
        'name': 'PBX Monitor',
        'description': 'Enable Buffalo PBX call monitoring and SPY call recording',
        'enabled': True,
        'metadata': None,
    }

    try:
        result = supabase.table(table_name).insert(flag_data).execute()

        if result.data and len(result.data) > 0:
            created_flag = result.data[0]
            logger.info(f"✅ Successfully created 'pbx-monitor' feature flag!")
            logger.info(f"   ID: {created_flag.get('id')}")
            logger.info(f"   Name: {created_flag.get('name')}")
            logger.info(f"   Enabled: {created_flag.get('enabled')}")
            logger.info(f"   Description: {created_flag.get('description')}")
            return True
        else:
            logger.error("❌ Failed to create flag: No data returned")
            return False
    except Exception as e:
        logger.error(f"❌ Error creating flag: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("PBX Monitor Feature Flag Creator")
    logger.info("=" * 60)

    success = create_pbx_monitor_flag()

    logger.info("=" * 60)
    if success:
        logger.info("✅ Done!")
        sys.exit(0)
    else:
        logger.error("❌ Failed to create feature flag")
        sys.exit(1)
