from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_scopes import ScopedManager
from i18nfield.fields import I18nCharField, I18nTextField

from pretalx.common.choices import Choices
from pretalx.common.mixins.models import LogMixin
from pretalx.common.urls import EventUrls
from pretalx.common.utils import path_with_hash


class TrackStates(Choices):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    CANCELED = "canceled"
    REJECTED = "rejected"
    BLOCKED = "blocked"

    display_values = {
        SUBMITTED: _("submitted"),
        ACCEPTED: _("accepted"),
        CANCELED: _("canceled"),
        REJECTED: _("rejected"),
        BLOCKED: _("blocked"),
    }
    valid_choices = [(key, value) for key, value in display_values.items()]

    valid_next_states = {
        SUBMITTED: (REJECTED, CANCELED, ACCEPTED),
        REJECTED: (ACCEPTED, SUBMITTED),
        ACCEPTED: tuple(BLOCKED),
        CANCELED: (ACCEPTED, SUBMITTED),
        BLOCKED: tuple(ACCEPTED),
    }

    method_names = {
        SUBMITTED: "make_submitted",
        REJECTED: "reject",
        ACCEPTED: "accept",
        CANCELED: "cancel",
        BLOCKED: "block",
    }


def logo_path(instance, filename):
    return f"community_logo/{path_with_hash(filename)}"


class Track(LogMixin, models.Model):

    event = models.ForeignKey(
        to="event.Event", on_delete=models.PROTECT, related_name="tracks"
    )
    name = I18nCharField(
        max_length=200,
        verbose_name=_("Topic Name"),
    )
    description = I18nTextField(
        verbose_name=_("Topic Description"),
        help_text=_("Make sure to mention how is it related to 𝐅𝐋𝐎𝐒𝐒."),
    )
    community_name = I18nCharField(
        max_length=200,
        verbose_name=_("Community Name"),
        default="",
    )
    community_description = I18nTextField(
        verbose_name=_("Community Description"),
        default="",
    )
    community_logo = models.ImageField(
        null=True,
        blank=True,
        verbose_name=_("Community Logo"),
        upload_to=logo_path,
    )
    notes = models.TextField(
        verbose_name=_("Notes"),
        null=True,
        blank=True,
    )
    room = models.ForeignKey(
        to="schedule.Room",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    state = models.CharField(
        max_length=TrackStates.get_max_length(),
        choices=TrackStates.get_choices(),
        default=TrackStates.SUBMITTED,
        verbose_name=_("Track state"),
    )
    color = models.CharField(
        max_length=7,
        verbose_name=_("Color"),
        validators=[
            RegexValidator(r"#([0-9A-Fa-f]{3}){1,2}"),
        ],
    )
    requires_access_code = models.BooleanField(
        verbose_name=_("Requires access code"),
        help_text=_(
            "This track will only be shown to submitters with a matching access code."
        ),
        default=False,
    )

    objects = ScopedManager(event="event")

    class urls(EventUrls):
        base = edit = "{self.event.cfp.urls.tracks}{self.pk}/"
        delete = "{base}delete"
        prefilled_cfp = "{self.event.cfp.urls.public}?track={self.slug}"

    def __str__(self) -> str:
        return str(self.name)

    @property
    def slug(self) -> str:
        """The slug makes tracks more readable in URLs.

        It consists of the ID, followed by a slugified (and, in lookups,
        optional) form of the track name.
        """
        return f"{self.id}-{slugify(self.name)}"
