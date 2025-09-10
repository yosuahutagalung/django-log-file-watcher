from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import render

from authentication.forms import LoginForm


# Create your views here.
class LoginView(DjangoLoginView):
    template_name = 'authentication/login.html'
    form_class = LoginForm