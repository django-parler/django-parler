from django.db.models.constants import LOOKUP_SEP
from django.db import models
import django.db.models.fields


class NotRelationField(Exception):
    pass


def get_model_from_relation(field):
    # type: (django.db.models.fields.Field) -> models.Model
    try:
        path_info = field.get_path_info()
    except AttributeError:
        raise NotRelationField
    else:
        return path_info[-1].to_opts.model


def get_extra_related_translation_paths(model, path):
    # type: (models.Model, str) -> List[str]
    """
    Returns paths with active and default transalation models for all Translatable models in path
    """
    from parler.models import TranslatableModel
    pieces = path.split(LOOKUP_SEP)
    parent = model
    current_path = ''
    extra_paths = []
    for piece in pieces:
        field = parent._meta.get_field(piece)
        parent = get_model_from_relation(field)
        current_path += LOOKUP_SEP + piece if current_path else piece
        if issubclass(parent, TranslatableModel):
            for extension in parent._parler_meta:
                extra_paths.append(current_path + LOOKUP_SEP + extension.rel_name_active)
                extra_paths.append(current_path + LOOKUP_SEP + extension.rel_name_default)
    return extra_paths
