# Generated by Django 3.2.8 on 2021-11-27 01:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('submission', '0063_remove_track_color'),
        ('person', '0029_contact_track'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='speakerinformation',
            name='limit_types',
        ),
        migrations.AlterField(
            model_name='contact',
            name='track',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='submission.track'),
        ),
    ]
