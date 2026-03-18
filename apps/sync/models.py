from django.db import models


class SyncConfiguration(models.Model):
    """Single connection to Tyler's control plane.

    Admin creates this once during setup.
    If no active config exists, sync signals skip silently.
    """

    control_plane_url = models.URLField(
        help_text="Tyler's inbound webhook URL, e.g. https://guildhouse.example.com/api/v1/capstone/inbound/"
    )
    shared_secret = models.CharField(
        max_length=255, help_text="Shared secret for HMAC signature verification. Must match Tyler's config."
    )
    instance_id = models.CharField(
        max_length=100, help_text="This instance's unique ID, e.g. 'entropyopposition'"
    )
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Sync Configuration"

    def __str__(self):
        active = "active" if self.is_active else "inactive"
        return f"Sync \u2192 {self.control_plane_url} ({active})"

    @classmethod
    def get_active(cls):
        """Return the active sync config, or None if not configured."""
        return cls.objects.filter(is_active=True).first()
