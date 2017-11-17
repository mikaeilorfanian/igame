from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect

from .deposit import deposit_real_money
from .forms import DepositForm
from .game import play_random_game
from .models import BalanceTooLowError, Wallet


def home(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'home.html', {'form': form})


def dashboard(request):
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            deposit_amount = Decimal(form.cleaned_data['amount'])

            deposit_real_money(request.user, deposit_amount)
            messages.success(request, 'You just deposited {} into your account'.format(deposit_amount))

    deposit_form = DepositForm()
    real_money_wallet = Wallet.objects.get(user=request.user, money_type=Wallet.REAL_MONEY)
    bonus_wallets = Wallet.objects.filter(user=request.user, money_type=Wallet.BONUS).all()
    return render(
        request,
        'dashboard.html',
        {'form': deposit_form, 'real_money_wallet': real_money_wallet, 'bonus_wallets': bonus_wallets}
    )


def play(request):
    try:
        outcome = play_random_game(request.user)
        messages.success(request, 'You {}'.format(outcome))
    except BalanceTooLowError:
        messages.error(request, 'You do not have enough money in any of your wallets! Deposit some money first!')

    return redirect('dashboard')
