import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()

from django.core.management.base import BaseCommand
from customer.models import Party
from django.db.models import Count


class Command(BaseCommand):
    help = "Find duplicated TRN values in Party"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # Find duplicated TRN values (excluding null/blank)
        duplicates = (
            Party.objects
            .exclude(trn__isnull=True)
            .exclude(trn__exact="")
            .values('trn')
            .annotate(trn_count=Count('id'))
            .filter(trn_count__gt=1)
        )
        if not duplicates:
            print("No duplicated TRN found.")
            return

        print("Duplicated TRN values in Party:")
        for dup in duplicates:
            trn = dup['trn']
            parties = Party.objects.filter(trn=trn)
            names = ", ".join([p.name for p in parties])
            Types = ", ".join([p.type for p in parties])
            print(f"TRN: {trn} | Count: {dup['trn_count']} | Parties: {names} | Type: {Types}")

if __name__ == "__main__":
    command = Command()
    command.handle(dry_run=False)