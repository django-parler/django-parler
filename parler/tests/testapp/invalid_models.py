from django.db import models

from parler.models import TranslatableModel, TranslatedFields
from parler.tests.testapp.models import RegularModel


class RegularModelProxy(TranslatableModel, RegularModel):
    # Overwriting existing fields in a regular model by using a proxy.
    # This doesn't work yet, and unittests confirm that.
    translations = TranslatedFields(
        original_field=models.CharField(default="translated", max_length=255)
    )

    class Meta:
        proxy = True
