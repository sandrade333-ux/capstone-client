from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Job(TimestampedModel):
    """Job model for work orders and service requests."""

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)

    company = models.ForeignKey(
        "crm.Company", on_delete=models.CASCADE, related_name="jobs", null=True, blank=True
    )
    contact = models.ForeignKey(
        "crm.Contact", on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_jobs",
    )

    scheduled_start = models.DateTimeField(null=True, blank=True, db_index=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True, help_text="Additional job data")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["scheduled_start"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class JobNote(TimestampedModel):
    """Notes and comments on jobs."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="notes")
    content = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_notes",
    )
    attachments = models.JSONField(
        default=list, blank=True, help_text="Placeholder for file attachments (URLs or metadata)"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job Note"
        verbose_name_plural = "Job Notes"

    def __str__(self):
        return f"Note on {self.job.title} at {self.created_at}"
