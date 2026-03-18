import hashlib
import hmac
import json
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.billing.models import DisputeRecord, Invoice, VoidRequest
from apps.crm.models import Contact
from apps.sync.models import SyncConfiguration


class SyncInboundTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(first_name="Sync", last_name="Test", email="s@s.com")
        self.config = SyncConfiguration.objects.create(
            control_plane_url="https://guildhouse.example.com/api/v1/capstone/inbound/",
            shared_secret="test-secret-123",
            instance_id="test-instance",
            is_active=True,
        )
        self.client = Client()

    def _make_invoice(self, number, status="sent"):
        return Invoice.objects.create(
            invoice_number=number, contact=self.contact, status=status,
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )

    def _signed_post(self, payload_dict):
        body = json.dumps(payload_dict, sort_keys=True).encode()
        sig = "sha256=" + hmac.new(b"test-secret-123", body, hashlib.sha256).hexdigest()
        return self.client.post(
            reverse("sync:sync_inbound"),
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )

    def test_void_approved_handler(self):
        inv = self._make_invoice("INV-APPROVE")
        inv.status = "void_pending"
        inv.save(update_fields=["status"])
        VoidRequest.objects.create(invoice=inv, reason="please void")

        resp = self._signed_post({
            "event": "invoice.void_approved",
            "data": {"invoice_id": str(inv.pk), "note": "Approved by Tyler"},
        })
        self.assertEqual(resp.status_code, 200)

        inv.refresh_from_db()
        self.assertEqual(inv.status, "void")
        vr = VoidRequest.objects.get(invoice=inv)
        self.assertEqual(vr.status, "approved")

    def test_void_rejected_handler(self):
        inv = self._make_invoice("INV-REJECT")
        inv.status = "void_pending"
        inv.save(update_fields=["status"])
        VoidRequest.objects.create(invoice=inv, reason="please void")

        resp = self._signed_post({
            "event": "invoice.void_rejected",
            "data": {"invoice_id": str(inv.pk), "reason": "Not justified"},
        })
        self.assertEqual(resp.status_code, 200)

        inv.refresh_from_db()
        self.assertEqual(inv.status, "void_rejected")
        vr = VoidRequest.objects.get(invoice=inv)
        self.assertEqual(vr.status, "rejected")

    def test_dispute_resolved_void(self):
        inv = self._make_invoice("INV-DRVOID", "disputed")
        vr = VoidRequest.objects.create(invoice=inv, reason="void pls", status="rejected")
        DisputeRecord.objects.create(void_request=vr, dispute_reason="I disagree")

        resp = self._signed_post({
            "event": "dispute.resolved",
            "data": {"invoice_id": str(inv.pk), "resolution": "resolved_void", "note": "OK voided"},
        })
        self.assertEqual(resp.status_code, 200)

        inv.refresh_from_db()
        self.assertEqual(inv.status, "resolved_void")

    def test_dispute_resolved_kept(self):
        inv = self._make_invoice("INV-DRKEPT", "disputed")
        vr = VoidRequest.objects.create(invoice=inv, reason="void pls", status="rejected")
        DisputeRecord.objects.create(void_request=vr, dispute_reason="I disagree")

        resp = self._signed_post({
            "event": "dispute.resolved",
            "data": {"invoice_id": str(inv.pk), "resolution": "resolved_kept", "note": "Invoice stays"},
        })
        self.assertEqual(resp.status_code, 200)

        inv.refresh_from_db()
        self.assertEqual(inv.status, "resolved_kept")

    def test_invalid_hmac_rejected(self):
        resp = self.client.post(
            reverse("sync:sync_inbound"),
            data=json.dumps({"event": "test"}).encode(),
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE="sha256=wrong",
        )
        self.assertEqual(resp.status_code, 401)
