# Generated by Django 4.2.13 on 2024-07-01 20:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_transaction_bankrupcy_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='bankrupcy',
        ),
    ]