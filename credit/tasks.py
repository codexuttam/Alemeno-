from celery import shared_task
import pandas as pd
from django.conf import settings
from .models import Customer, Loan
from decimal import Decimal
import os
from django.utils.dateparse import parse_date

@shared_task
def ingest_excel_task(customers_path: str = '/data/customer_data.xlsx', loans_path: str = '/data/loan_data.xlsx'):
    # Check files exist
    if not os.path.exists(customers_path):
        return {'status': 'no_customers_file', 'path': customers_path}
    if not os.path.exists(loans_path):
        return {'status': 'no_loans_file', 'path': loans_path}

    df_c = pd.read_excel(customers_path)
    for _, row in df_c.iterrows():
        try:
            monthly = Decimal(str(row.get('monthly_salary', 0)))
        except Exception:
            monthly = Decimal(0)
        approved_limit = int((monthly * 36 / Decimal(100000)).quantize(Decimal('1')) * 100000)
        Customer.objects.update_or_create(
            id=int(row.get('customer_id')),
            defaults={
                'first_name': row.get('first_name',''),
                'last_name': row.get('last_name',''),
                'phone_number': str(row.get('phone_number','')),
                'monthly_salary': monthly,
                'approved_limit': approved_limit,
                'current_debt': Decimal(str(row.get('current_debt',0)))
            }
        )

    df_l = pd.read_excel(loans_path)
    for _, row in df_l.iterrows():
        try:
            cust_id = int(row.get('customer id') or row.get('customer_id'))
        except Exception:
            continue
        customer = None
        try:
            customer = Customer.objects.get(id=cust_id)
        except Customer.DoesNotExist:
            continue
        loan_amount = Decimal(str(row.get('loan amount',0)))
        tenure = int(row.get('tenure',0) or 0)
        interest_rate = Decimal(str(row.get('interest rate',0)))
        emi = Decimal(str(row.get('monthly repayment',0) or 0))
        emis_paid = int(row.get('EMIs paid on time',0) or 0)
        start = row.get('start date')
        end = row.get('end date')
        Loan.objects.update_or_create(
            external_loan_id=str(row.get('loan id','')),
            defaults={
                'customer': customer,
                'loan_amount': loan_amount,
                'tenure': tenure,
                'interest_rate': interest_rate,
                'monthly_repayment': emi,
                'emis_paid_on_time': emis_paid,
                'start_date': start if not pd.isna(start) else None,
                'end_date': end if not pd.isna(end) else None,
                'approved': True,
            }
        )

    return {'status': 'ok'}
