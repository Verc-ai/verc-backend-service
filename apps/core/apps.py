from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        """
        Initialize and pre-warm Supabase connections on app startup.

        This prevents cold-start failures on first user request by:
        1. Initializing the Supabase client singleton
        2. Testing storage API connectivity
        3. Warming up connection pools
        """
        # Only run once (Django calls ready() multiple times in some scenarios)
        if not hasattr(self, '_supabase_prewarmed'):
            self._supabase_prewarmed = True

            try:
                from apps.core.services.supabase import get_supabase_client
                from django.conf import settings

                logger.info("🔥 Pre-warming Supabase connections...")

                # Initialize client
                supabase = get_supabase_client()
                if not supabase:
                    logger.warning("⚠️ Supabase client not available - skipping pre-warm")
                    return

                # Test storage API connection to warm up
                config = settings.APP_SETTINGS.supabase
                bucket = config.audio_bucket

                # List bucket to verify connectivity (lightweight operation)
                # This warms up the storage connection pool
                # Note: list() with no args returns root directory listing
                supabase.storage.from_(bucket).list(path="")

                logger.info("✅ Supabase connections pre-warmed successfully")

            except Exception as e:
                # Don't fail app startup if pre-warming fails
                # The retry logic will handle failures during actual requests
                logger.warning(f"⚠️ Failed to pre-warm Supabase connections: {e}")

