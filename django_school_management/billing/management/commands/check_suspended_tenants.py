from django.core.management.base import BaseCommand
from django_school_management.billing.services import SuspensionService

class Command(BaseCommand):
    help = 'Checks for past_due subscriptions exceeding the grace period and suspends the tenant.'

    def handle(self, *args, **options):
        self.stdout.write('Running daily suspension check...')
        suspended_count = SuspensionService.check_and_suspend_past_due_tenants()
        
        if suspended_count > 0:
            self.stdout.write(self.style.WARNING(f'Successfully suspended {suspended_count} tenant(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('No tenants required suspension today.'))
