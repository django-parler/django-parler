# django-parler

Reusable Django library that adds model-level translation support via a separate `*Translation` table per model. No runnable server — this is a Django app package.

## Tech Stack

- **Language**: Python 3.6–3.10
- **Framework**: Django 2.2 / 3.x / 4.0
- **Formatting**: black (line-length 99) + isort (profile=black)
- **Testing**: Django test runner via `runtests.py` (not pytest)
- **Coverage**: coverage + codecov (`.coveragerc`)
- **CI**: GitHub Actions (`.github/workflows/tests.yaml`)
- **Docs**: Sphinx + RTD theme (`docs/`)

## Build & Run

```bash
# Install in editable mode with test extras
pip install -e .[tests]

# Run all tests
python runtests.py

# Run tests for a specific app
python runtests.py parler
python runtests.py article

# Coverage
coverage run --rcfile=.coveragerc runtests.py && coverage report

# Full tox matrix (Python 3.6-3.10 × Django 2.2-4.0)
tox

# Format
black . && isort .

# Build docs
cd docs && make html
```

## Project Structure

```
parler/             ← Main package (all production code lives here)
  models.py         ← TranslatableModel, TranslatedFields, TranslatedFieldsModel
  managers.py       ← TranslatableManager + QuerySet
  fields.py         ← TranslatedField descriptor
  cache.py          ← Translation caching layer
  admin.py          ← TranslatableAdmin, language tab UI
  forms.py          ← TranslatableModelForm
  views.py          ← View mixins
  signals.py        ← pre/post_translation_save signals
  appsettings.py    ← All PARLER_* settings with defaults
  utils/            ← Language helpers (conf, context, i18n, template, views)
  templatetags/     ← parler_tags.py
  tests/
    testapp/        ← Minimal Django app used only in tests
    test_*.py       ← Test modules per concern
example/article/    ← Working usage example
runtests.py         ← Test runner (configures in-memory SQLite Django project)
```

## Conventions

- **Formatting**: black (line-length 99) + isort before every commit
- **Tests**: `test_<concern>.py`, Django `TestCase`, no pytest
- **Commits**: conventional style — `feat:`, `fix:`, `docs:`, PR number in body `(#NNN)`
- **Settings**: always add new settings to `parler/appsettings.py` with a `getattr(settings, "PARLER_...", default)` pattern
- **Errors**: `TranslationDoesNotExist` (subclass of `ObjectDoesNotExist`) for missing translation rows

## Key Concepts

- `TranslatableModel` + `TranslatedFields(...)` → metaclass generates a `*Translation` DB table
- `TranslatedField` descriptor → proxies attribute access to the current-language translation row
- Translation rows are cached in Django's cache framework; key includes `PARLER_CACHE_PREFIX`
- Language fallback chain configured via `PARLER_LANGUAGES` in Django settings
