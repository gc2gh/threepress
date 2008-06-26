from django import newforms as forms
from django_openidauth.regviews import RegistrationFormOpenID

class EpubValidateForm(forms.Form):
    epub = forms.FileField()

