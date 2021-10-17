# Generated by Django 3.2.8 on 2021-10-17 03:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0031_alter_event_organiser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='organiser',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='event', to='event.organiser'),
        ),
    ]
