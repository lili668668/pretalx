# Generated by Django 3.2.8 on 2021-11-14 12:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submission', '0062_auto_20211024_1251'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='track',
            name='color',
        ),
    ]
