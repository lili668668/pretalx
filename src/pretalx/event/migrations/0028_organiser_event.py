# Generated by Django 3.2.8 on 2021-10-16 17:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0027_alter_event_organiser'),
    ]

    operations = [
        migrations.AddField(
            model_name='organiser',
            name='event',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='organisers', to='event.event'),
        ),
    ]
