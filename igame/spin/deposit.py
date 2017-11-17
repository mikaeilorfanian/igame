from django.db import transaction as db_transaction
from django.db.models import F

from .models import  DepositTransaction, Transaction, Wallet, user_made_deposit_signal


def deposit_real_money(user, amount):
    with db_transaction.atomic():
        real_money_wallet = Wallet.objects.get(user=user, money_type=Wallet.REAL_MONEY)
        real_money_wallet.current_balance = F('current_balance') + amount
        real_money_wallet.save()
        transaction = Transaction.objects.create(amount=amount, wallet=real_money_wallet)
        DepositTransaction.objects.create(transaction=transaction)
        user_made_deposit_signal.send(sender=None, user=user, deposit_amount=amount)
