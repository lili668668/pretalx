from django import forms
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from django_scopes.forms import SafeModelChoiceField

from pretalx.cfp.forms.cft import CfTFormMixin
from pretalx.common.mixins.forms import PublicContent, I18nContent
from pretalx.submission.models import Question, Track, SubmissionStates, Submission
from i18nfield.forms import I18nModelForm


class InfoTrackForm(CfTFormMixin, PublicContent, I18nContent, forms.ModelForm, I18nModelForm):
    def __init__(self, event, **kwargs):
        self.event = event
        self.readonly = kwargs.pop("readonly", False)
        initial = kwargs.pop("initial", {}) or {}

        super().__init__(initial=initial, **kwargs)

        self.fields['notes'].help_text = _("Tell us your request.")

        if self.readonly:
            for f in self.fields.values():
                f.disabled = True

    def clean_name(self):
        name = self.cleaned_data["name"]
        qs = self.event.tracks.all()
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if any(str(s.name) == str(name) for s in qs):
            raise forms.ValidationError(_("This track name has existed!"))
        return name

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

    class Meta:
        model = Track
        fields = [
            "name",
            "description",
            "community_name",
            "community_description",
            "community_logo",
            "notes"
        ]
        public_fields = ["name", "description", "community_name", "community_description", "community_logo"]
        i18n_fields = ["name", "description", "community_name", "community_description"]


class SubmissionFilterForm(forms.Form):
    state = forms.MultipleChoiceField(
        choices=SubmissionStates.get_choices(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
    )
    submission_type = forms.MultipleChoiceField(
        required=False, widget=forms.SelectMultiple(attrs={"class": "select2"})
    )
    track = forms.MultipleChoiceField(
        required=False, widget=forms.SelectMultiple(attrs={"class": "select2"})
    )
    tags = forms.MultipleChoiceField(
        required=False, widget=forms.SelectMultiple(attrs={"class": "select2"})
    )
    question = SafeModelChoiceField(queryset=Question.objects.none(), required=False)

    def __init__(self, event, *args, limit_tracks=False, **kwargs):
        self.event = event
        usable_states = kwargs.pop("usable_states", None)
        super().__init__(*args, **kwargs)
        qs = event.submissions
        state_qs = Submission.all_objects.filter(event=event)
        if usable_states:
            qs = qs.filter(state__in=usable_states)
            state_qs = state_qs.filter(state__in=usable_states)
        state_count = {
            d["state"]: d["state__count"]
            for d in state_qs.order_by("state").values("state").annotate(Count("state"))
        }
        sub_types = event.submission_types.all()
        tracks = limit_tracks or event.tracks.all()
        if len(sub_types) > 1:
            type_count = {
                d["submission_type_id"]: d["submission_type_id__count"]
                for d in qs.order_by("submission_type_id")
                .values("submission_type_id")
                .annotate(Count("submission_type_id"))
            }
            self.fields["submission_type"].choices = [
                (
                    sub_type.pk,
                    f"{str(sub_type.name)} ({type_count.get(sub_type.pk, 0)})",
                )
                for sub_type in event.submission_types.all()
            ]
            self.fields["submission_type"].widget.attrs["title"] = _("Session types")
        else:
            self.fields.pop("submission_type", None)
        if len(tracks) > 1:
            track_count = {
                d["track"]: d["track__count"]
                for d in qs.order_by("track").values("track").annotate(Count("track"))
            }
            self.fields["track"].choices = [
                (track.pk, f"{track.name} ({track_count.get(track.pk, 0)})")
                for track in tracks
            ]
            self.fields["track"].widget.attrs["title"] = _("Tracks")
        else:
            self.fields.pop("track", None)

        if not self.event.tags.all().exists():
            self.fields.pop("tags", None)
        else:
            tag_count = event.tags.prefetch_related("submissions").annotate(
                submission_count=Count("submissions", distinct=True)
            )
            tag_count = {tag.tag: tag.submission_count for tag in tag_count}
            self.fields["tags"].choices = [
                (tag.pk, f"{tag.tag} ({tag_count.get(tag.tag, 0)})")
                for tag in self.event.tags.all()
            ]
            self.fields["tags"].widget.attrs["title"] = _("Tags")

        if usable_states:
            usable_states = [
                choice
                for choice in self.fields["state"].choices
                if choice[0] in usable_states
            ]
        else:
            usable_states = self.fields["state"].choices
        self.fields["state"].choices = [
            (choice[0], f"{choice[1].capitalize()} ({state_count.get(choice[0], 0)})")
            for choice in usable_states
        ]
        self.fields["state"].widget.attrs["title"] = _("Proposal states")
        self.fields["question"].queryset = event.questions.all()
