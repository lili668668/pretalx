from django import forms
from django.conf import settings
from django.db.models import Q
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _
from django_scopes import scopes_disabled
from django_scopes.forms import SafeModelMultipleChoiceField
from i18nfield.forms import I18nModelForm

from pretalx.common.forms.fields import ImageField
from pretalx.common.mixins.forms import I18nHelpText, ReadOnlyFlag
from pretalx.event.models import Event, Organiser, Team, TeamInvite, organiser
from pretalx.orga.forms.widgets import HeaderSelect, MultipleLanguagesWidget
from pretalx.submission.models import Track


class TeamForm(ReadOnlyFlag, I18nHelpText, I18nModelForm):
    def __init__(self, *args, organiser=None, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        self.fields["organiser"].widget = forms.HiddenInput()
        if instance and getattr(instance, "pk", None):
            self.fields.pop("organiser")
        else:
            self.fields["organiser"].initial = organiser
        if instance and instance.pk:
            self.fields["is_reviewer"].help_text = mark_safe(
                f' (<a href="{instance.orga_urls.base}tracks">'
                + str(_("Additional review team settings"))
                + "</a>)"
            )

    class Meta:
        model = Team
        fields = [
            "name",
            "organiser",
            "can_change_teams",
            "can_change_organiser_settings",
            "can_change_event_settings",
            "can_change_submissions",
            "is_reviewer",
        ]


class TeamTrackForm(I18nHelpText, I18nModelForm):
    @scopes_disabled()
    def __init__(self, *args, organiser=None, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        self.fields["limit_tracks"].queryset = Track.objects.filter(
            event__organiser=organiser
        ).order_by("-event__date_from", "name")

    @scopes_disabled()
    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

    class Meta:
        model = Team
        fields = ["force_hide_speaker_names", "limit_tracks"]
        field_classes = {
            "limit_tracks": SafeModelMultipleChoiceField,
        }
        widgets = {"limit_tracks": forms.CheckboxSelectMultiple}


class TeamInviteForm(ReadOnlyFlag, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    class Meta:
        model = TeamInvite
        fields = ("email",)


class OrganiserForm(ReadOnlyFlag, I18nHelpText, I18nModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if kwargs.get("instance"):
            self.fields["slug"].disabled = True

    class Meta:
        model = Organiser
        fields = ("name", "slug")


class EventWizardInitialForm(forms.Form):
    locales = forms.MultipleChoiceField(
        choices=settings.LANGUAGES,
        label=_("Use languages"),
        help_text=_("Choose all languages that your event should be available in."),
        widget=MultipleLanguagesWidget,
    )

    def __init__(self, *args, user=None, organiser=None, **kwargs):
        super().__init__(*args, **kwargs)


class EventWizardBasicsForm(I18nHelpText, I18nModelForm):
    def __init__(self, *args, user=None, locales=None, organiser=None, **kwargs):
        self.locales = locales or []
        super().__init__(*args, **kwargs, locales=locales)
        self.fields["locale"].choices = [
            (a, b) for a, b in settings.LANGUAGES if a in locales
        ]
        self.fields["slug"].help_text = (
            str(
                _(
                    "This is the address your event will be available at. "
                    "Should be short, only contain lowercase letters and numbers, and must be unique. "
                    "We recommend some kind of abbreviation with less than 10 characters that can be easily remembered."
                )
            )
            + " <strong>"
            + str(_("You cannot change the slug later on!"))
            + "</strong>"
        )

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        qs = Event.objects.all()
        if qs.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(
                _(
                    "This short name is already taken, please choose another one (or ask the owner of that event to add you to their team)."
                )
            )

        return slug.lower()

    class Meta:
        model = Event
        fields = ("name", "slug", "timezone", "email", "locale")


class EventWizardTimelineForm(forms.ModelForm):
    cft_deadline = forms.DateTimeField(
        label=_("Call for Partincipates Deadline"),
        required=True,
    )
    cfp_deadline = forms.DateTimeField(
        label=_("Call for Proposal Deadline"),
        required=True,
    )

    def __init__(self, *args, user=None, locales=None, organiser=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cfp_deadline"].widget.attrs["class"] = "datetimepickerfield"
        self.fields["cft_deadline"].widget.attrs["class"] = "datetimepickerfield"

    class Meta:
        model = Event
        fields = ("date_from", "date_to")
        widgets = {
            "date_from": forms.DateInput(attrs={"class": "datepickerfield"}),
            "date_to": forms.DateInput(
                attrs={"class": "datepickerfield", "data-date-after": "#id_date_from"}
            ),
        }


class EventWizardDisplayForm(forms.Form):
    primary_color = forms.CharField(
        max_length=7,
        label=_("Main event colour"),
        help_text=_(
            "Provide a hex value like #00ff00 if you want to style pretalx in your event's colour scheme."
        ),
        required=False,
    )
    display_header_pattern = forms.ChoiceField(
        label=_("Frontpage header pattern"),
        help_text=_(
            'Choose how the frontpage header banner will be styled. Pattern source: <a href="http://www.heropatterns.com/">heropatterns.com</a>, CC BY 4.0.'
        ),
        choices=(
            ("", _("Plain")),
            ("pcb", _("Circuits")),
            ("bubbles", _("Circles")),
            ("signal", _("Signal")),
            ("topo", _("Topography")),
            ("graph", _("Graph Paper")),
        ),
        required=False,
        widget=HeaderSelect,
    )

    def __init__(self, *args, user=None, locales=None, organiser=None, **kwargs):
        super().__init__(*args, **kwargs)
        logo = Event._meta.get_field("logo")
        self.fields["logo"] = ImageField(
            required=False, label=logo.verbose_name, help_text=logo.help_text
        )
        self.fields["primary_color"].widget.attrs["class"] = "colorpickerfield"


class EventWizardCopyForm(forms.Form):
    @staticmethod
    def copy_from_queryset(user):
        return Event.objects.filter(
            Q(
                organiser_id__in=user.teams.filter(can_change_event_settings=True).values_list("organiser", flat=True)
            )
        )

    def __init__(self, *args, user=None, locales=None, organiser=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["copy_from_event"] = forms.ModelChoiceField(
            label=_("Copy configuration from"),
            queryset=EventWizardCopyForm.copy_from_queryset(user),
            widget=forms.RadioSelect,
            empty_label=_("Do not copy"),
            required=False,
        )
