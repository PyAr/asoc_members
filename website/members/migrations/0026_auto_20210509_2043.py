# Generated by Django 3.1.8 on 2021-05-09 20:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0025_auto_20200522_1235'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='member',
            options={'get_latest_by': 'modified'},
        ),
        migrations.AlterModelOptions(
            name='organization',
            options={'get_latest_by': 'modified'},
        ),
        migrations.AlterModelOptions(
            name='patron',
            options={'get_latest_by': 'modified'},
        ),
        migrations.AlterModelOptions(
            name='paymentstrategy',
            options={'get_latest_by': 'modified'},
        ),
        migrations.AlterModelOptions(
            name='person',
            options={'get_latest_by': 'modified'},
        ),
    ]