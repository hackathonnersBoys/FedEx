# Generated by Django 5.1.3 on 2024-12-11 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0034_driver_truck_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mms',
            name='dedicated_phone_number',
        ),
        migrations.AddField(
            model_name='mms',
            name='dedicated_phone_numbers',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='mms',
            name='name',
            field=models.CharField(default='', max_length=255),
        ),
    ]
