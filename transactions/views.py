from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404,redirect,render
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID
from datetime import datetime
from django.db.models import Sum
from accounts.models import UserBankAccount
from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.template.loader import render_to_string
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferMoneyForm
)
from transactions.models import Transaction


def transaction_email_address(mail_subj,templates,amount,towhom):
    
     message=render_to_string(templates,
      {
        'user':towhom,
        'amount':amount
      })

     to_email=towhom.email                           
    
     send_email=EmailMultiAlternatives(mail_subj,'',to=[to_email])
     send_email.attach_alternative(message,"text/html")
     send_email.send()
    
class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
       
      
       
        transaction_email_address("Bank Deposite info",'transactions/deposite_email.html',amount,self.request.user)

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'


    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial
    

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        self.request.user.account.balance -= form.cleaned_data.get('amount')
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        transaction_email_address("Money withdraw info",'transactions/withdraw_email.html',amount,self.request.user)

        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )
        transaction_email_address("Application for Loan programme",'transactions/loan_email.html',amount,self.request.user)

        return super().form_valid(form)


class TransferMoneyView(View):
    template_name = 'transactions/transfer_money.html'
    model = Transaction 

    def get(self, request):
        form = TransferMoneyForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        
        form = TransferMoneyForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            to_user_id = form.cleaned_data['to_user_id']

            current_user = request.user.account
            try:
                to_user = UserBankAccount.objects.get(account_no=to_user_id)
                print(to_user)
                if current_user.balance <= 0:
                    messages.error(
                        request,
                        'you have not enough balance to transfer'
                    )
                    return render(request, self.template_name, {'form': form, 'title': 'Transfer Money'})

                if amount > current_user.balance:
                    messages.error(
                        request,
                        f'You have {current_user.balance} $ in your account. '
                        'You can not transfer more than your account balance'
                    )
                    return render(request, self.template_name, {'form': form, 'title': 'Transfer Money'})

                current_user.balance -= amount
                transaction_email_address("Transfer money Details",'transactions/sender.html',amount,current_user.user)
                current_user.save()
                to_user.balance += amount
               
                transaction_email_address("Transfer money Details",'transactions/reciever.html',amount,to_user.user)
                to_user.save()

                messages.success(
                    request,
                    f'Transfer of {"{:,.2f}".format(float(amount))}$ successful'
                )

            except UserBankAccount.DoesNotExist:
                messages.error(
                    request, 'User account not found. Please check the account number.')

            return render(request, 'transactions/transfer_money.html', {'form': form, 'title': 'Transfer Money'})
        return render(request, self.template_name, {'form': form, 'title': 'Transfer Money'})

class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset
    


