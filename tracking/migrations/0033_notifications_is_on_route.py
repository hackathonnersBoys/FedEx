# Generated by Django 5.1.3 on 2024-12-10 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0032_rename_geofence_notifications_geofence_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='notifications',
            name='is_on_route',
            field=models.BooleanField(default=1),
        ),
    ]