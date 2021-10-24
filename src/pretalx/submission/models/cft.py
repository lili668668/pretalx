import datetime as dt

from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_scopes import ScopedManager
from i18nfield.fields import I18nCharField, I18nTextField

from pretalx.common.mixins.models import LogMixin
from pretalx.common.phrases import phrases
from pretalx.common.urls import EventUrls


class CfT(LogMixin, models.Model):
    event = models.OneToOneField(to="event.Event", on_delete=models.PROTECT)
    is_start = models.BooleanField(default=False)
    headline = I18nCharField(
        max_length=300, null=True, blank=True, verbose_name=_("headline")
    )
    text = I18nTextField(
        null=True,
        blank=True,
        verbose_name=_("text"),
        help_text=phrases.base.use_markdown,
    )
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("cft_deadline"),
    )

    objects = ScopedManager(event="event")

    class urls(EventUrls):
        base = "{self.event.orga_urls.cft}"
        public = "{self.event.urls.base}cft"
        editor = "{base}flow/"
        toggle = "{base}toggle/"
        questions = "{base}questions/"
        new_question = "{questions}new"
        remind_questions = "{questions}remind"
        text = edit_text = "{base}text"
        types = "{base}types/"
        new_type = "{types}new"
        tracks = "{base}tracks/"
        new_track = "{tracks}new"
        new_access_code = "{access_codes}new"
        submit = "{self.event.urls.base}submit/"

    def __str__(self) -> str:
        """Help with debugging."""
        return f"CfP(event={self.event.slug})"

    @cached_property
    def is_open(self) -> bool:
        if self.deadline is None:
            return self.is_start
        return self.deadline >= now() if self.is_start else False
