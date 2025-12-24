"""
Django management command to create a default admin user from environment variables
Usage: python manage.py seed_admin
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError, OperationalError, ProgrammingError
from SaveNLoad.models.user import SimpleUsers, UserRole
import os


class Command(BaseCommand):
    help = 'Creates a default admin user from environment variables (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing admin user if it exists',
        )

    def handle(self, *args, **options):
        # Get admin credentials from environment variables
        admin_username = os.getenv('DEFAULT_ADMIN_USERNAME')
        admin_email = os.getenv('DEFAULT_ADMIN_EMAIL')
        admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD')

        # Check if all required environment variables are set
        if not admin_username:
            print('DEFAULT_ADMIN_USERNAME environment variable is not set')
            return

        if not admin_email:
            print('DEFAULT_ADMIN_EMAIL environment variable is not set')
            return

        if not admin_password:
            print('DEFAULT_ADMIN_PASSWORD environment variable is not set')
            return

        # Check if database tables exist (migrations may not have been run)
        try:
            # Try a simple query to check if table exists
            SimpleUsers.objects.first()
        except (OperationalError, ProgrammingError) as e:
            error_msg = str(e).lower()
            if 'does not exist' in error_msg or 'relation' in error_msg:
                print('ERROR: Database tables do not exist. Please run migrations first:')
                print('  python manage.py makemigrations')
                print('  python manage.py migrate')
                print(f'ERROR: Database tables do not exist: {str(e)}')
                return
            else:
                # Re-raise if it's a different database error
                raise

        # Check if admin user already exists
        try:
            existing_user = SimpleUsers.objects.get(username=admin_username)
            
            if options['update']:
                # Update existing user
                existing_user.email = admin_email
                existing_user.set_password(admin_password)
                existing_user.role = UserRole.ADMIN
                existing_user.save()
                
                print(f'Updated admin user: {admin_username} (email: {admin_email})')
            else:
                print(f'Admin user "{admin_username}" already exists. Use --update flag to update it.')
            return

        except SimpleUsers.DoesNotExist:
            # User doesn't exist, create new admin
            pass

        # Check if email is already taken by another user
        try:
            existing_email = SimpleUsers.objects.get(email=admin_email)
            print(f'Email "{admin_email}" is already registered to user "{existing_email.username}"')
            return
        except SimpleUsers.DoesNotExist:
            # Email is available
            pass

        # Create new admin user
        try:
            admin_user = SimpleUsers.objects.create(
                username=admin_username,
                email=admin_email,
                role=UserRole.ADMIN
            )
            admin_user.set_password(admin_password)
            admin_user.save()

            print(f'Successfully created admin user: {admin_username} (email: {admin_email})')
            print(f'Default admin user created: {admin_username}')

        except IntegrityError as e:
            print(f'Failed to create admin user: {str(e)}')
            print(f'ERROR: Failed to create admin user: {str(e)}')

