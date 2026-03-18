from django.db import models
from django.utils import timezone

class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    approved_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    current_debt = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.id})"

class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    external_loan_id = models.CharField(max_length=100, blank=True, null=True)
    loan_amount = models.DecimalField(max_digits=14, decimal_places=2)
    tenure = models.IntegerField(help_text='Tenure in months')
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text='Annual interest in percent')
    monthly_repayment = models.DecimalField(max_digits=14, decimal_places=2)
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def emis_left(self):
        # approximate if start_date present
        if not self.start_date:
            return self.tenure
        from django.utils import timezone
        months_passed = (timezone.now().year - self.start_date.year) * 12 + (timezone.now().month - self.start_date.month)
        left = self.tenure - months_passed
        return max(0, left)

    def __str__(self):
        return f"Loan {self.id} for Customer {self.customer_id}"


class IngestionRun(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    task_id = models.CharField(max_length=100, blank=True, null=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')

    customers_created = models.IntegerField(default=0)
    customers_updated = models.IntegerField(default=0)
    customers_skipped = models.IntegerField(default=0)
    loans_created = models.IntegerField(default=0)
    loans_updated = models.IntegerField(default=0)
    loans_skipped = models.IntegerField(default=0)

    logs = models.TextField(blank=True, default='')

    def mark_finished(self, processed: dict, logs: str = ''):
        self.customers_created = processed.get('customers_created', 0)
        self.customers_updated = processed.get('customers_updated', 0)
        self.customers_skipped = processed.get('customers_skipped', 0)
        self.loans_created = processed.get('loans_created', 0)
        self.loans_updated = processed.get('loans_updated', 0)
        self.loans_skipped = processed.get('loans_skipped', 0)
        self.finished_at = timezone.now()
        self.logs = (self.logs or '') + '\n' + logs
        self.status = 'completed'
        self.save()

    def mark_failed(self, logs: str = ''):
        self.finished_at = timezone.now()
        self.logs = (self.logs or '') + '\n' + logs
        self.status = 'failed'
        self.save()
