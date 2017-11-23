from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import F

from .models import BonusWageredTransaction, Transaction, Wallet
from redis.fake_redis import fake_redis

class MoneySpentForWagering:

    redis = fake_redis

    def __init__(self, user_id):
        self.user_id = user_id

    def set(self, amount):
        self.redis.set(self.key, amount)

    def increase(self, amount):
        self.redis.incr(self.key, amount)

    def decrease(self, amount):
        self.redis.decr(self.key, amount)

    @property
    def total(self):
        total = self.redis.get(self.key)

        if total is None:
            total = self.calculate_total()
            self.set(total)

        return total

    @property
    def key(self):
        return 'money_spent:{}'.format(self.user_id)

    def calculate_total(self):
        raise NotImplementedError


def transfer_eligible_bonuses_to_real_money_wallet(user):
    money_spent = MoneySpentForWagering(user.pk)
    real_money_wallet = user.wallets.get(money_type=Wallet.REAL_MONEY)

    with db_transaction.atomic():
        for bonus_wallet in user.wallets.filter(money_type=Wallet.BONUS, current_balance__gt=Decimal(0)).\
                order_by('current_balance').all():
            wallet_cachin_requirement = bonus_wallet.current_balance * bonus_wallet.wagering_requirement

            if money_spent.total < wallet_cachin_requirement:
                break

            real_money_wallet.current_balance = F('current_balance') + bonus_wallet.current_balance
            transaction = Transaction.objects.create(amount=bonus_wallet.current_balance, wallet=real_money_wallet)
            BonusWageredTransaction.objects.create(
                transaction=transaction,
                real_money_wallet=real_money_wallet,
                bonus_wallet=bonus_wallet,
                amount=bonus_wallet.current_balance
            )
            money_spent.decrease(wallet_cachin_requirement)

        real_money_wallet.save()
