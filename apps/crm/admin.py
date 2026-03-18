from django.contrib import admin

from .models import Company, Contact, Interaction


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    fields = ["first_name", "last_name", "email", "phone", "source"]
    show_change_link = True


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "created_at"]
    search_fields = ["name", "email"]
    inlines = [ContactInline]


class InteractionInline(admin.TabularInline):
    model = Interaction
    extra = 0
    fields = ["interaction_type", "subject", "occurred_at"]
    show_change_link = True


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "email", "phone", "company", "source"]
    list_filter = ["source"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    inlines = [InteractionInline]


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ["contact", "interaction_type", "subject", "occurred_at"]
    list_filter = ["interaction_type"]
    search_fields = ["subject", "summary"]
