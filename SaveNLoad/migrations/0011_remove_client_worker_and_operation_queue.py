# Generated migration to remove ClientWorker and OperationQueue models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('SaveNLoad', '0010_alter_clientworker_options_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ClientWorker',
        ),
        migrations.DeleteModel(
            name='OperationQueue',
        ),
    ]

