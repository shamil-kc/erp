from django.db import models
from django.contrib.auth.models import User
from customer.models import Party


class PaymentEntry(models.Model):
    PAYMENT_TYPE_CHOICES = (('hand', 'Cash'), ('bank', 'Bank'),
                            ('check', 'Check'),)

    invoice_type = models.CharField(max_length=10,
        choices=(('sale', 'Sale'), ('purchase', 'Purchase')),
        help_text='Type of invoice this payment belongs to')

    invoice_id = models.PositiveIntegerField(
        help_text='ID of related Sale or Purchase invoice')

    payment_type = models.CharField(max_length=10,
                                    choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    charges = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text='Customer or Supplier for this payment')

    cheque_number = models.CharField(max_length=100, null=True, blank=True)
    is_cheque_cleared = models.BooleanField(default=False)
    cheque_cleared_date = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True, help_text='Date of payment')  # <-- New field

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True)

    class Meta:
        verbose_name_plural = "Payment Entries"

    def __str__(self):
        return f"{self.payment_type} payment of {self.amount} for {self.invoice_type} invoice #{self.invoice_id}"


class CashAccount(models.Model):
    # Only one row should exist for the company
    cash_in_hand = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cash_in_bank = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    check_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    type = models.CharField(
        max_length=20, choices=(('main', 'Main'), ('profit', 'Profit')),
        default='main', unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    def deposit(self, amount, account_type):
        if account_type == 'cash_in_hand':
            self.cash_in_hand += amount
        elif account_type == 'cash_in_bank':
            self.cash_in_bank += amount
        elif account_type == 'cash_in_check':
            self.check_cash += amount
        else:
            raise ValueError("Invalid account type")
        self.save()

    def withdraw(self, amount, account_type):
        if account_type == 'cash_in_hand':
            self.cash_in_hand -= amount
        elif account_type == 'cash_in_bank':
            self.cash_in_bank -= amount
        elif account_type == 'cash_in_check':
            self.check_cash -= amount
        else:
            raise ValueError("Invalid account type")
        self.save()

    def transfer(self, from_type, to_type, amount):
        if from_type == to_type:
            raise ValueError("Cannot transfer to the same account type!")
        self.withdraw(amount, from_type)
        self.deposit(amount, to_type)

    def __str__(self):
        return f"CashAccount — Cash: ₹{self.cash_in_hand}, Bank: ₹{self.cash_in_bank}, Check: ₹{self.check_cash}"


class CashAccountTransfer(models.Model):
    FROM_TYPE_CHOICES = (('cash_in_hand', 'Cash in Hand'), ('cash_in_bank', 'Cash in Bank'), ('cash_in_check', 'Check Cash'))
    TO_TYPE_CHOICES = FROM_TYPE_CHOICES

    from_account = models.ForeignKey(CashAccount, related_name='transfers_out', on_delete=models.CASCADE)
    to_account = models.ForeignKey(CashAccount, related_name='transfers_in', on_delete=models.CASCADE)
    from_type = models.CharField(max_length=20, choices=FROM_TYPE_CHOICES)
    to_type = models.CharField(max_length=20, choices=TO_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Cash Account Transfers"

    def __str__(self):
        return f"Transfer ₹{self.amount} from {self.from_account.type}({self.from_type}) to {self.to_account.type}({self.to_type})"
