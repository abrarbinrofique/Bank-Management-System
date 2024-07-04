from django.contrib import admin

# from transactions.models import Transaction
from .models import Transaction
from .views import transaction_email_address
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'amount', 'balance_after_transaction', 'transaction_type', 'loan_approve']
    
    def save_model(self, request, obj, form, change):
        obj.account.balance += obj.amount
        obj.balance_after_transaction = obj.account.balance
        transaction_email_address('Loan approval','transactions/Loanapprove.html',obj.amount,obj.account.user)
        obj.account.save()
        super().save_model(request, obj, form, change)