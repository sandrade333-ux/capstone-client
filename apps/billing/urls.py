from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("invoices/<uuid:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<uuid:pk>/void/", views.RequestVoidView.as_view(), name="void_request"),
    path("invoices/<uuid:pk>/dispute/", views.DisputeVoidView.as_view(), name="dispute"),
]
