from django.contrib import admin

from .models import DisputeRecord, Invoice, LineItem, VoidRequest


class LineItemInline(admin.TabularInline):
    model = LineItem
    extra = 1
    fields = ["description", "quantity", "unit_price", "amount"]
    readonly_fields = ["amount"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "contact", "total", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["invoice_number", "contact__email", "contact__first_name", "contact__last_name"]
    readonly_fields = ["status"]
    inlines = [LineItemInline]


@admin.register(LineItem)
class LineItemAdmin(admin.ModelAdmin):
    list_display = ["description", "invoice", "quantity", "unit_price", "amount"]


@admin.register(VoidRequest)
class VoidRequestAdmin(admin.ModelAdmin):
    list_display = ["invoice", "status", "requested_by", "created_at"]
    list_filter = ["status"]
    readonly_fields = [
        "invoice", "requested_by", "reason", "status",
        "reviewer_note", "reviewed_at", "sync_sent_at", "sync_ack_at",
    ]


@admin.register(DisputeRecord)
class DisputeRecordAdmin(admin.ModelAdmin):
    list_display = ["void_request", "status", "disputed_by", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["status", "resolved_at", "resolved_by", "resolution_note"]
