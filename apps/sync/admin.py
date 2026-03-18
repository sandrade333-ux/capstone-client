from django.contrib import admin

from .models import SyncConfiguration


@admin.register(SyncConfiguration)
class SyncConfigurationAdmin(admin.ModelAdmin):
    list_display = ["control_plane_url", "instance_id", "is_active", "last_sync_at"]
    list_filter = ["is_active"]
