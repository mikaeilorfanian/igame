from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from spin.bonus import create_default_bonus_types
from spin.constants import SPIN_APP_SETTINGS as app_settings
from spin.deposit import deposit_real_money
from spin.models import Wallet


class Command(BaseCommand):

    def handle(self, *args, **options):
        user = User.objects.create(username='test-user')
        user.set_password('PassworD')
        user.save()
        deposit_real_money(user, app_settings['TEST_USER_BEGINNING_BALANCE'])
        create_default_bonus_types()
