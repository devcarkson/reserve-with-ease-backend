from django.core.management.base import BaseCommand
from accounts.models import EmailVerification, PasswordReset, Wishlist
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Clean up orphaned verification tokens from deleted users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('DRY RUN - No changes will be made')
            self.stdout.write('')
        
        # Find orphaned EmailVerification records
        orphaned_ev = EmailVerification.objects.filter(user__isnull=True)
        ev_count = orphaned_ev.count()
        
        if ev_count > 0:
            self.stdout.write(f'Orphaned EmailVerification records: {ev_count}')
            if not dry_run:
                deleted_ev, _ = orphaned_ev.delete()
                self.stdout.write(f'Deleted: {deleted_ev}')
        else:
            self.stdout.write('No orphaned EmailVerification records found')
        
        # Find orphaned PasswordReset records
        orphaned_pr = PasswordReset.objects.filter(user__isnull=True)
        pr_count = orphaned_pr.count()
        
        if pr_count > 0:
            self.stdout.write(f'Orphaned PasswordReset records: {pr_count}')
            if not dry_run:
                deleted_pr, _ = orphaned_pr.delete()
                self.stdout.write(f'Deleted: {deleted_pr}')
        else:
            self.stdout.write('No orphaned PasswordReset records found')
        
        # Find orphaned Wishlist records
        orphaned_wl = Wishlist.objects.filter(user__isnull=True)
        wl_count = orphaned_wl.count()
        
        if wl_count > 0:
            self.stdout.write(f'Orphaned Wishlist records: {wl_count}')
            if not dry_run:
                deleted_wl, _ = orphaned_wl.delete()
                self.stdout.write(f'Deleted: {deleted_wl}')
        else:
            self.stdout.write('No orphaned Wishlist records found')
        
        # Also clean up expired tokens (older than 7 days)
        from django.utils import timezone
        from datetime import timedelta
        
        expired_threshold = timezone.now() - timedelta(days=7)
        
        # Clean up expired EmailVerification tokens
        expired_ev = EmailVerification.objects.filter(
            created_at__lt=expired_threshold,
            is_used=False
        )
        ev_expired_count = expired_ev.count()
        
        if ev_expired_count > 0:
            self.stdout.write(f'Expired EmailVerification records: {ev_expired_count}')
            if not dry_run:
                deleted_expired_ev, _ = expired_ev.delete()
                self.stdout.write(f'Deleted: {deleted_expired_ev}')
        
        # Clean up expired PasswordReset tokens
        expired_pr = PasswordReset.objects.filter(
            created_at__lt=expired_threshold,
            is_used=False
        )
        pr_expired_count = expired_pr.count()
        
        if pr_expired_count > 0:
            self.stdout.write(f'Expired PasswordReset records: {pr_expired_count}')
            if not dry_run:
                deleted_expired_pr, _ = expired_pr.delete()
                self.stdout.write(f'Deleted: {deleted_expired_pr}')
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write('DRY RUN COMPLETE - No changes were made')
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Cleanup completed successfully!'))
