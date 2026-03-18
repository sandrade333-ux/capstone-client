"""Seed demo data. Idempotent — safe to run multiple times."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed demo data: company, contacts, jobs, invoices."

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from apps.billing.models import Invoice, LineItem, VoidRequest
        from apps.crm.models import Company, Contact
        from apps.jobs.models import Job

        User = get_user_model()

        now = timezone.now()

        # Company
        company, _ = Company.objects.get_or_create(
            name="Entropy Opposition LLC",
            defaults={"address": "42 Flux St, Portland, OR 97201", "phone": "503-555-0142", "email": "info@entropyopposition.com"},
        )
        self.stdout.write(f"  Company: {company.name}")

        # Contacts
        sam, _ = Contact.objects.get_or_create(
            first_name="Sam", last_name="Anthony",
            defaults={"email": "sam@entropyopposition.com", "phone": "503-555-0101", "company": company, "source": "referral"},
        )
        maria, _ = Contact.objects.get_or_create(
            first_name="Maria", last_name="Chen",
            defaults={"email": "maria@example.com", "phone": "503-555-0202", "source": "website"},
        )
        pete, _ = Contact.objects.get_or_create(
            first_name="Pete", last_name="Kowalski",
            defaults={"email": "pete@example.com", "phone": "503-555-0303", "company": company, "source": "phone"},
        )
        self.stdout.write(f"  Contacts: {sam}, {maria}, {pete}")

        # Jobs
        job1, _ = Job.objects.get_or_create(
            title="Chimney inspection at 123 Main St",
            defaults={"description": "Annual inspection and cleaning", "status": "completed", "company": company, "contact": sam, "actual_start": now, "actual_end": now},
        )
        job2, _ = Job.objects.get_or_create(
            title="Fireplace liner repair at 456 Oak Ave",
            defaults={"description": "Replace cracked liner section", "status": "in_progress", "company": company, "contact": maria, "scheduled_start": now},
        )
        self.stdout.write(f"  Jobs: {job1}, {job2}")

        # Invoices
        inv1, created1 = Invoice.objects.get_or_create(
            invoice_number="INV-2026-0001",
            defaults={"contact": sam, "job": job1, "status": "paid", "issued_at": now, "paid_at": now, "subtotal": Decimal("275.00"), "total": Decimal("275.00")},
        )
        if created1:
            LineItem.objects.get_or_create(
                invoice=inv1, description="Annual chimney inspection",
                defaults={"quantity": Decimal("1.00"), "unit_price": Decimal("275.00"), "amount": Decimal("275.00")},
            )

        inv2, created2 = Invoice.objects.get_or_create(
            invoice_number="INV-2026-0002",
            defaults={"contact": maria, "job": job2, "status": "sent", "issued_at": now, "subtotal": Decimal("850.00"), "tax": Decimal("68.00"), "total": Decimal("918.00")},
        )
        if created2:
            LineItem.objects.get_or_create(
                invoice=inv2, description="Fireplace liner (12ft stainless)",
                defaults={"quantity": Decimal("1.00"), "unit_price": Decimal("650.00"), "amount": Decimal("650.00")},
            )
            LineItem.objects.get_or_create(
                invoice=inv2, description="Installation labor (2 hours)",
                defaults={"quantity": Decimal("2.00"), "unit_price": Decimal("100.00"), "amount": Decimal("200.00")},
            )

        self.stdout.write(f"  Invoices: {inv1}, {inv2}")

        # Third invoice — overdue, with a pending void request for demo
        inv3, created3 = Invoice.objects.get_or_create(
            invoice_number="INV-2026-0003",
            defaults={
                "contact": pete, "status": "void_pending",
                "issued_at": now, "subtotal": Decimal("425.00"),
                "total": Decimal("425.00"),
            },
        )
        if created3:
            LineItem.objects.get_or_create(
                invoice=inv3, description="Emergency flue repair",
                defaults={"quantity": Decimal("1.00"), "unit_price": Decimal("425.00"), "amount": Decimal("425.00")},
            )
        # Pending void request — the governance demo
        owner = User.objects.filter(is_superuser=True).first()
        if inv3.status == "void_pending" and not VoidRequest.objects.filter(invoice=inv3).exists():
            VoidRequest.objects.create(
                invoice=inv3,
                requested_by=owner,
                reason="Customer cancelled the job before work started. Full refund requested.",
            )
            self.stdout.write("  Void request: pending for INV-2026-0003")

        self.stdout.write(self.style.SUCCESS("Seed complete."))
