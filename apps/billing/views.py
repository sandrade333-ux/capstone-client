from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView
from django.template.response import TemplateResponse

from .models import DisputeRecord, Invoice, VoidRequest


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """Show invoice with line items, void request, and dispute status."""

    model = Invoice
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["line_items"] = self.object.line_items.all()
        try:
            ctx["void_request"] = self.object.void_request
        except VoidRequest.DoesNotExist:
            ctx["void_request"] = None
        return ctx


class RequestVoidView(LoginRequiredMixin, View):
    """Request to void an invoice. GET shows form, POST submits."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.can_request_void:
            return HttpResponseBadRequest("This invoice cannot be voided.")
        return TemplateResponse(request, "billing/void_request_form.html", {"invoice": invoice})

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.can_request_void:
            return HttpResponseBadRequest("This invoice cannot be voided.")

        reason = request.POST.get("reason", "").strip()
        if not reason:
            return TemplateResponse(
                request,
                "billing/void_request_form.html",
                {"invoice": invoice, "error": "Please provide a reason."},
            )

        VoidRequest.objects.create(
            invoice=invoice,
            requested_by=request.user,
            reason=reason,
        )
        invoice.status = Invoice.STATUS_VOID_PENDING
        invoice.save(update_fields=["status"])

        return redirect("billing:invoice_detail", pk=invoice.pk)


class DisputeVoidView(LoginRequiredMixin, View):
    """Dispute a void rejection. GET shows form, POST submits."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.can_dispute:
            return HttpResponseBadRequest("This invoice cannot be disputed.")
        return TemplateResponse(request, "billing/dispute_form.html", {"invoice": invoice})

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.can_dispute:
            return HttpResponseBadRequest("This invoice cannot be disputed.")

        dispute_reason = request.POST.get("dispute_reason", "").strip()
        if not dispute_reason:
            return TemplateResponse(
                request,
                "billing/dispute_form.html",
                {"invoice": invoice, "error": "Please explain your dispute."},
            )

        try:
            void_request = invoice.void_request
        except VoidRequest.DoesNotExist:
            return HttpResponseBadRequest("No void request to dispute.")

        DisputeRecord.objects.create(
            void_request=void_request,
            disputed_by=request.user,
            dispute_reason=dispute_reason,
        )
        invoice.status = Invoice.STATUS_DISPUTED
        invoice.save(update_fields=["status"])

        return redirect("billing:invoice_detail", pk=invoice.pk)
