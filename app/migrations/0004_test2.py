# Generated by Django 4.2 on 2023-05-06 23:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_test_delete_immudbmodel'),
    ]

    operations = [
        migrations.CreateModel(
            name='TEST2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('verified', models.BooleanField(default=False)),
                ('create_multi', models.JSONField(blank=True, null=True)),
                ('key', models.CharField(default='Fj15d4oJ4Wbds96eltnqrIzTPX1V0R1Q4Wre', max_length=255)),
                ('nome', models.CharField(max_length=155)),
                ('ok', models.IntegerField()),
            ],
            options={
                'abstract': False,
                'managed': False,
            },
        ),
    ]
