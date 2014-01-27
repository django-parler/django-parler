"""
Translation support for admin forms.
"""
import django
from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m, BaseModelAdmin, InlineModelAdmin
from django.contrib.admin.util import get_deleted_objects, unquote
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import router
from django.forms import Media
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseRedirect, Http404, HttpRequest
from django.shortcuts import render
from django.utils.encoding import iri_to_uri, force_unicode
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _, get_language
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

class TabsList(list):
    def __init__(self, seq=(), css_class=None):
        self.css_class = css_class
        self.current_is_translated = False
        self.allow_deletion = False
        super(TabsList, self).__init__(seq)


class BaseTranslatableAdmin(BaseModelAdmin):
    """
    The shared code between the regular model admin and inline classes.
    """
    form = TranslatableModelForm
    query_language_key = 'language'


    @property
    def media(self):
        # Currently, `prepopulated_fields` can't be used because it breaks the admin validation.
        # TODO: as a fix TranslatedFields should become a RelatedField on the shared model (may also support ORM queries)
        # As workaround, declare the fields in get_prepopulated_fields() and we'll provide the admin media automatically.
        has_prepoplated = len(self.get_prepopulated_fields(_fakeRequest))
        base_media = super(BaseTranslatableAdmin, self).media
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
                # forms: show first tab by default
                code = self._get_first_tab_language()

            return normalize_language_code(code)


    def _get_first_tab_language(self):
        try:
            lang_choices = appsettings.PARLER_LANGUAGES[settings.SITE_ID]
            code = lang_choices[0]['code']
        except (KeyError, IndexError):
            # No configuration, always fallback to default language.
            # This is essentially a non-multilingual configuration.
            code = appsettings.PARLER_DEFAULT_LANGUAGE_CODE

        return normalize_language_code(code)


    def get_form_language(self, request, obj=None):
        """
        Return the current language for the currently displayed object fields.
        """
        if obj is not None:
            return obj.get_current_language()
        else:
            return self._language(request)


    def get_queryset_language(self, request):
        """
        Return the language to use in the queryset.
        """
        if not is_multilingual_project():
            # Make sure the current translations remain visible, not the dynamically set get_language() value.
            return appsettings.PARLER_DEFAULT_LANGUAGE_CODE
        else:
            # Allow to adjust to current language
            # This is overwritten for the inlines, which follow the primary object.
            return get_language()


    def queryset(self, request):
        """
        Make sure the current language is selected.
        """
        qs = super(BaseTranslatableAdmin, self).queryset(request)

        if self._has_translatable_model():
            if not isinstance(qs, TranslatableQuerySet):
                raise ImproperlyConfigured("{0} class does not inherit from TranslatableQuerySet".format(qs.__class__.__name__))

            # Apply a consistent language to all objects.
            qs_language = self.get_queryset_language(request)
            if qs_language:
                qs = qs.language(qs_language)

        return qs


    def get_language_tabs(self, request, obj, available_languages, css_class=None):
        """
        Determine the language tabs to show.
        """
        tabs = TabsList(css_class=css_class)
        get = request.GET.copy()  # QueryDict object
        language = self.get_form_language(request, obj)
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

        tabs.current_is_translated = language in available_languages
        tabs.allow_deletion = len(available_languages) > 1
        return tabs



class TranslatableAdmin(BaseTranslatableAdmin, admin.ModelAdmin):
    """
    Base class for translated admins.

    This class also works as regular admin for non TranslatableModel objects.
    When using this class with a non-TranslatableModel,
    all operations effectively become a NO-OP.
    """

    deletion_not_allowed_template = 'admin/parler/deletion_not_allowed.html'

    #: Whether translations of inlines should also be deleted when deleting a translation.
    delete_inline_translations = True


    @property
    def change_form_template(self):
        # Dynamic property to support transition to regular models.
        if self._has_translatable_model():
            # While this breaks the admin template name detection,
            # the get_change_form_base_template() makes sure it inherits from your template.
            return 'admin/parler/change_form.html'
        else:
            return None # get default admin selection


    def language_column(self, object):
        """
        The language column which can be included in the ``list_display``.
        """
        languages = self.get_available_languages(object)
        languages = [self.get_language_short_title(code) for code in languages]
        return u'<span class="available-languages">{0}</span>'.format(' '.join(languages))

    language_column.allow_tags = True
    language_column.short_description = _("Languages")


    def get_language_short_title(self, language_code):
        """
        Hook for allowing to change the title in the :func:`language_column` of the list_display.
        """
        return language_code


    def get_available_languages(self, obj):
        """
        Fetching the available languages as queryset.
        """
        if obj:
            return obj.get_available_languages()
        else:
            return self.model._translations_model.objects.none()


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
            form_class.language_code = self.get_form_language(request, obj)

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
            lang_code = self.get_form_language(request, obj)
            lang = get_language_title(lang_code)

            available_languages = self.get_available_languages(obj)
            language_tabs = self.get_language_tabs(request, obj, available_languages)
            context['language_tabs'] = language_tabs
            if language_tabs:
                context['title'] = '%s (%s)' % (context['title'], lang)
            if not language_tabs.current_is_translated:
                add = True  # lets prepopulated_fields_js work.

        # django-fluent-pages uses the same technique
        if 'default_change_form_template' not in context:
            context['default_change_form_template'] = self.get_change_form_base_template()

        #context['base_template'] = self.get_change_form_base_template()
        return super(TranslatableAdmin, self).render_change_form(request, context, add, change, form_url, obj)


    def response_add(self, request, obj, post_url_continue=None):
        # Minor behavior difference for Django 1.4
        if post_url_continue is None and django.VERSION < (1,5):
            post_url_continue = '../%s/'

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

        # Extend deleted objects with the inlines.
        if self.delete_inline_translations:
            shared_obj = translation.master
            for inline, qs in self._get_inline_translations(request, translation.language_code, obj=shared_obj):
                (del2, perms2, protected2) = get_deleted_objects(qs, qs.model._meta, request.user, self.admin_site, using)
                deleted_objects += del2
                perms_needed = perms_needed or perms2
                protected += protected2

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

        # Also delete translations of inlines which the user has access to.
        if self.delete_inline_translations:
            master = translation.master
            for inline, qs in self._get_inline_translations(request, translation.language_code, obj=master):
                qs.delete()


    def _get_inline_translations(self, request, language_code, obj=None):
        """
        Fetch the inline translations
        """
        for inline in self.get_inline_instances(request, obj=obj):
            if issubclass(inline.model, TranslatableModel):
                # leverage inlineformset_factory() to find the ForeignKey.
                # This also resolves the fk_name if it's set.
                fk = inline.get_formset(request, obj).fk

                rel_name = 'master__{}'.format(fk.name)
                filters = {
                    'language_code': language_code,
                    rel_name: obj
                }

                qs = inline.model._translations_model.objects.filter(**filters)
                if obj is not None:
                    qs = qs.using(obj._state.db)

                yield inline, qs


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


class TranslatableBaseInlineFormSet(BaseInlineFormSet):
    language_code = None

    def _construct_form(self, i, **kwargs):
        form = super(TranslatableBaseInlineFormSet, self)._construct_form(i, **kwargs)
        form.language_code = self.language_code   # Pass the language code for new objects!
        return form

    def save_new(self, form, commit=True):
        obj = super(TranslatableBaseInlineFormSet, self).save_new(form, commit)
        return obj


class TranslatableInlineModelAdmin(BaseTranslatableAdmin, InlineModelAdmin):
    """
    Base class for inline models.
    """
    form = TranslatableModelForm
    formset = TranslatableBaseInlineFormSet

    @property
    def inline_tabs(self):
        """
        Whether to show inline tabs, can be set as attribute on the inline.
        """
        return not self._has_translatable_parent_model()

    def _has_translatable_parent_model(self):
        # Allow fallback to regular models when needed.
        return issubclass(self.parent_model, TranslatableModel)

    def get_queryset_language(self, request):
        if not is_multilingual_project():
            # Make sure the current translations remain visible, not the dynamically set get_language() value.
            return appsettings.PARLER_DEFAULT_LANGUAGE_CODE
        else:
            # Set the initial language for fetched objects.
            # This is needed for the TranslatableInlineModelAdmin
            return self._language(request)

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super(TranslatableInlineModelAdmin, self).get_formset(request, obj, **kwargs)
        # Existing objects already got the language code from the queryset().language() method.
        # For new objects, the language code should be set here.
        FormSet.language_code = self.get_form_language(request, obj)

        if self.inline_tabs:
            # Need to pass information to the template, this can only happen via the FormSet object.
            available_languages = self.get_available_languages(obj, FormSet)
            FormSet.language_tabs = self.get_language_tabs(request, obj, available_languages, css_class='parler-inline-language-tabs')
            FormSet.language_tabs.allow_deletion = self._has_translatable_parent_model()   # Views not available otherwise.

        return FormSet

    def get_form_language(self, request, obj=None):
        if self._has_translatable_parent_model():
            return super(TranslatableInlineModelAdmin, self).get_form_language(request, obj=obj)
        else:
            # Follow the ?language parameter
            return self._language(request)

    def get_available_languages(self, obj, formset):
        """
        Fetching the available inline languages as queryset.
        """
        if obj:
            # Inlines dictate language code, not the parent model.
            filter = {
                'master__{0}'.format(formset.fk.name): obj
            }
            return self.model._translations_model.objects.using(obj._state.db).filter(**filter) \
                   .values_list('language_code', flat=True).distinct().order_by('language_code')
        else:
            return self.model._translations_model.objects.none()


class TranslatableStackedInline(TranslatableInlineModelAdmin):
    @property
    def template(self):
        if self.inline_tabs:
            return 'admin/parler/edit_inline/stacked_tabs.html'
        else:
            # Admin default
            return 'admin/edit_inline/stacked.html'


class TranslatableTabularInline(TranslatableInlineModelAdmin):
    @property
    def template(self):
        if self.inline_tabs:
            return 'admin/parler/edit_inline/tabular_tabs.html'
        else:
            # Admin default
            return 'admin/edit_inline/tabular.html'
