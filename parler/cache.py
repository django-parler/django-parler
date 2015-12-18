"""
django-parler uses caching to avoid fetching model data when it doesn't have to.

These functions are used internally by django-parler to fetch model data.
Since all calls to the translation table are routed through our model descriptor fields,
cache access and expiry is rather simple to implement.
"""
import django
from django.core.cache import cache
from django.utils import six
from parler import appsettings
from parler.utils import get_language_settings

if six.PY3:
    long = int

if django.VERSION >= (1, 6):
    DEFAULT_TIMEOUT = cache.default_timeout
else:
    DEFAULT_TIMEOUT = 0


class IsMissing(object):
    # Allow _get_any_translated_model() to evaluate this as False.

    def __nonzero__(self):
        return False   # Python 2

    def __bool__(self):
        return False   # Python 3

    def __repr__(self):
        return "<IsMissing>"

MISSING = IsMissing()  # sentinel value


def get_object_cache_keys(instance):
    """
    Return the cache keys associated with an object.
    """
    if instance.pk is None or instance._state.adding:
        return []

    keys = []
    tr_models = instance._parler_meta.get_all_models()

    # TODO: performs a query to fetch the language codes. Store that in memcached too.
    for language in instance.get_available_languages():
        for tr_model in tr_models:
            keys.append(get_translation_cache_key(tr_model, instance.pk, language))

    return keys


def get_translation_cache_key(translated_model, master_id, language_code):
    """
    The low-level function to get the cache key for a translation.
    """
    # Always cache the entire object, as this already produces
    # a lot of queries. Don't go for caching individual fields.
    return 'parler.{0}.{1}.{2}.{3}'.format(translated_model._meta.app_label, translated_model.__name__, master_id, language_code)


def get_cached_translation(instance, language_code=None, related_name=None, use_fallback=False):
    """
    Fetch an cached translation.

    .. versionadded 1.2 Added the ``related_name`` parameter.
    """
    if language_code is None:
        language_code = instance.get_current_language()

    translated_model = instance._parler_meta.get_model_by_related_name(related_name)
    values = _get_cached_values(instance, translated_model, language_code, use_fallback)
    if not values:
        return None

    try:
        translation = translated_model(**values)
    except TypeError:
        # Some model field was removed, cache entry is no longer working.
        return None

    translation._state.adding = False
    return translation


def get_cached_translated_field(instance, field_name, language_code=None, use_fallback=False):
    """
    Fetch an cached field.
    """
    if language_code is None:
        language_code = instance.get_current_language()

    # In django-parler 1.1 the order of the arguments was fixed, It used to be language_code, field_name
    # This serves as detection against backwards incompatibility issues.
    if len(field_name) <= 5 and len(language_code) > 5:
        raise RuntimeError("Unexpected language code, did you swap field_name, language_code?")

    translated_model = instance._parler_meta.get_model_by_field(field_name)
    values = _get_cached_values(instance, translated_model, language_code, use_fallback)
    if not values:
        return None

    # Allow older cached versions where the field didn't exist yet.
    return values.get(field_name, None)


def _get_cached_values(instance, translated_model, language_code, use_fallback=False):
    """
    Fetch an cached field.
    """
    if not appsettings.PARLER_ENABLE_CACHING or not instance.pk or instance._state.adding:
        return None

    key = get_translation_cache_key(translated_model, instance.pk, language_code)
    values = cache.get(key)
    if not values:
        return None

    # Check for a stored fallback marker
    if values.get('__FALLBACK__', False):
        # Internal trick, already set the fallback marker, so no query will be performed.
        instance._translations_cache[translated_model][language_code] = MISSING

        # Allow to return the fallback language instead.
        if use_fallback:
            lang_dict = get_language_settings(language_code)
            # iterate over list of fallback languages, which should be already
            # in proper order
            for fallback_lang in lang_dict['fallbacks']:
                if fallback_lang != language_code:
                    return _get_cached_values(
                        instance, translated_model, fallback_lang,
                        use_fallback=False
                    )
        return None

    values['master'] = instance
    values['language_code'] = language_code
    return values


def _cache_translation(translation, timeout=DEFAULT_TIMEOUT):
    """
    Store a new translation in the cache.
    """
    if not appsettings.PARLER_ENABLE_CACHING:
        return

    if translation.master_id is None:
        raise ValueError("Can't cache unsaved translation")

    # Cache a translation object.
    # For internal usage, object parameters are not suited for outside usage.
    fields = translation.get_translated_fields()
    values = {'id': translation.id}
    for name in fields:
        values[name] = getattr(translation, name)

    key = get_translation_cache_key(translation.__class__, translation.master_id, translation.language_code)
    cache.set(key, values, timeout=timeout)


def _cache_translation_needs_fallback(instance, language_code, related_name, timeout=DEFAULT_TIMEOUT):
    """
    Store the fact that a translation doesn't exist, and the fallback should be used.
    """
    if not appsettings.PARLER_ENABLE_CACHING or not instance.pk or instance._state.adding:
        return

    tr_model = instance._parler_meta.get_model_by_related_name(related_name)
    key = get_translation_cache_key(tr_model, instance.pk, language_code)
    cache.set(key, {'__FALLBACK__': True}, timeout=timeout)


def _delete_cached_translations(shared_model):
    cache.delete_many(get_object_cache_keys(shared_model))


def _delete_cached_translation(translation):
    if not appsettings.PARLER_ENABLE_CACHING:
        return

    # Delete a cached translation
    # For internal usage, object parameters are not suited for outside usage.
    key = get_translation_cache_key(translation.__class__, translation.master_id, translation.language_code)
    cache.delete(key)
