from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.billing.models import Invoice, VoidRequest, DisputeRecord
from apps.crm.models import Contact
from apps.sync.models import SyncConfiguration


class SyncOutboundTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(first_name="Out", last_name="Test", email="o@o.com")
        self.config = SyncConfiguration.objects.create(
            control_plane_url="https://test.example.com/inbound/",
            shared_secret="secret-abc",
            instance_id="test-outbound",
            is_active=True,
        )

    @patch("apps.sync.signals.requests.post")
    def test_void_request_fires_signal(self, mock_post):
        mock_post.return_value.status_code = 200
        inv = Invoice.objects.create(
            invoice_number="INV-OUTSIG", contact=self.contact, status="void_pending",
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        VoidRequest.objects.create(invoice=inv, reason="void please")

        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args
        import json
        body = json.loads(call_args.kwargs.get("data", call_args[1].get("data", "")))
        self.assertEqual(body["event"], "invoice.void_requested")

    @patch("apps.sync.signals.requests.post")
    def test_dispute_fires_signal(self, mock_post):
        mock_post.return_value.status_code = 200
        inv = Invoice.objects.create(
            invoice_number="INV-OUTDISP", contact=self.contact, status="void_rejected",
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        vr = VoidRequest.objects.create(invoice=inv, reason="void", status="rejected")
        DisputeRecord.objects.create(void_request=vr, dispute_reason="I disagree")

        # Find the dispute signal call
        calls = mock_post.call_args_list
        import json
        dispute_calls = [c for c in calls if "disputed" in json.loads(c.kwargs.get("data", c[1].get("data", ""))).get("event", "")]
        self.assertTrue(len(dispute_calls) > 0)

    @patch("apps.sync.signals.requests.post")
    def test_no_sync_config_skips_silently(self, mock_post):
        SyncConfiguration.objects.all().delete()
        inv = Invoice.objects.create(
            invoice_number="INV-NOCONFIG", contact=self.contact, status="void_pending",
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        VoidRequest.objects.create(invoice=inv, reason="no config")
        mock_post.assert_not_called()

    @patch("apps.sync.signals.requests.post")
    def test_signal_includes_instance_id(self, mock_post):
        mock_post.return_value.status_code = 200
        inv = Invoice.objects.create(
            invoice_number="INV-INSTID", contact=self.contact, status="void_pending",
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        VoidRequest.objects.create(invoice=inv, reason="instance check")

        import json
        body = json.loads(mock_post.call_args.kwargs.get("data", mock_post.call_args[1].get("data", "")))
        self.assertEqual(body["instance_id"], "test-outbound")
