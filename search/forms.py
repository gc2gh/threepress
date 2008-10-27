from django import forms

class EpubSearchForm(forms.Form):
    q = forms.CharField()
