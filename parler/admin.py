"""
Translation support for admin forms.
"""
from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django.contrib.admin.util import get_deleted_objects, unquote
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import router
from django.forms import Media
from django.http import HttpResponseRedirect, Http404, HttpRequest
from django.shortcuts import render
from django.utils.encoding import iri_to_uri, force_unicode
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _
from parler import appsettings
from parler.forms import TranslatableModelForm
from parler.managers import TranslatableQuerySet
from parler.models import TranslatableModel
from parler.utils.compat import transaction_atomic
from parler.utils.i18n import normalize_language_code, get_language_title, is_multilingual_project
from parler.utils.template import select_template_name

# Code partially taken from django-hvad
# which is (c) 2011, Jonas Obrist, BSD licensed


_language_media = Media(css={
    'all': ('parler/admin/language_tabs.css',)
})
_language_prepopulated_media = _language_media + Media(js=(
    'admin/js/urlify.js',
    'admin/js/prepopulate.min.js'
))

_fakeRequest = HttpRequest()


class TranslatableAdmin(admin.ModelAdmin):
    """
    Base class for translated admins.

    This class also works as regular admin for non TranslatableModel objects.
    When using this class with a non-TranslatableModel,
    all operations effectively become a NO-OP.
    """

    form = TranslatableModelForm

    deletion_not_allowed_template = 'admin/parler/deletion_not_allowed.html'

    query_language_key = 'language'


    @property
    def change_form_template(self):
        # Dynamic property to support transition to regular models.
        if self._has_translatable_model():
            # While this breaks the admin template name detection,
            # the get_change_form_base_template() makes sure it inherits from your template.
            return 'admin/parler/change_form.html'
        else:
            return None # get default admin selection


    @property
    def media(self):
        # Currently, `prepopulated_fields` can't be used because it breaks the admin validation.
        # TODO: as a fix TranslatedFields should become a RelatedField on the shared model (may also support ORM queries)
        # As workaround, declare the fields in get_prepopulated_fields() and we'll provide the admin media automatically.
        has_prepoplated = len(self.get_prepopulated_fields(_fakeRequest))
        base_media = super(TranslatableAdmin, self).media
        if has_prepoplated:
            return base_media + _language_prepopulated_media
        else:
            return base_media + _language_media


    def _has_translatable_model(self):
        # Allow fallback to regular models when needed.
        return issubclass(self.model, TranslatableModel)


    def _language(self, request, obj=None):
        """
        Get the language parameter from the current request.
        """
        if not is_multilingual_project() or not self._has_translatable_model():
            # By default, the objects are stored in a single static language.
            # This makes the transition to multilingual easier as well.
            # The default language can operate as fallback language too.
            return appsettings.PARLER_DEFAULT_LANGUAGE_CODE
        else:
            # In multilingual mode, take the provided language of the request.
            code = request.GET.get(self.query_language_key)

            if not code:
                # Show first tab by default
                try:
                    lang_choices = appsettings.PARLER_LANGUAGES[settings.SITE_ID]
                    code = lang_choices[0]['code']
                except (KeyError, IndexError):
                    # No configuration, always fallback to default language.
                    # This is essentially a non-multilingual configuration.
                    code = appsettings.PARLER_DEFAULT_LANGUAGE_CODE

            return normalize_language_code(code)


    def language_column(self, object):
        """
        The language column which can be included in the ``list_display``.
        """
        languages = self.get_available_languages(object)
        return u'<span class="available-languages">{0}</span>'.format(' '.join(languages))

    language_column.allow_tags = True
    language_column.short_description = _("Languages")


    def get_available_languages(self, obj):
        """
        Fetching the available languages as queryset.
        """
        if obj:
            return obj.get_available_languages()
        else:
            return self.model._translations_model.objects.get_empty_query_set()


    def queryset(self, request):
        """
        Make sure the current language is selected.
        """
        qs = super(TranslatableAdmin, self).queryset(request)

        if self._has_translatable_model():
            if not isinstance(qs, TranslatableQuerySet):
                raise ImproperlyConfigured("{0} class does not inherit from TranslatableQuerySet".format(qs.__class__.__name__))

            if not is_multilingual_project():
                # Make sure the current translations remain visible, not the dynamically set get_language() value.
                qs = qs.language(appsettings.PARLER_DEFAULT_LANGUAGE_CODE)
        return qs


    def get_object(self, request, object_id):
        """
        Make sure the object is fetched in the correct language.
        """
        obj = super(TranslatableAdmin, self).get_object(request, object_id)
        if obj is not None and self._has_translatable_model():  # Allow fallback to regular models.
            obj.set_current_language(self._language(request, obj), initialize=True)

        return obj


    def get_form(self, request, obj=None, **kwargs):
        """
        Pass the current language to the form.
        """
        form_class = super(TranslatableAdmin, self).get_form(request, obj, **kwargs)
        if self._has_translatable_model():
            form_class.language_code = obj.get_current_language() if obj is not None else self._language(request)

        return form_class


    def get_urls(self):
        """
        Add a delete-translation view.
        """
        urlpatterns = super(TranslatableAdmin, self).get_urls()
        if not self._has_translatable_model():
            return urlpatterns
        else:
            info = self.model._meta.app_label, self.model._meta.module_name

            return patterns('',
                url(r'^(.+)/delete-translation/(.+)/$',
                    self.admin_site.admin_view(self.delete_translation),
                    name='{0}_{1}_delete_translation'.format(*info)
                ),
            ) + urlpatterns


    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """
        Insert the language tabs.
        """
        if self._has_translatable_model():
            lang_code = obj.get_current_language() if obj is not None else self._language(request)
            lang = get_language_title(lang_code)

            available_languages = self.get_available_languages(obj)
            current_is_translated = lang_code in available_languages
            language_tabs = self.get_language_tabs(request, obj, available_languages)

            context['current_is_translated'] = current_is_translated
            context['allow_deletion'] = len(available_languages) > 1
            context['language_tabs'] = language_tabs
            if language_tabs:
                context['title'] = '%s (%s)' % (context['title'], lang)
            if not current_is_translated:
                add = True  # lets prepopulated_fields_js work.

        # django-fluent-pages uses the same technique
        if 'default_change_form_template' not in context:
            context['default_change_form_template'] = self.get_change_form_base_template()

        #context['base_template'] = self.get_change_form_base_template()
        return super(TranslatableAdmin, self).render_change_form(request, context, add, change, form_url, obj)


    def response_add(self, request, obj, post_url_continue=None):
        # Make sure ?language=... is included in the redirects.
        redirect = super(TranslatableAdmin, self).response_add(request, obj, post_url_continue)
        return self._patch_redirect(request, obj, redirect)


    def response_change(self, request, obj):
        # Make sure ?language=... is included in the redirects.
        redirect = super(TranslatableAdmin, self).response_change(request, obj)
        return self._patch_redirect(request, obj, redirect)


    def _patch_redirect(self, request, obj, redirect):
        if redirect.status_code not in (301,302):
            return redirect  # a 200 response likely.

        uri = iri_to_uri(request.path)
        info = (self.model._meta.app_label, self.model._meta.module_name)

        # Pass ?language=.. to next page.
        language = request.GET.get(self.query_language_key)
        if language:
            continue_urls = (uri, "../add/", reverse('admin:{0}_{1}_add'.format(*info)))
            if redirect['Location'] in continue_urls and self.query_language_key in request.GET:
                # "Save and add another" / "Save and continue" URLs
                redirect['Location'] += "?{0}={1}".format(self.query_language_key, language)
        return redirect


    def get_language_tabs(self, request, obj, available_languages):
        """
        Determine the language tabs to show.
        """
        tabs = []
        get = request.GET.copy()  # QueryDict object
        language = obj.get_current_language() if obj is not None else self._language(request)
        tab_languages = []

        base_url = '{0}://{1}{2}'.format(request.is_secure() and 'https' or 'http', request.get_host(), request.path)

        for lang_dict in appsettings.PARLER_LANGUAGES.get(settings.SITE_ID, ()):
            code = lang_dict['code']
            title = get_language_title(code)
            get['language'] = code
            url = '{0}?{1}'.format(base_url, get.urlencode())

            if code == language:
                status = 'current'
            elif code in available_languages:
                status = 'available'
            else:
                status = 'empty'

            tabs.append((url, title, code, status))
            tab_languages.append(code)

        # Additional stale translations in the database?
        if appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS:
            for code in available_languages:
                if code not in tab_languages:
                    get['language'] = code
                    url = '{0}?{1}'.format(base_url, get.urlencode())

                    if code == language:
                        status = 'current'
                    else:
                        status = 'available'

                    tabs.append((url, get_language_title(code), code, status))

        return tabs


    @csrf_protect_m
    @transaction_atomic
    def delete_translation(self, request, object_id, language_code):
        """
        The 'delete translation' admin view for this model.
        """
        opts = self.model._meta
        translations_model = self.model._translations_model

        try:
            translation = translations_model.objects.select_related('master').get(master=unquote(object_id), language_code=language_code)
        except translations_model.DoesNotExist:
            raise Http404

        if not self.has_delete_permission(request, translation):
            raise PermissionDenied

        if self.get_available_languages(translation.master).count() <= 1:
            return self.deletion_not_allowed(request, translation, language_code)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.

        using = router.db_for_write(translations_model)
        lang = get_language_title(language_code)
        (deleted_objects, perms_needed, protected) = get_deleted_objects(
            [translation], translations_model._meta, request.user, self.admin_site, using)

        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = _('{0} translation of {1}').format(lang, force_unicode(translation))  # in hvad: (translation.master)

            self.log_deletion(request, translation, obj_display)
            self.delete_model_translation(request, translation)
            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % dict(
                name=force_unicode(opts.verbose_name), obj=force_unicode(obj_display)
            ))

            if self.has_change_permission(request, None):
                return HttpResponseRedirect(reverse('admin:{0}_{1}_changelist'.format(opts.app_label, opts.module_name)))
            else:
                return HttpResponseRedirect(reverse('admin:index'))

        object_name = _('{0} Translation').format(force_unicode(opts.verbose_name))
        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = {
            "title": title,
            "object_name": object_name,
            "object": translation,
            "deleted_objects": deleted_objects,
            "perms_lacking": perms_needed,
            "protected": protected,
            "opts": opts,
            "app_label": opts.app_label,
        }

        return render(request, self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (opts.app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % opts.app_label,
            "admin/delete_confirmation.html"
        ], context)


    def deletion_not_allowed(self, request, obj, language_code):
        """
        Deletion-not-allowed view.
        """
        opts = self.model._meta
        context = {
            'object': obj.master,
            'language_code': language_code,
            'opts': opts,
            'app_label': opts.app_label,
            'language_name': get_language_title(language_code),
            'object_name': force_unicode(opts.verbose_name)
        }
        return render(request, self.deletion_not_allowed_template, context)


    def delete_model_translation(self, request, translation):
        """
        Hook for deleting a translation.
        """
        translation.delete()


    def get_change_form_base_template(self):
        """
        Determine what the actual `change_form_template` should be.
        """
        opts = self.model._meta
        app_label = opts.app_label
        return _lazy_select_template_name((
            "admin/{0}/{1}/change_form.html".format(app_label, opts.object_name.lower()),
            "admin/{0}/change_form.html".format(app_label),
            "admin/change_form.html"
        ))


_lazy_select_template_name = lazy(select_template_name, unicode)
