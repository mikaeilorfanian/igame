from django.db import transaction as db_transaction

from .models import BonusTransaction, BonusType, Transaction, Wallet


def create_default_bonus_types():
    BonusType.objects.create(active=True, event=BonusType.LOGIN)
    BonusType.objects.create(active=True, event=BonusType.REAL_MONEY_DEPOSIT)


def give_user_a_bonus(user, bonus_type, amount):
    with db_transaction.atomic():
        new_wallet = Wallet.objects.create(money_type=Wallet.BONUS, user=user, current_balance=amount)
        transaction = Transaction.objects.create(amount=amount, wallet=new_wallet)
        bonus_transaction = BonusTransaction.objects.create(transaction=transaction, bonus_type=bonus_type)
