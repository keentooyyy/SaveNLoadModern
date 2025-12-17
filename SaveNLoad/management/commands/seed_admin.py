"""
Django management command to create a default admin user from environment variables
Usage: python manage.py seed_admin
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from SaveNLoad.models.user import SimpleUsers, UserRole
import os
import logging

logger = logging.getLogger(__name__)


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
            self.stdout.write(
                self.style.ERROR('❌ DEFAULT_ADMIN_USERNAME environment variable is not set')
            )
            return

        if not admin_email:
            self.stdout.write(
                self.style.ERROR('❌ DEFAULT_ADMIN_EMAIL environment variable is not set')
            )
            return

        if not admin_password:
            self.stdout.write(
                self.style.ERROR('❌ DEFAULT_ADMIN_PASSWORD environment variable is not set')
            )
            return

        # Check if admin user already exists
        try:
            existing_user = SimpleUsers.objects.get(username=admin_username)
            
            if options['update']:
                # Update existing user
                existing_user.email = admin_email
                existing_user.set_password(admin_password)
                existing_user.role = UserRole.ADMIN
                existing_user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Updated admin user: {admin_username} (email: {admin_email})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Admin user "{admin_username}" already exists. Use --update flag to update it.'
                    )
                )
            return

        except SimpleUsers.DoesNotExist:
            # User doesn't exist, create new admin
            pass

        # Check if email is already taken by another user
        try:
            existing_email = SimpleUsers.objects.get(email=admin_email)
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Email "{admin_email}" is already registered to user "{existing_email.username}"'
                )
            )
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

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Successfully created admin user: {admin_username} (email: {admin_email})'
                )
            )
            logger.info(f'Default admin user created: {admin_username}')

        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to create admin user: {str(e)}')
            )
            logger.error(f'Failed to create admin user: {str(e)}')

