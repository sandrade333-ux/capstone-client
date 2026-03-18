"""Inbound webhook from Tyler's control plane.

Receives governance signals: void approvals, rejections, dispute resolutions.
Validates HMAC-SHA256 signature before processing.
"""

import hashlib
import hmac
import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.billing.models import DisputeRecord, Invoice, VoidRequest

from .models import SyncConfiguration

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def sync_inbound(request):
    """Receive governance signals from Tyler's control plane."""
    config = SyncConfiguration.get_active()
    if config is None:
        return JsonResponse({"error": "sync not configured"}, status=503)

    # Verify HMAC signature
    sig = request.headers.get("X-Webhook-Signature", "")
    expected = "sha256=" + hmac.new(
        config.shared_secret.encode(), request.body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return JsonResponse({"error": "invalid signature"}, status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    event = payload.get("event", "")
    data = payload.get("data", {})

    handlers = {
        "invoice.void_approved": _handle_void_approved,
        "invoice.void_rejected": _handle_void_rejected,
        "dispute.resolved": _handle_dispute_resolved,
    }

    handler = handlers.get(event)
    if handler:
        try:
            handler(data)
        except Exception:
            logger.exception("Error handling sync event %s", event)
            return JsonResponse({"error": "handler error"}, status=500)
    else:
        logger.info("Unhandled sync event: %s", event)

    return JsonResponse({"status": "ok"})


def _handle_void_approved(data):
    """Tyler approved the void request."""
    void_request = VoidRequest.objects.select_related("invoice").get(
        invoice__id=data["invoice_id"]
    )
    now = timezone.now()

    void_request.status = "approved"
    void_request.reviewer_note = data.get("note", "")
    void_request.reviewed_at = now
    void_request.sync_ack_at = now
    void_request.save()

    void_request.invoice.status = Invoice.STATUS_VOID
    void_request.invoice.save(update_fields=["status"])
    logger.info("Void approved for invoice %s", void_request.invoice.invoice_number)


def _handle_void_rejected(data):
    """Tyler rejected the void request."""
    void_request = VoidRequest.objects.select_related("invoice").get(
        invoice__id=data["invoice_id"]
    )
    now = timezone.now()

    void_request.status = "rejected"
    void_request.reviewer_note = data.get("reason", "")
    void_request.reviewed_at = now
    void_request.sync_ack_at = now
    void_request.save()

    void_request.invoice.status = Invoice.STATUS_VOID_REJECTED
    void_request.invoice.save(update_fields=["status"])
    logger.info("Void rejected for invoice %s", void_request.invoice.invoice_number)


def _handle_dispute_resolved(data):
    """Tyler resolved the dispute."""
    dispute = DisputeRecord.objects.select_related(
        "void_request", "void_request__invoice"
    ).get(void_request__invoice__id=data["invoice_id"])

    resolution = data.get("resolution", "resolved_kept")
    now = timezone.now()

    dispute.status = resolution
    dispute.resolution_note = data.get("note", "")
    dispute.resolved_at = now
    dispute.resolved_by = data.get("resolved_by", "Tyler")
    dispute.save()

    final_status = (
        Invoice.STATUS_RESOLVED_VOID
        if resolution == "resolved_void"
        else Invoice.STATUS_RESOLVED_KEPT
    )
    dispute.void_request.invoice.status = final_status
    dispute.void_request.invoice.save(update_fields=["status"])
    logger.info(
        "Dispute resolved for invoice %s: %s",
        dispute.void_request.invoice.invoice_number,
        resolution,
    )
