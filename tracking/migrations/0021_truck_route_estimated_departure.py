# Generated by Django 5.1.3 on 2024-12-07 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0020_remove_truck_log_timestamp_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='truck',
            name='route_estimated_departure',
            field=models.TextField(default=''),
        ),
    ]
