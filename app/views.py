from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView

from app.models import LogFile


class IndexView(LoginRequiredMixin, ListView):
    template_name = 'app/home.html'
    model = LogFile


class LogDetailView(LoginRequiredMixin, DetailView):
    template_name = 'app/log-details.html'
    model = LogFile
    pk_url_kwarg = 'log_id'

