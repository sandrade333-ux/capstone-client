from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Invoice(TimestampedModel):
    """Invoice model for billing customers."""

    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"
    STATUS_VOID_PENDING = "void_pending"
    STATUS_VOID_REJECTED = "void_rejected"
    STATUS_DISPUTED = "disputed"
    STATUS_RESOLVED_VOID = "resolved_void"
    STATUS_RESOLVED_KEPT = "resolved_kept"
    STATUS_VOID = "void"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_PAID, "Paid"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_VOID_PENDING, "Void Pending"),
        (STATUS_VOID_REJECTED, "Void Rejected"),
        (STATUS_DISPUTED, "Disputed"),
        (STATUS_RESOLVED_VOID, "Resolved \u2014 Voided"),
        (STATUS_RESOLVED_KEPT, "Resolved \u2014 Kept"),
        (STATUS_VOID, "Void"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)

    contact = models.ForeignKey("crm.Contact", on_delete=models.PROTECT, related_name="invoices")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )

    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["due_at"]),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.contact.get_full_name()}"

    @property
    def can_request_void(self):
        """Can Sam request a void for this invoice?"""
        return self.status in (self.STATUS_SENT, self.STATUS_OVERDUE)

    @property
    def can_dispute(self):
        """Can Sam dispute a void rejection?"""
        return self.status == self.STATUS_VOID_REJECTED

    @property
    def is_settled(self):
        """Is this invoice in a terminal state?"""
        return self.status in (
            self.STATUS_PAID,
            self.STATUS_VOID,
            self.STATUS_RESOLVED_VOID,
            self.STATUS_RESOLVED_KEPT,
            self.STATUS_CANCELLED,
        )

    def calculate_totals(self):
        """Calculate and update subtotal and total from line items."""
        line_items = self.line_items.all()
        self.subtotal = sum((item.amount for item in line_items), Decimal("0.00"))
        self.total = self.subtotal + self.tax
        self.save(update_fields=["subtotal", "total"])
        return self.total


class LineItem(TimestampedModel):
    """Line item for invoice."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Line Item"
        verbose_name_plural = "Line Items"

    def __str__(self):
        return f"{self.description} - {self.amount}"

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        if self.invoice_id:
            self.invoice.calculate_totals()


class VoidRequest(TimestampedModel):
    """Sam's request to void an invoice. Sent to Tyler via sync webhook."""

    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name="void_request")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="void_requests"
    )
    reason = models.TextField(help_text="Why do you want to void this invoice?")

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewer_note = models.TextField(blank=True, help_text="Tyler's note on the decision")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    sync_sent_at = models.DateTimeField(null=True, blank=True, help_text="When sync was sent to Tyler")
    sync_ack_at = models.DateTimeField(null=True, blank=True, help_text="When Tyler acknowledged")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Void request for {self.invoice} \u2014 {self.status}"


class DisputeRecord(TimestampedModel):
    """Sam's dispute of Tyler's void rejection.

    When Tyler rejects a void request, Sam can formally dispute the decision.
    Resolution is pushed via sync webhook from Tyler.
    """

    void_request = models.OneToOneField(
        VoidRequest, on_delete=models.CASCADE, related_name="dispute"
    )
    disputed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="disputes"
    )
    dispute_reason = models.TextField(help_text="Why do you disagree with Tyler's decision?")
    evidence = models.JSONField(
        default=dict,
        blank=True,
        help_text="Supporting evidence: customer emails, contracts, payment records, etc.",
    )

    RESOLUTION_CHOICES = [
        ("open", "Open"),
        ("resolved_void", "Resolved \u2014 Invoice Voided"),
        ("resolved_kept", "Resolved \u2014 Invoice Kept"),
        ("withdrawn", "Withdrawn by Sam"),
    ]
    status = models.CharField(max_length=20, choices=RESOLUTION_CHOICES, default="open")
    resolution_note = models.TextField(blank=True, help_text="How was this resolved?")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(
        max_length=100, blank=True, help_text="Who resolved this: Tyler, Sam, or mutual agreement"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispute: {self.void_request.invoice} \u2014 {self.status}"
