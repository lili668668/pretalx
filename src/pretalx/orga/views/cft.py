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


class TrackDelete(PermissionRequired, DetailView):
    permission_required = "orga.remove_track"
    template_name = "orga/cfp/track_delete.html"

    def get_object(self):
        return get_object_or_404(self.request.event.tracks, pk=self.kwargs.get("pk"))

    def post(self, request, *args, **kwargs):
        track = self.get_object()

        try:
            track.delete()
            request.event.log_action(
                "pretalx.track.delete", person=self.request.user, orga=True
            )
            messages.success(request, _("The track has been deleted."))
        except ProtectedError:  # TODO: show which/how many submissions are concerned
            messages.error(
                request,
                _("This track is in use in a proposal and cannot be deleted."),
            )
        return redirect(self.request.event.cfp.urls.tracks)