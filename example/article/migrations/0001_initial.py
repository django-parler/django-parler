# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('published', models.BooleanField(default=False, verbose_name='Is published')),
            ],
            options={
                'verbose_name': 'Article',
                'verbose_name_plural': 'Articles',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ArticleTranslation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('language_code', models.CharField(db_index=True, max_length=15, verbose_name='Language')),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('slug', models.SlugField(verbose_name='Slug')),
                ('content', models.TextField()),
                ('master', models.ForeignKey(to='article.Article', null=True, related_name='translations', editable=False, on_delete=models.CASCADE)),
            ],
            options={
                'default_permissions': (),
                'managed': True,
                'db_table': 'article_article_translation',
                'verbose_name': 'Article Translation',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='articletranslation',
            unique_together=set([('slug', 'language_code'), ('language_code', 'master')]),
        ),
        migrations.AddField(
            model_name='article',
            name='category',
            field=models.ForeignKey(to='article.Category', null=True, blank=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='StackedCategory',
            fields=[
            ],
            options={
                'verbose_name': 'Stacked Category',
                'proxy': True,
                'verbose_name_plural': 'Stacked Categories',
            },
            bases=('article.category',),
        ),
        migrations.CreateModel(
            name='TabularCategory',
            fields=[
            ],
            options={
                'verbose_name': 'Tabular Category',
                'proxy': True,
                'verbose_name_plural': 'Tabular Categories',
            },
            bases=('article.category',),
        ),
    ]
