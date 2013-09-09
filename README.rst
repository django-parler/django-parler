django-parler
=============

Simple Django model translations without nasty hacks, featuring nice admin integration.


Installation
============

First install the module, preferably in a virtual environment::

    git clone https://github.com/edoburu/django-parler.git
    cd django-parler
    pip install .

Configuration
-------------

Next, create a project which uses the app::

    cd ..
    django-admin.py startproject parlerdemo

Add the following settings::

    INSTALLED_APPS += (
        'parler',
    )

Extend from the translation classes.


Contributing
------------

This module is designed to be generic. In case there is anything you didn't like about it,
or think it's not flexible enough, please let us know. We'd love to improve it!

If you have any other valuable contribution, suggestion or idea,
please let us know as well because we will look into it.
Pull requests are welcome too. :-)
