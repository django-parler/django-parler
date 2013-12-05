from django.core.cache import cache
from parler import appsettings
from parler.utils import get_language_settings


def get_object_cache_keys(instance):
    """
    Return the cache keys associated with an object.
    """
    keys = []
    # TODO: performs a query to fetch the language codes. Store that in memcached too.
    for language in instance.get_available_languages():
        keys.append(get_translation_cache_key(instance._translations_model, instance.pk, language))

    return keys


def get_translation_cache_key(translated_model, master_id, language_code):
    """
    The low-level function to get the cache key for a translation.
    """
    # Always cache the entire object, as this already produces
    # a lot of queries. Don't go for caching individual fields.
    return 'parler.{0}.{1}.{2}'.format(translated_model.__name__, long(master_id), language_code)


def get_cached_translation(instance, language_code, use_fallback=False):
    """
    Fetch an cached translation.
    """
    if not appsettings.PARLER_ENABLE_CACHING:
        return None

    key = get_translation_cache_key(instance._translations_model, instance.pk, language_code)
    values = cache.get(key)
    if not values:
        return None

    # Check for a stored fallback marker
    if values.get('__FALLBACK__', False):
        # Allow to return the fallback language instead.
        if use_fallback:
            lang_dict = get_language_settings(language_code)
            if lang_dict['fallback'] != language_code:
                return get_cached_translation(instance, lang_dict['fallback'], use_fallback=False)
        return None

    values['master'] = instance
    values['language_code'] = language_code
    translation = instance._translations_model(**values)
    translation._state.adding = False
    return translation


def get_cached_translated_field(instance, language_code, field_name):
    """
    Fetch an cached field.
    """
    if not appsettings.PARLER_ENABLE_CACHING:
        return None

    values = get_translation_cache_key(instance._translations_model, instance.pk, language_code)
    if not values:
        return None

    # Allow older cached versions where the field didn't exist yet.
    return values.get(field_name, None)


def _cache_translation(translation, timeout=0):
    """
    Store a new translation in the cache.
    """
    if not appsettings.PARLER_ENABLE_CACHING:
        return

    # Cache a translation object.
    # For internal usage, object parameters are not suited for outside usage.
    fields = translation.get_translated_fields()
    values = {'id': translation.id}
    for name in fields:
        values[name] = getattr(translation, name)

    key = get_translation_cache_key(translation.__class__, translation.master_id, translation.language_code)
    cache.set(key, values, timeout=timeout)


def _cache_translation_needs_fallback(instance, language_code, timeout=0):
    """
    Store the fact that a translation doesn't exist, and the fallback should be used.
    """
    key = get_translation_cache_key(instance._translations_model, instance.pk, language_code)
    cache.set(key, {'__FALLBACK__': True}, timeout=timeout)


def _delete_cached_translations(shared_model):
    for key in get_object_cache_keys(shared_model):
        cache.delete(key)


def _delete_cached_translation(translation):
    if not appsettings.PARLER_ENABLE_CACHING:
        return

    # Delete a cached translation
    # For internal usage, object parameters are not suited for outside usage.
    key = get_translation_cache_key(translation.__class__, translation.master_id, translation.language_code)
    cache.delete(key)
