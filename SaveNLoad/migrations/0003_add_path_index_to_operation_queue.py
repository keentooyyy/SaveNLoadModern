# Generated migration
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SaveNLoad', '0002_game_banner_url_alter_game_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='operationqueue',
            name='path_index',
            field=models.IntegerField(blank=True, help_text='Index for multiple save locations (1-based, creates path_1, path_2 subfolders)', null=True),
        ),
    ]
