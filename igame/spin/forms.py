from django import forms


class DepositForm(forms.Form):
    amount = forms.DecimalField(label='The amount to deposit')
