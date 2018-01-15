"""
Translation support for admin forms.

*django-parler* provides the following classes:

* Model support: :class:`TranslatableAdmin`.
* Inline support: :class:`TranslatableInlineModelAdmin`, :class:`TranslatableStackedInline`, :class:`TranslatableTabularInline`.
* Utilities: :class:`SortedRelatedFieldListFilter`.

Admin classes can be created as expected:

.. code-block:: python

    from django.contrib import admin
    from parler.admin import TranslatableAdmin
    from myapp.models import Project

    class ProjectAdmin(TranslatableAdmin):
        list_display = ('title', 'status')
        fieldsets = (
            (None, {
                'fields': ('title', 'status'),
            }),
        )

    admin.site.register(Project, ProjectAdmin)

All translated fields can be used in the :attr:`~django.contrib.admin.ModelAdmin.list_display`
and :attr:`~django.contrib.admin.ModelAdmin.fieldsets` like normal fields.

While almost every admin feature just works, there are a few special cases to take care of:

* The :attr:`~django.contrib.admin.ModelAdmin.search_fields` needs the actual ORM fields.
* The :attr:`~django.contrib.admin.ModelAdmin.prepopulated_fields` needs to be replaced with a call
  to :func:`~django.contrib.admin.ModelAdmin.get_prepopulated_fields`.

See the :ref:`admin compatibility page <admin-compat>` for details.
"""
from __future__ import unicode_literals
import django
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m, BaseModelAdmin, InlineModelAdmin
from django.contrib.admin.utils import get_deleted_objects, unquote
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.db import router, transaction
from django.forms import Media
from django.http import HttpResponseRedirect, Http404, HttpRequest
from django.shortcuts import render
from django.utils.encoding import iri_to_uri, force_text
from django.utils.functional import cached_property
from django.utils.html import conditional_escape, escape
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, get_language
from parler import appsettings
from parler.forms import TranslatableModelForm, TranslatableBaseInlineFormSet
from parler.managers import TranslatableQuerySet
from parler.models import TranslatableModelMixin
from parler.utils.i18n import get_language_title, is_multilingual_project
from parler.utils.views import get_language_parameter, get_language_tabs
from parler.utils.template import select_template_name

try:
    from django.urls import reverse
except ImportError:
    # Support for Django <= 1.10
    from django.core.urlresolvers import reverse

# Code partially taken from django-hvad
# which is (c) 2011, Jonas Obrist, BSD licensed

__all__ = (
    'BaseTranslatableAdmin',
    'TranslatableAdmin',
    'TranslatableInlineModelAdmin',
    'TranslatableStackedInline',
    'TranslatableTabularInline',
    'SortedRelatedFieldListFilter',
)

if django.VERSION >= (1, 9) or 'flat' in settings.INSTALLED_APPS:
    _language_media = Media(css={
        'all': (
            'parler/admin/parler_admin.css',
            'parler/admin/parler_admin_flat.css',
        )
    })
else:
    _language_media = Media(css={
        'all': ('parler/admin/parler_admin.css',)
    })

_language_prepopulated_media = _language_media + Media(js=(
    'admin/js/urlify.js',
    'admin/js/prepopulate.min.js'
))

_fakeRequest = HttpRequest()


class BaseTranslatableAdmin(BaseModelAdmin):
    """
    The shared code between the regular model admin and inline classes.
    """
    #: The form to use for the model.
    form = TranslatableModelForm

    #: The URL parameter for the language value.
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
        return issubclass(self.model, TranslatableModelMixin)

    def _language(self, request, obj=None):
        """
        Get the language parameter from the current request.
        """
        return get_language_parameter(request, self.query_language_key)

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
            return appsettings.PARLER_LANGUAGES.get_default_language()
        else:
            # Allow to adjust to current language
            # This is overwritten for the inlines, which follow the primary object.
            return get_language()

    def get_queryset(self, request):
        """
        Make sure the current language is selected.
        """
        if django.VERSION >= (1, 6):
            qs = super(BaseTranslatableAdmin, self).get_queryset(request)
        else:
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
        current_language = self.get_form_language(request, obj)
        return get_language_tabs(request, current_language, available_languages, css_class=css_class)


class TranslatableAdmin(BaseTranslatableAdmin, admin.ModelAdmin):
    """
    Base class for translated admins.

    This class also works as regular admin for non TranslatableModel objects.
    When using this class with a non-TranslatableModel,
    all operations effectively become a NO-OP.
    """
    #: Whether the translations should be prefetched when displaying the 'language_column' in the list.
    prefetch_language_column = True

    deletion_not_allowed_template = 'admin/parler/deletion_not_allowed.html'

    #: Whether translations of inlines should also be deleted when deleting a translation.
    delete_inline_translations = True

    @property
    def change_form_template(self):
        """
        Dynamic property to support transition to regular models.

        This automatically picks ``admin/parler/change_form.html`` when the admin uses a translatable model.
        """
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
        return mark_safe(
            self._languages_column(object, span_classes='available-languages')
        )  # span class for backwards compatibility
    language_column.allow_tags = True  # Django < 1.9
    language_column.short_description = _("Languages")

    def all_languages_column(self, object):
        """
        The language column which can be included in the ``list_display``.
        It also shows untranslated languages
        """
        all_languages = [code for code, __ in settings.LANGUAGES]
        return mark_safe(
            self._languages_column(
                object, all_languages, span_classes='all-languages'
            )
        )
    all_languages_column.allow_tags = True  # Django < 1.9
    all_languages_column.short_description = _("Languages")

    def _languages_column(self, object, all_languages=None, span_classes=''):
        active_languages = self.get_available_languages(object)
        if all_languages is None:
            all_languages = active_languages

        current_language = object.get_current_language()
        buttons = []
        opts = self.opts
        for code in (all_languages or active_languages):
            classes = ['lang-code']
            if code in active_languages:
                classes.append('active')
            else:
                classes.append('untranslated')
            if code == current_language:
                classes.append('current')

            info = _get_model_meta(opts)
            admin_url = reverse('admin:{0}_{1}_change'.format(*info), args=(object.pk,), current_app=self.admin_site.name)
            buttons.append('<a class="{classes}" href="{href}?language={language_code}">{title}</a>'.format(
                language_code=code,
                classes=' '.join(classes),
                href=escape(admin_url),
                title=conditional_escape(self.get_language_short_title(code))
           ))
        return '<span class="language-buttons {0}">{1}</span>'.format(
            span_classes,
            ' '.join(buttons)
        )

    def get_language_short_title(self, language_code):
        """
        Hook for allowing to change the title in the :func:`language_column` of the list_display.
        """
        # Show language codes in uppercase by default.
        # This avoids a general text-transform CSS rule,
        # that might conflict with showing longer titles for a language instead of the code.
        # (e.g. show "Global" instead of "EN")
        return language_code.upper()

    def get_available_languages(self, obj):
        """
        Fetching the available languages as queryset.
        """
        if obj:
            return obj.get_available_languages()
        else:
            return self.model._parler_meta.root_model.objects.none()

    def get_queryset(self, request):
        qs = super(TranslatableAdmin, self).get_queryset(request)

        if self.prefetch_language_column:
            # When the available languages are shown in the listing, prefetch available languages.
            # This avoids an N-query issue because each row needs the available languages.
            list_display = self.get_list_display(request)
            if 'language_column' in list_display or 'all_languages_column' in list_display:
                qs = qs.prefetch_related(self.model._parler_meta.root_rel_name)

        return qs

    def get_object(self, request, object_id, *args, **kwargs):
        """
        Make sure the object is fetched in the correct language.
        """
        # The args/kwargs are to support Django 1.8, which adds a from_field parameter
        obj = super(TranslatableAdmin, self).get_object(request, object_id, *args, **kwargs)

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
            opts = self.model._meta
            info = _get_model_meta(opts)

            if django.VERSION < (1, 9):
                delete_path = url(
                    r'^(.+)/delete-translation/(.+)/$',
                    self.admin_site.admin_view(self.delete_translation),
                    name='{0}_{1}_delete_translation'.format(*info)
                )
            else:
                delete_path = url(
                    r'^(.+)/change/delete-translation/(.+)/$',
                    self.admin_site.admin_view(self.delete_translation),
                    name='{0}_{1}_delete_translation'.format(*info)
                )

            return [delete_path] + urlpatterns

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

            # Patch form_url to contain the "language" GET parameter.
            # Otherwise AdminModel.render_change_form will clean the URL
            # and remove the "language" when coming from a filtered object
            # list causing the wrong translation to be changed.

            params = request.GET.dict()
            params['language'] = lang_code
            form_url = add_preserved_filters({
                'preserved_filters': urlencode(params),
                'opts': self.model._meta
            }, form_url)

        # django-fluent-pages uses the same technique
        if 'default_change_form_template' not in context:
            context['default_change_form_template'] = self.default_change_form_template

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
        if redirect.status_code not in (301, 302):
            return redirect  # a 200 response likely.

        uri = iri_to_uri(request.path)
        opts = self.model._meta
        info = _get_model_meta(opts)

        # Pass ?language=.. to next page.
        language = request.GET.get(self.query_language_key)
        if language:
            continue_urls = (
                uri,
                "../add/",
                reverse('admin:{0}_{1}_add'.format(*info), current_app=self.admin_site.name),
            )
            redirect_parts = redirect['Location'].split('?')
            if redirect_parts[0] in continue_urls and self.query_language_key in request.GET:
                # "Save and add another" / "Save and continue" URLs
                delimiter = '&' if len(redirect_parts) > 1 else '?'
                redirect['Location'] += "{0}{1}={2}".format(delimiter, self.query_language_key, language)
        return redirect

    @csrf_protect_m
    @transaction.atomic
    def delete_translation(self, request, object_id, language_code):
        """
        The 'delete translation' admin view for this model.
        """
        opts = self.model._meta
        root_model = self.model._parler_meta.root_model

        # Get object and translation
        shared_obj = self.get_object(request, unquote(object_id))
        if shared_obj is None:
            raise Http404

        shared_obj.set_current_language(language_code)
        try:
            translation = root_model.objects.get(master=shared_obj, language_code=language_code)
        except root_model.DoesNotExist:
            raise Http404

        if not self.has_delete_permission(request, translation):
            raise PermissionDenied

        if len(self.get_available_languages(shared_obj)) <= 1:
            return self.deletion_not_allowed(request, translation, language_code)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.

        using = router.db_for_write(root_model)  # NOTE: all same DB for now.
        lang = get_language_title(language_code)

        # There are potentially multiple objects to delete;
        # the translation object at the base level,
        # and additional objects that can be added by inherited models.
        deleted_objects = []
        perms_needed = False
        protected = []

        # Extend deleted objects with the inlines.
        for qs in self.get_translation_objects(request, translation.language_code, obj=shared_obj, inlines=self.delete_inline_translations):
            if isinstance(qs, (list, tuple)):
                qs_opts = qs[0]._meta
            else:
                qs_opts = qs.model._meta

            deleted_result = get_deleted_objects(qs, qs_opts, request.user, self.admin_site, using)
            if django.VERSION >= (1, 8):
                (del2, model_counts, perms2, protected2) = deleted_result
            else:
                (del2, perms2, protected2) = deleted_result

            deleted_objects += del2
            perms_needed = perms_needed or perms2
            protected += protected2

        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = _('{0} translation of {1}').format(lang, force_text(translation))  # in hvad: (translation.master)

            self.log_deletion(request, translation, obj_display)
            self.delete_model_translation(request, translation)
            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % dict(
                name=force_text(opts.verbose_name), obj=force_text(obj_display)
            ))

            if self.has_change_permission(request, None):
                info = _get_model_meta(opts)
                return HttpResponseRedirect(reverse('admin:{0}_{1}_change'.format(*info), args=(object_id,), current_app=self.admin_site.name))
            else:
                return HttpResponseRedirect(reverse('admin:index', current_app=self.admin_site.name))

        object_name = _('{0} Translation').format(force_text(opts.verbose_name))
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

        # Small hack for django-polymorphic-tree.
        # This makes sure the breadcrumb renders correctly,
        # and avoids errors when the child model is not registered in the admin.
        if hasattr(self, 'base_model'):
            context.update({
                'base_opts': self.base_model._meta,
            })

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
            'object_name': force_text(opts.verbose_name)
        }
        return render(request, self.deletion_not_allowed_template, context)

    def delete_model_translation(self, request, translation):
        """
        Hook for deleting a translation.
        This calls :func:`get_translation_objects` to collect all related objects for the translation.
        By default, that includes the translations for inline objects.
        """
        master = translation.master
        for qs in self.get_translation_objects(request, translation.language_code, obj=master, inlines=self.delete_inline_translations):
            if isinstance(qs, (tuple, list)):
                # The objects are deleted one by one.
                # This triggers the post_delete signals and such.
                for obj in qs:
                    obj.delete()
            else:
                # Also delete translations of inlines which the user has access to.
                # This doesn't trigger signals, just like the regular
                qs.delete()

    def get_translation_objects(self, request, language_code, obj=None, inlines=True):
        """
        Return all objects that should be deleted when a translation is deleted.
        This method can yield all QuerySet objects or lists for the objects.
        """
        if obj is not None:
            # A single model can hold multiple TranslatedFieldsModel objects.
            # Return them all.
            for translations_model in obj._parler_meta.get_all_models():
                try:
                    translation = translations_model.objects.get(master=obj, language_code=language_code)
                except translations_model.DoesNotExist:
                    continue
                yield [translation]

        if inlines:
            for inline, qs in self._get_inline_translations(request, language_code, obj=obj):
                yield qs

    def _get_inline_translations(self, request, language_code, obj=None):
        """
        Fetch the inline translations
        """
        inline_instances = self.get_inline_instances(request, obj=obj)
        for inline in inline_instances:
            if issubclass(inline.model, TranslatableModelMixin):
                # leverage inlineformset_factory() to find the ForeignKey.
                # This also resolves the fk_name if it's set.
                fk = inline.get_formset(request, obj).fk

                rel_name = 'master__{0}'.format(fk.name)
                filters = {
                    'language_code': language_code,
                    rel_name: obj
                }

                for translations_model in inline.model._parler_meta.get_all_models():
                    qs = translations_model.objects.filter(**filters)
                    if obj is not None:
                        qs = qs.using(obj._state.db)

                    yield inline, qs

    @cached_property
    def default_change_form_template(self):
        """
        Determine what the actual `change_form_template` should be.
        """
        opts = self.model._meta
        app_label = opts.app_label
        return select_template_name((
            "admin/{0}/{1}/change_form.html".format(app_label, opts.object_name.lower()),
            "admin/{0}/change_form.html".format(app_label),
            "admin/change_form.html"
        ))


class TranslatableInlineModelAdmin(BaseTranslatableAdmin, InlineModelAdmin):
    """
    Base class for inline models.
    """
    #: The form to use.
    form = TranslatableModelForm
    #: The formset to use.
    formset = TranslatableBaseInlineFormSet

    @property
    def inline_tabs(self):
        """
        Whether to show inline tabs, can be set as attribute on the inline.
        """
        return not self._has_translatable_parent_model()

    def _has_translatable_parent_model(self):
        # Allow fallback to regular models when needed.
        return issubclass(self.parent_model, TranslatableModelMixin)

    def get_queryset_language(self, request):
        if not is_multilingual_project():
            # Make sure the current translations remain visible, not the dynamically set get_language() value.
            return appsettings.PARLER_LANGUAGES.get_default_language()
        else:
            # Set the initial language for fetched objects.
            # This is needed for the TranslatableInlineModelAdmin
            return self._language(request)

    def get_formset(self, request, obj=None, **kwargs):
        """
        Return the formset, and provide the language information to the formset.
        """
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
        """
        Return the current language for the currently displayed object fields.
        """
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
            # Hence, not looking at obj.get_available_languages(), but see what languages
            # are used by the inline objects that point to it.
            filter = {
                'master__{0}'.format(formset.fk.name): obj
            }
            return self.model._parler_meta.root_model.objects.using(obj._state.db).filter(**filter) \
                   .values_list('language_code', flat=True).distinct().order_by('language_code')
        else:
            return self.model._parler_meta.root_model.objects.none()


class TranslatableStackedInline(TranslatableInlineModelAdmin):
    """
    The inline class for stacked layout.
    """
    @property
    def template(self):
        if self.inline_tabs:
            return 'admin/parler/edit_inline/stacked_tabs.html'
        else:
            # Admin default
            return 'admin/edit_inline/stacked.html'


class TranslatableTabularInline(TranslatableInlineModelAdmin):
    """
    The inline class for tabular layout.
    """
    @property
    def template(self):
        if self.inline_tabs:
            return 'admin/parler/edit_inline/tabular_tabs.html'
        else:
            # Admin default
            return 'admin/edit_inline/tabular.html'


class SortedRelatedFieldListFilter(admin.RelatedFieldListFilter):
    """
    Override the standard :class:`~django.contrib.admin.RelatedFieldListFilter`,
    to sort the values after rendering their ``__unicode__()`` values.
    This can be used for translated models, which are difficult to sort beforehand.
    Usage:

    .. code-block:: python

        from django.contrib import admin
        from parler.admin import SortedRelatedFieldListFilter

        class MyAdmin(admin.ModelAdmin):

            list_filter = (
                ('related_field_name', SortedRelatedFieldListFilter),
            )
    """

    def __init__(self, *args, **kwargs):
        super(SortedRelatedFieldListFilter, self).__init__(*args, **kwargs)
        self.lookup_choices = sorted(self.lookup_choices, key=lambda a: a[1].lower())


if django.VERSION >= (1, 7):
    def _get_model_meta(opts):
        return opts.app_label, opts.model_name
else:
    def _get_model_meta(opts):
        return opts.app_label, opts.module_name
