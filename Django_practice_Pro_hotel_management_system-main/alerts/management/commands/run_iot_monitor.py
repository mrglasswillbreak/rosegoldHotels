import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from alerts.runtime import run_monitoring_cycle


class Command(BaseCommand):
    help = "Runs the simulated IoT monitoring worker and dispatches pending HSE notifications."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run a single monitoring cycle and exit.")
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Seconds to wait between cycles when running continuously.",
        )

    def handle(self, *args, **options):
        once = options["once"]
        interval = max(options["interval"], 15)

        if once:
            summary = run_monitoring_cycle(force_refresh=False)
            self.stdout.write(self.style.SUCCESS(f"Monitoring cycle completed: {summary}"))
            return

        self.stdout.write(self.style.SUCCESS(f"IoT monitor running every {interval} seconds. Press Ctrl+C to stop."))
        while True:
            close_old_connections()
            summary = run_monitoring_cycle(force_refresh=False)
            self.stdout.write(f"Monitoring cycle completed: {summary}")
            self.stdout.flush()
            close_old_connections()
            time.sleep(interval)
