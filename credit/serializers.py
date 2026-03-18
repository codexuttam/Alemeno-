from rest_framework import serializers
from .models import Customer, Loan
from .models import IngestionRun

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id','first_name','last_name','age','monthly_salary','approved_limit','phone_number','current_debt']

class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    age = serializers.IntegerField()
    monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    phone_number = serializers.CharField()

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ['id','customer','external_loan_id','loan_amount','tenure','interest_rate','monthly_repayment','emis_paid_on_time','start_date','end_date','approved']


class IngestionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionRun
        fields = ['id','task_id','status','started_at','finished_at','customers_created','customers_updated','customers_skipped','loans_created','loans_updated','loans_skipped','logs']
