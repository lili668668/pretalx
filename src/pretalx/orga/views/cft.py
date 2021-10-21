import json

from csp.decorators import csp_update
from django.contrib import messages
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.forms.models import inlineformset_factory
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_context_decorator import context

from pretalx.common.forms import I18nFormSet
from pretalx.common.mixins.views import (
    ActionFromUrl,
    EventPermissionRequired,
    PermissionRequired,
)
from pretalx.submission.models import (
    CfT,
)

class CfTToggle(EventPermissionRequired, TemplateView):
    template_name = "orga/cft/toggle.html"
    permission_required = "orga.edit_cft"

    def post(self, request, *args, **kwargs):
        event = request.event
        cft = request.event.cft
        action = request.POST.get("action")
        if action == "activate":
            if cft.is_start:
                messages.success(request, _("This cft was already started."))
            else:
                cft.is_start = True
                cft.save()
                cft.log_action(
                    "pretalx.cft.activate",
                    person=self.request.user,
                    orga=True,
                    data={},
                )
                messages.success(request, _("This cft is now start."))
        else:  # action == 'deactivate'
            if not cft.is_start:
                messages.success(request, _("This cft was already end."))
            else:
                cft.is_start = False
                cft.save()
                cft.log_action(
                    "pretalx.cft.deactivate",
                    person=self.request.user,
                    orga=True,
                    data={},
                )
                messages.success(request, _("This cft is now end."))
        return redirect(event.orga_urls.base)
