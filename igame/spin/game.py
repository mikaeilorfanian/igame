import random

from django.db import transaction
from django.db.models import F

from .constants import SPIN_APP_SETTINGS as app_settings
from .deduct import deduct_real_money__user_lost_game, get_wallet_for_game
from .models import BalanceTooLowError, Game, SpinGameTransaction, Transaction, Wallet


def play_random_game(user):
    outcome = random.choice([Game.LOST, Game.WON])
    play_game(user, outcome, app_settings['DEFAULT_GAME_LOSE_OR_WIN_AMOUNT'])

    return outcome


def play_game(user, outcome, bet_amount):
    with transaction.atomic():
        if outcome == Game.LOST:
            deduct_real_money__user_lost_game(user, bet_amount)
        else:
            reward_user(user, bet_amount)


def reward_user(user, bet_amount):
    game = Game.objects.create(outcome=Game.WON)
    wallet_to_be_rewarded = get_wallet_for_game(user, bet_amount)
    wallet_to_be_rewarded.current_balance = F('current_balance') + bet_amount
    wallet_to_be_rewarded.save()
    transaction = Transaction.objects.create(wallet=wallet_to_be_rewarded, amount=bet_amount)
    SpinGameTransaction.objects.create(game=game, transaction=transaction)
