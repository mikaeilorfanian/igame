from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db import models, transaction as db_transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal

from .constants import SPIN_APP_SETTINGS as app_settings


class BonusType(models.Model):
    LOGIN = 'login'
    REAL_MONEY_DEPOSIT = 'real_money_deposit'
    EVENT_CHOICES = (
        (LOGIN, 'User Logs In'),
        (REAL_MONEY_DEPOSIT, 'User Deposits Real Money'),
    )

    active = models.BooleanField(default=True)
    event = models.CharField(max_length=50, choices=EVENT_CHOICES, null=False)


@receiver(user_logged_in)
def user_log_in_real_money_bonus(sender, **kwargs):
    bonus_amount = app_settings['LOGIN_BONUS_AMOUNT']

    with db_transaction.atomic():
        wallet_to_be_rewarded = Wallet.objects.get(money_type=Wallet.REAL_MONEY, user=kwargs['user'])
        wallet_to_be_rewarded.current_balance = F('current_balance') + bonus_amount
        wallet_to_be_rewarded.save()
        transaction = Transaction.objects.create(amount=bonus_amount, wallet=wallet_to_be_rewarded)
        bonus_type = BonusType.objects.get(event=BonusType.LOGIN)
        bonus_transaction = BonusTransaction.objects.create(transaction=transaction, bonus_type=bonus_type)


class BalanceTooLowError(Exception):
    pass


class Wallet(models.Model):
    REAL_MONEY = 'real_money'
    BONUS = 'bonus'
    MONEY_TYPE_CHOICES = (
        (REAL_MONEY, 'Real Money Wallet'),
        (BONUS, 'Bonus Wallet'),
    )

    money_type = models.CharField(max_length=50, choices=MONEY_TYPE_CHOICES, null=False)
    user = models.ForeignKey(User, related_name='wallets')
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(0))
    wagering_requirement = models.IntegerField(default=10)

    def __str__(self):
        return 'balance: {}, type: {}'.format(self.current_balance, self.money_type)


class Game(models.Model):
    LOST = 'lost_game'
    WON = 'won_game'
    GAME_OUTCOME_CHOICES = (
        (LOST, 'User Lost'),
        (WON, 'User Won'),
    )

    created_at = models.TimeField(auto_now=True)
    outcome = models.CharField(max_length=20, choices=GAME_OUTCOME_CHOICES, null=False)


class Transaction(models.Model):
    created_at = models.TimeField(auto_now=True)
    amount = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    wallet = models.ForeignKey(Wallet, related_name='transactions')

    def __str__(self):
        return f'{self.amount}, Wallet: type:{self.wallet.money_type}, current_balance: {self.wallet.current_balance}'


class BonusTransaction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, primary_key=True)
    bonus_type = models.ForeignKey(BonusType)


class DepositTransaction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, primary_key=True)


user_made_deposit_signal = Signal(providing_args=['user', 'deposit_amount'])


@receiver(user_made_deposit_signal)
def real_money_deposit_bonus(sender, user, deposit_amount, **kwargs):
    from .bonus import give_user_a_bonus

    if deposit_amount > app_settings['MIN_REAL_MONEY_DEPOSIT_TO_GET_BONUS']:
        bonus_type = BonusType.objects.get(event=BonusType.REAL_MONEY_DEPOSIT)
        give_user_a_bonus(user, bonus_type, app_settings['DEFAULT_MONEY_DEPOSIT_BONUS_AMOUNT'])


class SpinGameTransaction(models.Model):
    game = models.ForeignKey(Game)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)


@receiver(post_save, sender=User)
def create_real_money_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance, money_type=Wallet.REAL_MONEY)
