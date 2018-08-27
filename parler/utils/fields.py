from django.db.models.constants import LOOKUP_SEP
from django.db import models
from django.db.models.fields.related import RelatedField

try:
    from django.db.models.fields.reverse_related import ForeignObjectRel
except ImportError:
    from django.db.models.fields.related import ForeignObjectRel


def _get_last_field_from_path(model, path):
    # type: (models.Model, str) -> models.fields.Field
    path_parts = path.split(LOOKUP_SEP)
    option = model._meta

    for part in path_parts[:-1]:
        field = option.get_field(part)
        path_info = field.get_path_info()
        option = path_info[-1].to_opts

    last_part = path_parts[-1]
    return option.get_field(last_part)


def get_extra_related_translation_paths(model, path):
    # type: (models.Model, str) -> List[str]
    """
    Returns paths with active and default translation models for all Translatable models in path
    """
    from parler.models import TranslatableModel

    last_field = _get_last_field_from_path(model=model, path=path)
    is_last_field_related_field = isinstance(last_field, RelatedField) or isinstance(last_field, ForeignObjectRel)

    if is_last_field_related_field and issubclass(last_field.related_model, TranslatableModel):
        extra_paths = []
        for extension in last_field.related_model._parler_meta:
            extra_paths.append(path + LOOKUP_SEP + extension.rel_name_active)
            extra_paths.append(path + LOOKUP_SEP + extension.rel_name_default)
        return extra_paths

    return []
