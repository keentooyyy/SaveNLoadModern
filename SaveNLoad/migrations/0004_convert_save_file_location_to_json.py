# Generated migration
from django.db import migrations, models
import json


def convert_save_file_location_to_json(apps, schema_editor):
    """
    Convert save_file_location (CharField with newline-separated paths) 
    to save_file_locations (JSONField with array of paths)
    All single paths are converted to single-element arrays: ["path"]
    """
    Game = apps.get_model('SaveNLoad', 'Game')
    
    for game in Game.objects.all():
        # Access the old field directly
        old_location = getattr(game, 'save_file_location', None)
        
        if old_location:
            # Strip whitespace
            save_file_location = str(old_location).strip()
            
            if save_file_location:
                # Check if it contains newlines (multiple paths)
                if '\n' in save_file_location or '\r\n' in save_file_location:
                    # Multiple paths - split by newline
                    # Handle both \n and \r\n
                    locations = []
                    for line in save_file_location.splitlines():
                        path = line.strip()
                        if path:  # Only add non-empty paths
                            locations.append(path)
                else:
                    # Single path - create array with one item
                    locations = [save_file_location]
            else:
                # Empty string - set to empty array
                locations = []
        else:
            # None or empty - set to empty array
            locations = []
        
        # Update the game with the new JSON field
        game.save_file_locations = locations
        game.save(update_fields=['save_file_locations'])
        
        # Debug output (optional - remove in production)
        print(f"Migrated game '{game.name}': {len(locations)} path(s)")


def reverse_convert_save_file_location_to_json(apps, schema_editor):
    """
    Reverse migration: Convert save_file_locations (JSONField) back to save_file_location (CharField)
    """
    Game = apps.get_model('SaveNLoad', 'Game')
    
    for game in Game.objects.all():
        locations = getattr(game, 'save_file_locations', None)
        
        if locations:
            # Join array with newlines, or use first item if single path
            if isinstance(locations, list) and len(locations) > 0:
                if len(locations) == 1:
                    # Single path - store as string
                    game.save_file_location = str(locations[0])
                else:
                    # Multiple paths - join with newline
                    game.save_file_location = '\n'.join(str(loc) for loc in locations if loc)
            else:
                game.save_file_location = ''
        else:
            game.save_file_location = ''
        
        game.save(update_fields=['save_file_location'])


class Migration(migrations.Migration):

    dependencies = [
        ('SaveNLoad', '0003_add_path_index_to_operation_queue'),
    ]

    operations = [
        # Step 1: Add the new JSONField (nullable first, we'll populate it)
        migrations.AddField(
            model_name='game',
            name='save_file_locations',
            field=models.JSONField(default=list, help_text='List of save file location paths (array of strings)'),
        ),
        # Step 2: Migrate data from old field to new field
        migrations.RunPython(
            convert_save_file_location_to_json,
            reverse_convert_save_file_location_to_json,
        ),
        # Step 3: Remove the old CharField
        migrations.RemoveField(
            model_name='game',
            name='save_file_location',
        ),
    ]

