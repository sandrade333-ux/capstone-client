from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.billing.models import DisputeRecord, Invoice, VoidRequest
from apps.crm.models import Contact


class BillingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("sam", "sam@test.com", "testpass123")
        self.contact = Contact.objects.create(first_name="Test", last_name="Client", email="c@c.com")
        self.client = Client()

    def _make_invoice(self, status, number):
        return Invoice.objects.create(
            invoice_number=number, contact=self.contact, status=status,
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )

    def test_request_void_requires_login(self):
        inv = self._make_invoice("sent", "INV-LOGIN")
        resp = self.client.get(reverse("billing:void_request", args=[inv.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_request_void_wrong_status(self):
        self.client.login(username="sam", password="testpass123")
        inv = self._make_invoice("draft", "INV-WRONG")
        resp = self.client.post(
            reverse("billing:void_request", args=[inv.pk]),
            {"reason": "test"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_request_void_creates_record(self):
        self.client.login(username="sam", password="testpass123")
        inv = self._make_invoice("sent", "INV-VOID")
        resp = self.client.post(
            reverse("billing:void_request", args=[inv.pk]),
            {"reason": "Customer cancelled"},
        )
        self.assertEqual(resp.status_code, 302)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "void_pending")
        self.assertTrue(VoidRequest.objects.filter(invoice=inv).exists())

    def test_dispute_requires_void_rejected(self):
        self.client.login(username="sam", password="testpass123")
        inv = self._make_invoice("sent", "INV-NDISP")
        resp = self.client.get(reverse("billing:dispute", args=[inv.pk]))
        self.assertEqual(resp.status_code, 400)

    def test_dispute_creates_record(self):
        self.client.login(username="sam", password="testpass123")
        inv = self._make_invoice("void_rejected", "INV-DISP")
        VoidRequest.objects.create(invoice=inv, reason="original", status="rejected")
        resp = self.client.post(
            reverse("billing:dispute", args=[inv.pk]),
            {"dispute_reason": "I disagree because..."},
        )
        self.assertEqual(resp.status_code, 302)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "disputed")
        self.assertTrue(DisputeRecord.objects.filter(void_request__invoice=inv).exists())

    def test_invoice_detail_shows_actions(self):
        self.client.login(username="sam", password="testpass123")
        inv = self._make_invoice("void_rejected", "INV-DETAIL")
        VoidRequest.objects.create(invoice=inv, reason="test", status="rejected", reviewer_note="No.")
        resp = self.client.get(reverse("billing:invoice_detail", args=[inv.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dispute This Decision")
