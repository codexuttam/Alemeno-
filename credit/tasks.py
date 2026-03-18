from celery import shared_task
import pandas as pd
from django.conf import settings
from .models import Customer, Loan
from decimal import Decimal
import os


def _get_candidate(row, keys):
    """Return first non-null value from row for given candidate keys."""
    # Build a map of normalized column name -> actual column name
    cols = {str(c).strip().lower(): c for c in row.index}
    for k in keys:
        # try exact
        if k in row.index:
            v = row.get(k)
            if pd.notna(v):
                return v
        # try normalized
        lk = str(k).strip().lower()
        if lk in cols:
            v = row.get(cols[lk])
            if pd.notna(v):
                return v
    return None


@shared_task(bind=True)
def ingest_excel_task(self, customers_path: str = None, loans_path: str = None):
    """Ingest customers and loans from Excel into DB.

    If paths are not provided, default to <BASE_DIR>/data/*.xlsx
    Returns a summary dict with processed counts.
    """
    if customers_path is None:
        customers_path = os.path.join(settings.BASE_DIR, 'data', 'customer_data.xlsx')
    if loans_path is None:
        loans_path = os.path.join(settings.BASE_DIR, 'data', 'loan_data.xlsx')

    processed = {'customers_created': 0, 'customers_updated': 0, 'customers_skipped': 0,
                 'loans_created': 0, 'loans_updated': 0, 'loans_skipped': 0}

    # Check files exist
    if not os.path.exists(customers_path):
        return {'status': 'no_customers_file', 'path': customers_path}
    if not os.path.exists(loans_path):
        return {'status': 'no_loans_file', 'path': loans_path}

    df_c = pd.read_excel(customers_path)
    for idx, row in df_c.iterrows():
        # tolerate several possible column names for customer id
        cid = _get_candidate(row, ['customer_id', 'customer id', 'customerId', 'id'])
        if cid is None:
            # skip rows without a clear id
            print(f"Skipping customer row {idx}: no id")
            processed['customers_skipped'] += 1
            continue
        try:
            cust_id = int(cid)
        except Exception:
            print(f"Skipping customer row {idx}: invalid id '{cid}'")
            processed['customers_skipped'] += 1
            continue

        try:
            monthly_raw = _get_candidate(row, ['monthly_salary', 'monthly income', 'monthly_income'])
            monthly = Decimal(str(monthly_raw)) if monthly_raw is not None and not pd.isna(monthly_raw) else Decimal(0)
        except Exception:
            monthly = Decimal(0)

        # approved limit: 36 * monthly rounded to nearest lakh
        try:
            lakh = Decimal(100000)
            approved_limit = (monthly * Decimal(36) / lakh).quantize(Decimal('1')) * lakh
        except Exception:
            approved_limit = Decimal(0)

        defaults = {
            'first_name': _get_candidate(row, ['first_name', 'First Name', 'firstname']) or '',
            'last_name': _get_candidate(row, ['last_name', 'Last Name', 'lastname']) or '',
            'phone_number': str(_get_candidate(row, ['phone_number', 'phone no', 'phone'])) if _get_candidate(row, ['phone_number', 'phone no', 'phone']) is not None else '',
            'monthly_salary': monthly,
            'approved_limit': approved_limit,
            'current_debt': Decimal(str(_get_candidate(row, ['current_debt', 'current debt', 'currentdebt']) or 0)),
        }

        obj, created = Customer.objects.update_or_create(id=cust_id, defaults=defaults)
        if created:
            processed['customers_created'] += 1
        else:
            processed['customers_updated'] += 1

    # Loans
    df_l = pd.read_excel(loans_path)
    for idx, row in df_l.iterrows():
        cid_raw = _get_candidate(row, ['customer id', 'customer_id', 'customerId', 'id'])
        if cid_raw is None:
            print(f"Skipping loan row {idx}: no customer id")
            processed['loans_skipped'] += 1
            continue
        try:
            cust_id = int(cid_raw)
        except Exception:
            print(f"Skipping loan row {idx}: invalid customer id '{cid_raw}'")
            processed['loans_skipped'] += 1
            continue

        try:
            customer = Customer.objects.get(id=cust_id)
        except Customer.DoesNotExist:
            print(f"Skipping loan row {idx}: customer {cust_id} not found")
            processed['loans_skipped'] += 1
            continue

        loan_amount = Decimal(str(_get_candidate(row, ['loan amount', 'loan_amount', 'loan_amount ']) or 0))
        tenure = int(_get_candidate(row, ['tenure', 'Tenure']) or 0)
        interest_rate = Decimal(str(_get_candidate(row, ['interest rate', 'interest_rate', 'rate']) or 0))
        emi = Decimal(str(_get_candidate(row, ['monthly repayment', 'monthly_repayment', 'emi']) or 0))
        emis_paid = int(_get_candidate(row, ['EMIs paid on time', 'emis_paid_on_time', 'emis_paid']) or 0)
        start = _get_candidate(row, ['start date', 'start_date'])
        end = _get_candidate(row, ['end date', 'end_date'])
        # generate external id from loan id column if present
        external_id = _get_candidate(row, ['loan id', 'loan_id', 'loanid'])

        defaults = {
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

        obj, created = Loan.objects.update_or_create(external_loan_id=str(external_id) if external_id is not None else None, defaults=defaults)
        if created:
            processed['loans_created'] += 1
        else:
            processed['loans_updated'] += 1

    print(f"Ingestion summary: {processed}")
    return {'status': 'ok', **processed}
