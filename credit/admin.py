from django.contrib import admin
from .models import Customer, Loan
from .models import IngestionRun

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id','first_name','last_name','phone_number','monthly_salary','approved_limit')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id','customer','loan_amount','tenure','interest_rate','approved')


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ('id','task_id','status','started_at','finished_at','customers_created','loans_created')
    readonly_fields = ('started_at','finished_at')
