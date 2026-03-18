from django.contrib import admin

from .models import Job, JobNote


class JobNoteInline(admin.TabularInline):
    model = JobNote
    extra = 0
    fields = ["content", "created_by", "created_at"]
    readonly_fields = ["created_at"]
    show_change_link = True


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "company", "contact", "assigned_to", "scheduled_start"]
    list_filter = ["status"]
    search_fields = ["title", "description"]
    inlines = [JobNoteInline]


@admin.register(JobNote)
class JobNoteAdmin(admin.ModelAdmin):
    list_display = ["job", "created_by", "created_at"]
    search_fields = ["content"]
