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
from django.views.generic import DetailView, ListView, TemplateView, UpdateView, View
from pretalx.orga.forms import TrackForm
from pretalx.common.views import CreateOrUpdateView
from django_context_decorator import context
from pretalx.orga.forms import CfTForm
from django.utils.http import url_has_allowed_host_and_scheme
from pretalx.submission.models.track import TrackStates
from pretalx.common.exceptions import TrackError

from pretalx.common.forms import I18nFormSet
from pretalx.common.mixins.views import (
    ActionFromUrl,
    EventPermissionRequired,
    PermissionRequired,
)
from pretalx.submission.models import (
    CfT,
    Track,
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

class TrackList(EventPermissionRequired, ListView):
    template_name = "orga/cft/track_view.html"
    context_object_name = "tracks"
    permission_required = "orga.view_tracks"

    def get_queryset(self):
        return self.request.event.tracks.all()


class TrackDetail(PermissionRequired, ActionFromUrl, CreateOrUpdateView):
    model = Track
    form_class = TrackForm
    template_name = "orga/cft/track_form.html"
    permission_required = "orga.view_track"
    write_permission_required = "orga.edit_track"

    def get_success_url(self) -> str:
        return self.request.event.cfp.urls.tracks

    def get_object(self):
        return self.request.event.tracks.filter(pk=self.kwargs.get("pk")).first()

    def get_permission_object(self):
        return self.get_object() or self.request.event

    def get_form_kwargs(self):
        result = super().get_form_kwargs()
        result["event"] = self.request.event
        return result

    def form_valid(self, form):
        form.instance.event = self.request.event
        result = super().form_valid(form)
        messages.success(self.request, _("The track has been saved."))
        if form.has_changed():
            action = "pretalx.track." + ("update" if self.object else "create")
            form.instance.log_action(action, person=self.request.user, orga=True)
        return result


class TrackStateChange(PermissionRequired, TemplateView):
    permission_required = "orga.change_track_state"
    template_name = "orga/cft/state_change.html"
    TARGETS = {
        "submitted": TrackStates.SUBMITTED,
        "accepted": TrackStates.ACCEPTED,
        "rejected": TrackStates.REJECTED,
        "canceled": TrackStates.CANCELED,
        "blocked": TrackStates.BLOCKED
    }

    @cached_property
    def object(self):
        return get_object_or_404(Track.objects.filter(id=self.kwargs.get("pk")))

    def get_permission_object(self):
        return self.object

    @context
    def track(self):
        return self.object

    @cached_property
    def _target(self) -> str:
        return self.TARGETS[self.request.resolver_match.url_name.split(".")[-1]]

    @context
    def target(self):
        return self._target

    def do(self, force=False):
        method = getattr(self.object, TrackStates.method_names[self._target])
        method(person=self.request.user, force=force)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if self._target == self.object.state:
            messages.info(
                request,
                _(
                    "Somebody else was faster than you: this proposal was already in the state you wanted to change it to."
                ),
            )
        else:
            try:
                self.do()
            except TrackError:
                self.do(force=True)
        url = self.request.GET.get("next")
        if url and url_has_allowed_host_and_scheme(url, allowed_hosts=None):
            return redirect(url)
        return redirect(self.object.orga_urls.base)

    @context
    def next(self):
        return self.request.GET.get("next")


class CfTTextDetail(PermissionRequired, ActionFromUrl, UpdateView):
    form_class = CfTForm
    model = CfT
    template_name = "orga/cft/text.html"
    permission_required = "orga.edit_cft"
    write_permission_required = "orga.edit_cft"

    def get_object(self):
        return self.request.event.cft

    def get_success_url(self) -> str:
        return self.object.urls.text

    @transaction.atomic
    def form_valid(self, form):
        messages.success(self.request, "The CfT update has been saved.")
        form.instance.event = self.request.event
        result = super().form_valid(form)
        if form.has_changed():
            form.instance.log_action(
                "pretalx.cft.update", person=self.request.user, orga=True
            )
        return result