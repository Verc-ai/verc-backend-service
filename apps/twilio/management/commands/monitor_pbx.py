"""
Django management command to run Buffalo PBX monitor.

Usage:
    python manage.py monitor_pbx
"""

from django.core.management.base import BaseCommand
from apps.twilio.pbx_monitor import run_pbx_monitor


class Command(BaseCommand):
    help = 'Monitor Buffalo PBX for call events and track calls'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Buffalo PBX monitor...'))
        self.stdout.write(self.style.WARNING('Press Ctrl+C to stop'))

        try:
            run_pbx_monitor()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nStopping PBX monitor...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            raise
