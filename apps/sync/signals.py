"""Outbound sync signals.

Fires webhooks to Tyler's control plane when CRM/billing data changes.
If no SyncConfiguration is active, skips silently with a log warning.
"""

import hashlib
import hmac
import json
import logging

import requests
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.billing.models import DisputeRecord, Invoice, VoidRequest
from apps.crm.models import Contact
from apps.jobs.models import Job

from .models import SyncConfiguration

logger = logging.getLogger(__name__)


def _send_sync_event(event_type, data):
    """Send a signed webhook to Tyler's control plane."""
    config = SyncConfiguration.get_active()
    if config is None:
        logger.debug("Sync not configured, skipping %s", event_type)
        return

    payload = json.dumps(
        {
            "version": "1",
            "event": event_type,
            "instance_id": config.instance_id,
            "data": data,
        },
        sort_keys=True,
        default=str,
    )
    signature = "sha256=" + hmac.new(
        config.shared_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()

    try:
        resp = requests.post(
            config.control_plane_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
            },
            timeout=10,
        )
        if resp.status_code < 300:
            logger.info("Sync %s sent successfully", event_type)
        else:
            logger.warning("Sync %s returned %s: %s", event_type, resp.status_code, resp.text[:200])
    except requests.RequestException as e:
        logger.error("Sync %s failed: %s", event_type, e)


def _model_to_dict(instance, fields):
    """Extract fields from a model instance as a JSON-safe dict."""
    data = {}
    for f in fields:
        val = getattr(instance, f, None)
        data[f] = val
    return data


@receiver(post_save, sender=Contact)
def sync_contact(sender, instance, created, **kwargs):
    event = "contact.created" if created else "contact.updated"
    _send_sync_event(event, _model_to_dict(instance, [
        "id", "first_name", "last_name", "email", "phone",
    ]))


@receiver(post_save, sender=Job)
def sync_job(sender, instance, created, **kwargs):
    if created:
        event = "job.created"
    elif instance.status == "completed":
        event = "job.completed"
    else:
        event = "job.status_changed"
    _send_sync_event(event, _model_to_dict(instance, [
        "id", "title", "status", "scheduled_start",
    ]))


@receiver(post_save, sender=Invoice)
def sync_invoice(sender, instance, created, **kwargs):
    if created:
        event = "invoice.created"
    elif instance.status == "sent":
        event = "invoice.sent"
    elif instance.status == "paid":
        event = "invoice.paid"
    elif instance.status == "overdue":
        event = "invoice.overdue"
    else:
        return  # Other status changes handled by VoidRequest/Dispute signals
    _send_sync_event(event, _model_to_dict(instance, [
        "id", "invoice_number", "status", "total",
    ]))


@receiver(post_save, sender=VoidRequest)
def sync_void_request(sender, instance, created, **kwargs):
    if created:
        _send_sync_event("invoice.void_requested", {
            "invoice_id": str(instance.invoice_id),
            "invoice_number": instance.invoice.invoice_number,
            "reason": instance.reason,
            "requested_by": str(instance.requested_by_id),
        })


@receiver(post_save, sender=DisputeRecord)
def sync_dispute(sender, instance, created, **kwargs):
    if created:
        _send_sync_event("void.disputed", {
            "invoice_id": str(instance.void_request.invoice_id),
            "invoice_number": instance.void_request.invoice.invoice_number,
            "dispute_reason": instance.dispute_reason,
            "disputed_by": str(instance.disputed_by_id),
        })
