from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django import forms
from posts.models import User, Contact


User = get_user_model()


class CreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')


class ContactForm(forms.ModelForm):
    class Meta():
        model = Contact
        fields = ('name', 'email', 'subject', 'body')
