# Generated by Django 3.2.6 on 2021-08-29 21:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_directories'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdirectory',
            name='name',
            field=models.TextField(default=str, unique=True),
        ),
        migrations.AlterField(
            model_name='userconnection',
            name='directory',
            field=models.ForeignKey(help_text='This refers to the directory used to log in the user', on_delete=django.db.models.deletion.CASCADE, related_name='connected_users', to='accounts.userdirectory'),
        ),
        migrations.AlterField(
            model_name='userconnection',
            name='directory_key',
            field=models.TextField(help_text='This is the unique ID provided by the directory to identify this user'),
        ),
        migrations.AlterField(
            model_name='userconnection',
            name='latest_directory_data',
            field=models.JSONField(blank=True, help_text='This field contains the newest known data about this user. It might be outdated, though.', null=True),
        ),
        migrations.AlterField(
            model_name='userconnection',
            name='user',
            field=models.ForeignKey(help_text='This refers to a user who can be logged in using a directory', on_delete=django.db.models.deletion.CASCADE, related_name='connections', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='userdirectory',
            name='description',
            field=models.TextField(blank=True, default=str),
        ),
        migrations.AddConstraint(
            model_name='userconnection',
            constraint=models.UniqueConstraint(fields=('directory', 'directory_key'), name='unique_directory_key'),
        ),
    ]