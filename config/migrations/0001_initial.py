# Generated by Django 4.2.4 on 2023-09-30 07:10

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keycloak_base_url', models.URLField()),
                ('keycloak_port', models.PositiveSmallIntegerField()),
                ('keycloak_ssl', models.BooleanField(default=True)),
                ('keycloak_client_id', models.CharField(max_length=200)),
                ('keycloak_secret', models.CharField(max_length=200)),
                ('keycloak_realm', models.CharField(max_length=100)),
                ('daas_provider_baseurl', models.CharField(default='localhost', max_length=200, null=True)),
            ],
        ),
    ]
