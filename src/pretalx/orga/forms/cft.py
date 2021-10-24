from django import forms
from i18nfield.forms import I18nModelForm

from pretalx.common.mixins.forms import I18nHelpText, ReadOnlyFlag
from pretalx.submission.models import (
    CfT,
)


class CfTForm(ReadOnlyFlag, I18nHelpText, I18nModelForm):
    class Meta:
        model = CfT
        fields = ["headline", "text", "deadline"]
        widgets = {
            "deadline": forms.DateTimeInput(attrs={"class": "datetimepickerfield"})
        }
