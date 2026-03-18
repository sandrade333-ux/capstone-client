from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.billing.models import DisputeRecord, Invoice, LineItem, VoidRequest
from apps.crm.models import Contact


class InvoicePropertyTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(first_name="Test", last_name="User", email="t@t.com")

    def _make_invoice(self, status, number=None):
        return Invoice.objects.create(
            invoice_number=number or f"INV-{status}",
            contact=self.contact,
            status=status,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )

    def test_can_request_void_sent(self):
        inv = self._make_invoice("sent")
        self.assertTrue(inv.can_request_void)

    def test_can_request_void_overdue(self):
        inv = self._make_invoice("overdue", "INV-overdue")
        self.assertTrue(inv.can_request_void)

    def test_can_request_void_draft(self):
        inv = self._make_invoice("draft")
        self.assertFalse(inv.can_request_void)

    def test_can_request_void_paid(self):
        inv = self._make_invoice("paid")
        self.assertFalse(inv.can_request_void)

    def test_can_dispute_void_rejected(self):
        inv = self._make_invoice("void_rejected")
        self.assertTrue(inv.can_dispute)

    def test_can_dispute_pending(self):
        inv = self._make_invoice("void_pending")
        self.assertFalse(inv.can_dispute)

    def test_is_settled_paid(self):
        inv = self._make_invoice("paid", "INV-settled")
        self.assertTrue(inv.is_settled)

    def test_is_settled_void_pending(self):
        inv = self._make_invoice("void_pending", "INV-not-settled")
        self.assertFalse(inv.is_settled)


class VoidRequestStrTests(TestCase):
    def test_str_contains_invoice(self):
        contact = Contact.objects.create(first_name="A", email="a@a.com")
        inv = Invoice.objects.create(
            invoice_number="INV-STR", contact=contact, status="sent",
            subtotal=Decimal("50.00"), total=Decimal("50.00"),
        )
        vr = VoidRequest.objects.create(invoice=inv, reason="Test")
        self.assertIn("INV-STR", str(vr))


class DisputeStrTests(TestCase):
    def test_str_contains_invoice(self):
        contact = Contact.objects.create(first_name="B", email="b@b.com")
        inv = Invoice.objects.create(
            invoice_number="INV-DISP", contact=contact, status="void_rejected",
            subtotal=Decimal("50.00"), total=Decimal("50.00"),
        )
        vr = VoidRequest.objects.create(invoice=inv, reason="Test", status="rejected")
        dispute = DisputeRecord.objects.create(void_request=vr, dispute_reason="Disagree")
        self.assertIn("INV-DISP", str(dispute))
