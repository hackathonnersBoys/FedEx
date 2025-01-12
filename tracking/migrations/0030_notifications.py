# Generated by Django 5.1.3 on 2024-12-10 20:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0029_remove_truck_log_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notifications',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('truck_id', models.CharField(max_length=100)),
                ('issue', models.CharField(max_length=100)),
                ('is_resolved', models.BooleanField(default=0)),
            ],
        ),
    ]
