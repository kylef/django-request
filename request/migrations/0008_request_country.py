# Generated by Django 4.1.4 on 2022-12-25 16:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0007_alter_request_is_ajax'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='country',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='country'),
        ),
    ]
