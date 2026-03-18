from django.core.management.base import BaseCommand
from credit.tasks import ingest_excel_task

class Command(BaseCommand):
    help = 'Trigger ingestion of customer_data.xlsx and loan_data.xlsx from /data'

    def add_arguments(self, parser):
        parser.add_argument('--customers', type=str, default=None)
        parser.add_argument('--loans', type=str, default=None)

    def handle(self, *args, **options):
        cust = options['customers']
        loans = options['loans']
        # Try to call Celery task
        res = ingest_excel_task.delay(cust, loans)
        self.stdout.write(self.style.SUCCESS(f'Triggered ingestion task id={res.id}'))
