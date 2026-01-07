from django.db import migrations, models
import django.db.models.deletion


def seed_system_settings(apps, schema_editor):
    SystemSetting = apps.get_model('SaveNLoad', 'SystemSetting')
    defaults = {
        'feature.rawg.enabled': False,
        'feature.email.enabled': False,
        'feature.email.registration_required': True,
        'feature.guest.enabled': False,
        'feature.guest.ttl_days': 14,
        'rawg.api_key': '',
        'email.gmail_user': '',
        'email.gmail_app_password': '',
        'reset.default_password': '',
    }
    for key, value in defaults.items():
        SystemSetting.objects.update_or_create(key=key, defaults={'value': value})


class Migration(migrations.Migration):

    dependencies = [
        ('SaveNLoad', '0013_refreshtoken'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=200, unique=True)),
                ('value', models.JSONField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='SaveNLoad.simpleusers')),
            ],
            options={
                'db_table': 'system_settings',
                'verbose_name': 'System Setting',
                'verbose_name_plural': 'System Settings',
            },
        ),
        migrations.AddField(
            model_name='simpleusers',
            name='guest_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='simpleusers',
            name='guest_migration_status',
            field=models.CharField(blank=True, choices=[('migrating', 'Migrating'), ('failed', 'Failed')], max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='simpleusers',
            name='guest_namespace',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='simpleusers',
            name='guest_pending_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='simpleusers',
            name='guest_pending_password',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='simpleusers',
            name='guest_pending_username',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='simpleusers',
            name='is_guest',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(seed_system_settings, migrations.RunPython.noop),
    ]
