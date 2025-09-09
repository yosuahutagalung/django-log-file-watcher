from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from app.models import LogFile


# Create your views here.
class IndexView(LoginRequiredMixin, ListView):
    template_name = 'app/home.html'
    model = LogFile
