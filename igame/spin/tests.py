from decimal import Decimal
import unittest
from unittest import skip

from django.contrib.auth.models import User
from django.test import TestCase

from .bonus import create_default_bonus_types, give_user_a_bonus
from .deduct import deduct_real_money__user_lost_game, get_wallet_for_game, negify
from .deposit import deposit_real_money
from .game import play_game, reward_user
from .models import (
    BalanceTooLowError,
    BonusTransaction,
    BonusType,
    DepositTransaction,
    Game,
    SpinGameTransaction,
    Transaction,
    Wallet,
)
from .wagering import MoneySpentForWagering, transfer_eligible_bonuses_to_real_money_wallet
from redis.fake_redis import FakeReadis, fake_redis


class TestDepositRealMoneyFunction(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test-user')

    def test_correct_data_is_saved_to_db_after_money_deposit(self):
        deposit_amount = Decimal(10)
        deposit_real_money(self.user, deposit_amount)

        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(DepositTransaction.objects.count(), 1)

    def test_transaction_has_correct_balance_after_money_deposit(self):
        deposit_amount = Decimal(10)
        deposit_real_money(self.user, deposit_amount)

        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance,
            deposit_amount
        )


class TestDecudtRealMoneyFunctionBecauseUserLostFunction(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test-user')
        self.real_moeny_wallet = Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY)
        self.beginning_wallet_balance = Decimal(10)
        deposit_real_money(self.user, self.beginning_wallet_balance)

    def test_correct_data_is_saved_to_db_after_money_deduction(self):
        deduction_amount = Decimal(2)
        deduct_real_money__user_lost_game(self.user, deduction_amount)

        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(
            Transaction.objects.count(),
            2 # deposit money transaction + deduct money transaction
        )
        self.assertEqual(SpinGameTransaction.objects.count(), 1)
        self.assertEqual(Game.objects.count(), 1)

    def test_after_money_is_deducted_real_money_wallet_has_correct_balance__1(self):
        """
        user has 1 real money wallet, no other wallets
        this wallet has more money in it than the deduction amount (has enough money in it)
        """
        prev_num_transactions = Transaction.objects.count()
        deduct_amount = Decimal(5)
        deduct_real_money__user_lost_game(self.user, deduct_amount)

        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance,
            self.beginning_wallet_balance-deduct_amount
        )
        self.assertEqual(Transaction.objects.count(), prev_num_transactions+1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(SpinGameTransaction.objects.count(), 1)


    def test_after_money_is_deducted_real_money_wallet_has_correct_balance__2(self):
        """
        user has 1 real money wallet, no other wallets
        this wallet doesn't have enough money in it
        """
        prev_num_transactions = Transaction.objects.count()
        deduct_amount = Decimal(15)
        initial_balance = Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance

        with self.assertRaises(BalanceTooLowError):
            deduct_real_money__user_lost_game(self.user, deduct_amount)
        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance,
            initial_balance
        )
        self.assertEqual(Transaction.objects.count(), prev_num_transactions)
        self.assertEqual(Game.objects.count(), 0)
        self.assertEqual(SpinGameTransaction.objects.count(), 0)

    def test_after_money_is_deducted_wallets_have_correct_balance__1(self):
        """
        user has 1 real money wallet and 1 bonus wallet
        real money wallet has no money in it
        """
        self.real_moeny_wallet.current_balance = 0
        self.real_moeny_wallet.save()

        create_default_bonus_types()
        bonus_amount = Decimal(10)
        bonus_type = BonusType.objects.get(event=BonusType.LOGIN)
        give_user_a_bonus(self.user, bonus_type, bonus_amount)

        prev_num_transactions = Transaction.objects.count()
        deduct_amount = Decimal(4)
        deduct_real_money__user_lost_game(self.user, deduct_amount)

        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance,
            0
        )
        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.BONUS).current_balance,
            bonus_amount-deduct_amount
        )
        self.assertEqual(Transaction.objects.count(), prev_num_transactions+1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(SpinGameTransaction.objects.count(), 1)

    def test_after_money_is_deducted_wallets_have_correct_balance__2(self):
        """
        user has 1 real money wallet and 1 bonus wallet
        real money wallet doesn't have enough money in it
        payment is charged against the bonus wallet
        """
        create_default_bonus_types()
        bonus_amount = Decimal(15)
        bonus_type = BonusType.objects.get(event=BonusType.LOGIN)
        give_user_a_bonus(self.user, bonus_type, bonus_amount)

        prev_num_transactions = Transaction.objects.count()
        deduct_amount = Decimal(14)
        deduct_real_money__user_lost_game(self.user, deduct_amount)

        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance,
            self.beginning_wallet_balance
        )
        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.BONUS).current_balance,
            bonus_amount-deduct_amount
        )
        self.assertEqual(Transaction.objects.count(), prev_num_transactions+1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(SpinGameTransaction.objects.count(), 1)

    def test_after_money_is_deducted_wallets_have_correct_balance__3(self):
        """
        user has 1 real money wallet and 2 bonus wallets
        real money wallet doesn't have enough money in it
        first bonus wallet has enough money in it, so it gets charged
        second bonus wallet doesn't get charged
        """
        create_default_bonus_types()
        bonus_amount = Decimal(15)
        give_user_a_bonus(self.user, BonusType.objects.get(event=BonusType.LOGIN), bonus_amount)
        give_user_a_bonus(self.user, BonusType.objects.get(event=BonusType.REAL_MONEY_DEPOSIT), bonus_amount)

        prev_num_transactions = Transaction.objects.count()
        deduct_amount = Decimal(14)
        deduct_real_money__user_lost_game(self.user, deduct_amount)

        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance,
            self.beginning_wallet_balance
        )
        self.assertEqual(
            Wallet.objects.filter(user=self.user, money_type=Wallet.BONUS).first().current_balance,
            bonus_amount-deduct_amount
        )
        self.assertEqual(
            Wallet.objects.filter(user=self.user, money_type=Wallet.BONUS).last().current_balance,
            bonus_amount
        )
        self.assertEqual(Transaction.objects.count(), prev_num_transactions+1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(SpinGameTransaction.objects.count(), 1)

    def test_after_money_is_deducted_wallets_have_correct_balance__4(self):
        """
        user has 1 real money wallet and 2 bonus wallets
        real money wallet doesn't have enough money in it
        first bonus wallet doesn't have enough money in it
        second bonus wallet gets charged
        """
        create_default_bonus_types()
        bonus_amount = Decimal(23)
        give_user_a_bonus(self.user, BonusType.objects.get(event=BonusType.LOGIN), bonus_amount)
        give_user_a_bonus(self.user, BonusType.objects.get(event=BonusType.REAL_MONEY_DEPOSIT), bonus_amount+1)

        prev_num_transactions = Transaction.objects.count()
        deduct_amount = Decimal(24)
        deduct_real_money__user_lost_game(self.user, deduct_amount)

        self.assertEqual(
            Wallet.objects.get(user=self.user, money_type=Wallet.REAL_MONEY).current_balance,
            self.beginning_wallet_balance
        )
        self.assertEqual(
            Wallet.objects.filter(user=self.user, money_type=Wallet.BONUS).first().current_balance,
            bonus_amount
        )
        self.assertEqual(
            Wallet.objects.filter(user=self.user, money_type=Wallet.BONUS).last().current_balance,
            0
        )
        self.assertEqual(Transaction.objects.count(), prev_num_transactions+1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(SpinGameTransaction.objects.count(), 1)


class GiveUserBonusFunction(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test-user')
        create_default_bonus_types()
        self.login_bonus_type = BonusType.objects.get(event=BonusType.LOGIN)
        self.money_deposit_bonus_type = BonusType.objects.get(event=BonusType.REAL_MONEY_DEPOSIT)

    def test_correct_data_is_saved_to_db__user_gets_login_bonus(self):
        bonus_amount = Decimal(10)
        give_user_a_bonus(self.user, BonusType.objects.get(event=BonusType.LOGIN), bonus_amount)

        self.assertEqual(BonusTransaction.objects.count(), 1)
        self.assertEqual(Wallet.objects.count(), 2)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(
            Wallet.objects.get(money_type=Wallet.BONUS).current_balance, bonus_amount
        )

    def test_correct_data_is_saved_to_db__user_gets_money_deposit_bonus(self):
        bonus_amount = Decimal(10)
        give_user_a_bonus(self.user, BonusType.objects.get(event=BonusType.REAL_MONEY_DEPOSIT), bonus_amount)

        self.assertEqual(BonusTransaction.objects.count(), 1)
        self.assertEqual(Wallet.objects.count(), 2)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(
            Wallet.objects.get(money_type=Wallet.BONUS).current_balance, bonus_amount
        )


class RewardUser(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test-user')

    def test_user_wins_correct_data_saved_in_db_when_money_is_rewarded_to_real_money_wallet(self):
        wallet = Wallet.objects.get(money_type=Wallet.REAL_MONEY, user=self.user)
        deposit_real_money(self.user, Decimal(10))
        wallet.refresh_from_db()
        prev_balance = wallet.current_balance

        bet_amount = Decimal(2)
        reward_user(self.user, bet_amount)
        wallet_to_be_rewarded = get_wallet_for_game(self.user, bet_amount)

        self.assertEqual(
            Wallet.objects.get(id=wallet_to_be_rewarded.id).current_balance,
            prev_balance+bet_amount
        )
        self.assertEqual(SpinGameTransaction.objects.count(), 1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 2) # 1 for money deposit 1 for reward

    def test_user_wins_and_money_is_rewarded_to_bonus_wallet(self):
        create_default_bonus_types()
        give_user_a_bonus(self.user, BonusType.objects.get(event=BonusType.LOGIN), Decimal(10))
        wallet = Wallet.objects.get(money_type=Wallet.BONUS)
        prev_balance = wallet.current_balance

        bet_amount = Decimal(2)
        reward_user(self.user, bet_amount)
        wallet_to_be_rewarded = get_wallet_for_game(self.user, bet_amount)

        self.assertEqual(
            Wallet.objects.get(id=wallet_to_be_rewarded.id).current_balance,
            prev_balance+bet_amount
        )
        self.assertEqual(SpinGameTransaction.objects.count(), 1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 2) # 1 for money deposit 1 for reward


class TestDepositRealMoney(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test-user')

    def test_real_money_added_to_correct_wallet_and_correct_data_saved_to_db(self):
        deposit_amount = Decimal(10)
        deposit_real_money(self.user, deposit_amount)

        self.assertEqual(
            Wallet.objects.get(money_type=Wallet.REAL_MONEY, user=self.user).current_balance,
            deposit_amount
        )
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(DepositTransaction.objects.count(), 1)


class TestUserLogin(TestCase):

    def test_user_gets_empty_real_money_wallet_after_its_created(self):
        pass



class TestRedisFakerClass(unittest.TestCase):

    def setUp(self):
        self.redis = FakeReadis()

    def tearDown(self):
        self.redis.storage = dict()

    def test_set_and_get_two_keys(self):
        self.redis.set('a', 10)
        self.redis.set('b', 20)

        self.assertEqual(self.redis.get('a'), 10)
        self.assertEqual(self.redis.get('b'), 20)

    def test_increment_and_decrement_value(self):
        self.redis.set('a', 10)
        self.redis.incr('a', 2)
        self.assertEqual(self.redis.get('a'), 12)

        self.redis.set('b', 3)
        self.redis.decr('b', 3)
        self.assertEqual(self.redis.get('b'), 0)

    def test_reset_fake_redis(self):
        self.redis.set('c', 10)
        self.redis.clear()

        self.assertEqual(len(fake_redis.storage), 0)
        self.assertEqual(len(FakeReadis.storage), 0)


class TestMoneySpentClass(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test-user')
        self.money_spent = MoneySpentForWagering(self.user.pk)

    def tearDown(self):
        self.money_spent.redis.storage = dict()

    def test_key_to_cached_amount_of_money_spent_by_user(self):
        self.assertIn(str(self.user.pk), self.money_spent.key)

    def test_set_user_money_spent_and_get_total(self):
        self.money_spent.set(Decimal(100))

        self.assertEqual(self.money_spent.total, Decimal(100))

    @skip('Not implemented method')
    def test_calculate_total_money_spent_for_user_when_its_not_in_cache(self):
        self.money_spent.calculate_total()

    def test_increase_money_spent_for_user(self):
        self.money_spent.set(Decimal(0))
        self.money_spent.increase(Decimal(10))

        self.assertEqual(self.money_spent.total, Decimal(10))

    def test_decrease_money_spent(self):
        self.money_spent.set(Decimal(10))
        self.money_spent.decrease(Decimal(1))

        self.assertEqual(self.money_spent.total, Decimal(9))

