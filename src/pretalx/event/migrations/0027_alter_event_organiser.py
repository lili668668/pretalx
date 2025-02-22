# Generated by Django 3.2.8 on 2021-10-16 17:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0026_team_force_hide_speaker_names'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='organiser',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='events', to='event.organiser'),
        ),
    ]
