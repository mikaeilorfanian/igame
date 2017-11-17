from django.db.models import F, Sum

from .models import BalanceTooLowError, DepositTransaction, Game, SpinGameTransaction, Transaction, Wallet


def deduct_real_money__user_lost_game(user, amount):
    wallet = get_wallet_for_game(user, amount)
    game = Game.objects.create(outcome=Game.LOST)
    deduction_amount = negify(amount)

    wallet.current_balance = F('current_balance') + deduction_amount
    wallet.save()

    transaction = Transaction.objects.create(amount=deduction_amount, wallet=wallet)
    SpinGameTransaction.objects.create(game=game, transaction=transaction)


def negify(number):
    return -1 * number


def get_wallet_for_game(user, bet_amount):
    try:
        return user.wallets.filter(current_balance__gte=bet_amount).order_by('-money_type')[0]
    except IndexError:
        raise BalanceTooLowError
