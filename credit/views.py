from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer
from django.db.models import Sum
import math
from datetime import date

def round_to_nearest_lakh(value: Decimal) -> int:
    lakh = Decimal(100000)
    return int((value / lakh).quantize(Decimal('1')) * lakh)

def calculate_emi(principal: Decimal, annual_rate: Decimal, months: int) -> float:
    if months <= 0:
        return 0.0
    r = float(annual_rate) / 12.0 / 100.0
    p = float(principal)
    if r == 0:
        return p / months
    emi = p * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return round(emi, 2)

@api_view(['POST'])
def register_view(request):
    data = request.data
    required = ['first_name','last_name','age','monthly_income','phone_number']
    for f in required:
        if f not in data:
            return Response({"error": f"Missing {f}"}, status=status.HTTP_400_BAD_REQUEST)

    monthly_income = Decimal(str(data['monthly_income']))
    approved_limit = round_to_nearest_lakh(monthly_income * 36)
    customer = Customer.objects.create(
        first_name=data['first_name'],
        last_name=data['last_name'],
        age=data['age'],
        monthly_salary=monthly_income,
        phone_number=data['phone_number'],
        approved_limit=approved_limit,
    )
    resp = {
        'customer_id': customer.id,
        'name': f"{customer.first_name} {customer.last_name}",
        'age': customer.age,
        'monthly_income': int(customer.monthly_salary),
        'approved_limit': int(customer.approved_limit),
        'phone_number': customer.phone_number,
    }
    return Response(resp, status=status.HTTP_201_CREATED)

def compute_credit_score(customer: Customer) -> int:
    # get customer's loans
    loans = customer.loans.all()
    total_current_loans = loans.filter(approved=True).aggregate(total=Sum('loan_amount'))['total'] or Decimal(0)
    if total_current_loans > customer.approved_limit:
        return 0

    # On-time repayment ratio
    total_emis = loans.aggregate(total=Sum('tenure'))['total'] or 0
    total_on_time = loans.aggregate(total=Sum('emis_paid_on_time'))['total'] or 0
    ratio = 0.0
    if total_emis:
        ratio = float(total_on_time) / float(total_emis)

    score_on_time = int(ratio * 40)

    # Number of loans taken
    n_loans = loans.count()
    if n_loans <= 1:
        score_loans = 20
    elif n_loans <= 3:
        score_loans = 10
    else:
        score_loans = 0

    # Loan activity in current year
    current_year = date.today().year
    loans_this_year = loans.filter(start_date__year=current_year).count()
    if loans_this_year == 0:
        score_activity = 20
    elif loans_this_year == 1:
        score_activity = 10
    else:
        score_activity = 0

    # Loan approved volume
    total_volume = loans.aggregate(total=Sum('loan_amount'))['total'] or Decimal(0)
    if total_volume <= customer.approved_limit:
        score_volume = 20
    else:
        score_volume = 0

    total_score = score_on_time + score_loans + score_activity + score_volume
    return int(total_score)

@api_view(['POST'])
def check_eligibility_view(request):
    data = request.data
    required = ['customer_id','loan_amount','interest_rate','tenure']
    for f in required:
        if f not in data:
            return Response({"error": f"Missing {f}"}, status=status.HTTP_400_BAD_REQUEST)

    customer = get_object_or_404(Customer, id=data['customer_id'])
    loan_amount = Decimal(str(data['loan_amount']))
    interest_rate = Decimal(str(data['interest_rate']))
    tenure = int(data['tenure'])

    # sum of current EMIs
    current_emis = 0.0
    for loan in customer.loans.filter(approved=True):
        current_emis += float(loan.monthly_repayment)

    if current_emis > float(customer.monthly_salary) * 0.5:
        return Response({
            'customer_id': customer.id,
            'approval': False,
            'interest_rate': float(interest_rate),
            'corrected_interest_rate': None,
            'tenure': tenure,
            'monthly_installment': None,
            'message': 'Current EMIs exceed 50% of monthly salary'
        }, status=status.HTTP_200_OK)

    credit_score = compute_credit_score(customer)

    # Determine allowed slab and corrected interest rate
    approval = False
    corrected_interest_rate = float(interest_rate)
    
    if credit_score > 50:
        approval = True
    elif credit_score > 30: # 30 < score <= 50
        if float(interest_rate) > 12:
            approval = True
        else:
            approval = True # It can be approved but with corrected rate
            corrected_interest_rate = 12.0
    elif credit_score > 10: # 10 < score <= 30
        if float(interest_rate) > 16:
            approval = True
        else:
            approval = True
            corrected_interest_rate = 16.0
    else:
        approval = False

    # Additional check: If sum of all current EMIs > 50% of monthly salary, don't approve
    if current_emis > float(customer.monthly_salary) * 0.5:
        approval = False
        message = 'Current EMIs exceed 50% of monthly salary'
    else:
        message = 'Eligible' if approval else 'Credit score too low'

    # if sum of current loans > approved limit (This is already in compute_credit_score returning 0, but good to be explicit if needed)
    # Actually compute_credit_score handles it by returning 0, which falls into the last else (approval = False)

    monthly_installment = None
    if approval:
        monthly_installment = calculate_emi(loan_amount, Decimal(str(corrected_interest_rate)), tenure)

    resp = {
        'customer_id': customer.id,
        'approval': approval,
        'interest_rate': float(interest_rate),
        'corrected_interest_rate': corrected_interest_rate if corrected_interest_rate != float(interest_rate) else float(interest_rate),
        'tenure': tenure,
        'monthly_installment': monthly_installment,
    }
    return Response(resp, status=status.HTTP_200_OK)

@api_view(['POST'])
def create_loan_view(request):
    data = request.data
    required = ['customer_id','loan_amount','interest_rate','tenure']
    for f in required:
        if f not in data:
            return Response({"error": f"Missing {f}"}, status=status.HTTP_400_BAD_REQUEST)
    # Use eligibility check
    eligibility_resp = check_eligibility_view(request).data
    if not eligibility_resp.get('approval'):
        return Response({'loan_id': None, 'customer_id': data['customer_id'], 'loan_approved': False, 'message': eligibility_resp.get('message','Not eligible'), 'monthly_installment': None}, status=status.HTTP_200_OK)

    customer = get_object_or_404(Customer, id=data['customer_id'])
    loan_amount = Decimal(str(data['loan_amount']))
    interest_rate = Decimal(str(data['interest_rate']))
    tenure = int(data['tenure'])
    # Use corrected interest if present
    corrected = eligibility_resp.get('corrected_interest_rate')
    rate_used = Decimal(str(corrected)) if corrected is not None else interest_rate
    monthly_installment = calculate_emi(loan_amount, rate_used, tenure)

    loan = Loan.objects.create(
        customer=customer,
        loan_amount=loan_amount,
        tenure=tenure,
        interest_rate=rate_used,
        monthly_repayment=Decimal(str(monthly_installment)),
        approved=True
    )

    return Response({'loan_id': loan.id, 'customer_id': customer.id, 'loan_approved': True, 'message': 'Loan approved', 'monthly_installment': monthly_installment}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def view_loan_view(request, loan_id: int):
    loan = get_object_or_404(Loan, id=loan_id)
    customer = loan.customer
    customer_json = {
        'id': customer.id,
        'first_name': customer.first_name,
        'last_name': customer.last_name,
        'phone_number': customer.phone_number,
        'age': customer.age,
    }
    resp = {
        'loan_id': loan.id,
        'customer': customer_json,
        'loan_approved': loan.approved,
        'loan_amount': float(loan.loan_amount),
        'interest_rate': float(loan.interest_rate),
        'monthly_installment': float(loan.monthly_repayment),
        'tenure': loan.tenure,
    }
    return Response(resp, status=status.HTTP_200_OK)

@api_view(['GET'])
def view_loans_by_customer(request, customer_id: int):
    customer = get_object_or_404(Customer, id=customer_id)
    loans = customer.loans.filter(approved=True)
    items = []
    for loan in loans:
        items.append({
            'loan_id': loan.id,
            'loan_amount': float(loan.loan_amount),
            'interest_rate': float(loan.interest_rate),
            'monthly_installment': float(loan.monthly_repayment),
            'repayments_left': loan.emis_left(),
        })
    return Response(items, status=status.HTTP_200_OK)
