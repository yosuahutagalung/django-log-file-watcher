from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView

from app.helpers import tail
from app.models import LogFile


class IndexView(LoginRequiredMixin, ListView):
    template_name = 'app/home.html'
    model = LogFile
    ordering = 'name'


class LogDetailView(LoginRequiredMixin, DetailView):
    template_name = 'app/log-details.html'
    model = LogFile
    pk_url_kwarg = 'log_id'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lines = []
        try:
            lines = tail(self.object.path, 500)
        except FileNotFoundError:
            messages.error(self.request, 'Log file not found')
        except Exception as e:
            messages.error(self.request, f'Error: {e}')

        ctx['lines'] = lines
        return ctx

