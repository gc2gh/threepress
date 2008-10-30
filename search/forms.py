from django import forms

from xapian import Stem

langs = Stem.get_available_languages()
choices = []
for l in langs.split(' '):
    choices.append( (l, l.capitalize() ) )

class EpubSearchForm(forms.Form):
    q = forms.CharField()
    language = forms.ChoiceField(choices=choices,
                                 initial='english',
                                 widget=forms.RadioSelect)
