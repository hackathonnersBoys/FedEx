# Generated by Django 5.1.3 on 2024-12-11 22:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0035_remove_mms_dedicated_phone_number_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('load', models.IntegerField(default=0)),
                ('unload', models.IntegerField(default=0)),
            ],
        ),
    ]
