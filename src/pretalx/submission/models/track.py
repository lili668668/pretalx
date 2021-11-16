from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import pgettext, gettext_lazy as _
from django_scopes import ScopedManager
from i18nfield.fields import I18nCharField, I18nTextField

from pretalx.common.choices import Choices
from pretalx.common.mixins.models import LogMixin
from pretalx.common.urls import EventUrls
from pretalx.common.utils import path_with_hash
from pretalx.common.exceptions import TrackError
from pretalx.cfp.signals import track_state_change


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
        SUBMITTED: "to_submitted",
        REJECTED: "to_rejected",
        ACCEPTED: "to_accepted",
        CANCELED: "to_canceled",
        BLOCKED: "to_blocked",
    }


def logo_path(instance, filename):
    return f"community_logo/{path_with_hash(filename)}"


class Track(LogMixin, models.Model):
    event = models.ForeignKey(
        to="event.Event", on_delete=models.PROTECT, related_name="tracks"
    )
    name = I18nCharField(
        max_length=200,
        verbose_name=_("Track Name"),
    )
    description = I18nTextField(
        verbose_name=_("Track Description"),
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
    requires_access_code = models.BooleanField(
        verbose_name=_("Requires access code"),
        help_text=_(
            "This track will only be shown to submitters with a matching access code."
        ),
        default=False,
    )

    objects = ScopedManager(event="event")

    class urls(EventUrls):
        base = edit = "{self.event.cft.urls.tracks}{self.pk}/"
        delete = "{base}delete"
        prefilled_cfp = "{self.event.cfp.urls.public}?track={self.slug}"
        change_to_submitted = "{base}to-submitted"
        change_to_accepted = "{base}to-accepted"
        change_to_rejected = "{base}to-rejected"
        change_to_canceled = "{base}to-canceled"
        change_to_blocked = "{base}to-blocked"

    def _set_state(self, new_state, force=False, person=None):
        """Check if the new state is valid for this Submission (based on
        SubmissionStates.valid_next_states).

        If yes, set it and save the object. if no, raise a
        SubmissionError with a helpful message.
        """
        valid_next_states = TrackStates.valid_next_states.get(self.state, [])

        if self.state == new_state:
            return
        if force or new_state in valid_next_states:
            old_state = self.state
            self.state = new_state
            self.save(update_fields=["state"])
            track_state_change.send_robust(
                self.event, submission=self, old_state=old_state, user=person
            )
        else:
            source_states = (
                src
                for src, dsts in TrackStates.valid_next_states.items()
                if new_state in dsts
            )

            # build an error message mentioning all states, which are valid source states for the desired new state.
            trans_or = pgettext(
                'used in talk confirm/accept/reject/...-errors, like "... must be accepted OR foo OR bar ..."',
                " or ",
            )
            state_names = dict(TrackStates.get_choices())
            source_states = trans_or.join(
                str(state_names[state]) for state in source_states
            )
            raise TrackError(
                _(
                    "Proposal must be {src_states} not {state} to be {new_state}."
                ).format(
                    src_states=source_states, state=self.state, new_state=new_state
                )
            )

    def to_submitted(self, person=None, force: bool = False):
        self._set_state(TrackStates.SUBMITTED, person, force)

    def to_accepted(self, person=None, force: bool = False):
        self._set_state(TrackStates.ACCEPTED, person, force)

    def to_rejected(self, person=None, force: bool = False):
        self._set_state(TrackStates.REJECTED, person, force)

    def to_canceled(self, person=None, force: bool = False):
        self._set_state(TrackStates.CANCELED, person, force)

    def to_blocked(self, person=None, force: bool = False):
        self._set_state(TrackStates.BLOCKED, person, force)

    def __str__(self) -> str:
        return str(self.name)

    @property
    def slug(self) -> str:
        """The slug makes tracks more readable in URLs.

        It consists of the ID, followed by a slugified (and, in lookups,
        optional) form of the track name.
        """
        return f"{self.id}-{slugify(self.name)}"
