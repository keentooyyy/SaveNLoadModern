# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SaveNLoad', '0004_convert_save_file_location_to_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='path_mappings',
            field=models.JSONField(blank=True, default=dict, help_text="Mapping of local save path to path_index (1,2,3...). e.g., {'C:\\\\path1': 1, 'C:\\\\path2': 2}"),
        ),
    ]
