# Generated by Django 5.1.3 on 2024-12-11 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0033_notifications_is_on_route'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='truck_id',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
