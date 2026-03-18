from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimestampedModel


class Company(TimestampedModel):
    """Company model for B2B customers."""

    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional company data")

    class Meta:
        ordering = ["name"]
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class Contact(TimestampedModel):
    """Contact model for individual customers or leads."""

    CONTACT_SOURCE_CHOICES = [
        ("website", "Website"),
        ("phone", "Phone Call"),
        ("email", "Email"),
        ("referral", "Referral"),
        ("social", "Social Media"),
        ("other", "Other"),
    ]

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="contacts"
    )
    source = models.CharField(max_length=50, choices=CONTACT_SOURCE_CHOICES, default="other")
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorizing contacts (list of strings, max 50)",
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional contact data")

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        super().clean()
        if self.tags:
            normalized = [tag.strip().lower() for tag in self.tags if tag and tag.strip()]
            self.tags = list(set(normalized))[:50]
            for tag in self.tags:
                if len(tag) > 50:
                    raise ValidationError({"tags": f"Tag too long (max 50 chars): {tag}"})
                if len(tag) < 1:
                    raise ValidationError({"tags": "Tags cannot be empty"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Interaction(TimestampedModel):
    """Interaction model for tracking communications with contacts."""

    INTERACTION_TYPE_CHOICES = [
        ("call", "Phone Call"),
        ("email", "Email"),
        ("sms", "SMS"),
        ("meeting", "Meeting"),
        ("note", "Note"),
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPE_CHOICES)
    subject = models.CharField(max_length=255, blank=True)
    summary = models.TextField()
    occurred_at = models.DateTimeField(db_index=True)
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interactions", help_text="User who created this interaction",
    )

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name = "Interaction"
        verbose_name_plural = "Interactions"
        indexes = [
            models.Index(fields=["contact", "-occurred_at"]),
            models.Index(fields=["interaction_type"]),
        ]

    def __str__(self):
        return f"{self.get_interaction_type_display()} with {self.contact} on {self.occurred_at}"
