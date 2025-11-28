from django.urls import include, path
from pigapp_app import views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

router = DefaultRouter()
router.register("costs", views.CostViewSet)
"""
router.register('costgroups',views.CostGroupViewSet)
router.register('cashflowgroups',views.CashFlowGroupViewSet)
router.register('devs',views.DevViewSet)
router.register('invoices',views.InvoiceViewSet)
router.register('cashflows',views.CashFlowViewSet)
router.register('costrepeats',views.CostRepeatFlowViewSet)
"""

app_name = "pigapp_app"

urlpatterns = [
    path("create/", views.CreateUserView.as_view(), name="create"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", views.ManageUserView.as_view(), name="me"),
    # invoice
    path("invoice_list/", views.InvoiceListAV.as_view(), name="invoice_list"),
    path(
        "invoice_sum_cost_list/<int:invoice_id>/<str:paid>",
        views.InvoiceSumCostAV.as_view(),
        name="invoice_sum_cost_list",
    ),
    path(
        "all_invoice_sum_cost_list/<str:paid>",
        views.AllInvoiceSumCostAV.as_view(),
        name="all_invoice_sum_cost_list",
    ),
    path(
        "only_invoice_list/",
        views.OnlyInvoiceListAV.as_view(),
        name="only_invoice_list",
    ),
    path(
        "invoice_detail/<int:pk>",
        views.InvoiceDetailAV.as_view(),
        name="invoice_detail",
    ),
    path(
        "only_invoice_detail/<int:pk>",
        views.OnlyInvoiceDetailAV.as_view(),
        name="only_invoice_detail",
    ),
    path(
        "all_invoice_sum_amount/",
        views.AllAmountInvoicesAPIView.as_view(),
        name="all_invoice_sum_amount",
    ),
    path(
        "invoice_search/",
        views.InvoiceListWithFilterAV.as_view(),
        name="invoice_search",
    ),
    path(
        "invoice_ordering/",
        views.InvoiceListOrderingDate.as_view(),
        name="invoice_ordering",
    ),
    path("invoice_only_ids/", views.AllInvoiceIDs.as_view(), name="invoice_only_ids"),
    path(
        "invoice/transfer/<int:szamla1_id>/<int:szamla2_id>",
        views.InvoiceAmountTransferAPIView.as_view(),
        name="invoice/transfer",
    ),
    path(
        'api/invoices/combo/', views.InvoiceComboAPIView.as_view(), name='invoice-combo'
    ),
    path(
        'api/update-invoice-amount/',
        views.UpdateInvoiceAmountView.as_view(),
        name='update-invoice-amount',
    ),
    # invoice end
    # costrepeat
    path("new_cost_repeat/", views.NewCostRepeatAV.as_view(), name="new_cost_repeat"),
    path(
        "costrepeat_list/", views.AllCostRepeatListAV.as_view(), name="costrepeat_list"
    ),
    path(
        "all_costrepeat_sum_cost_list/<str:paid>",
        views.AllCostRepeatSumCostAV.as_view(),
        name="all_costrepeat_sum_cost_list",
    ),
    # costrepeat end
    # cashflow
    path("new_cash_flow/", views.NewCashFlowAV.as_view(), name="new_cash_flow"),
    path("list_cash_flow/", views.ListCashFlowAV.as_view(), name="list_cash_flow"),
    path(
        "list_cash_flow_filter_date/<str:from_date>",
        views.ListCashFlowFilterDateAV.as_view(),
        name="list_cash_flow_filter_date",
    ),
    path(
        "list_cash_flow_last/",
        views.ListCashFlowLastAV.as_view(),
        name="list_cash_flow_last",
    ),
    path(
        "api/cashflows/<int:pk>/",
        views.CashFlowDetailView.as_view(),
        name="cashflow-detail",
    ),
    # cashflow end
    # cashflowgroup
    path(
        "new_cash_flow_groups/",
        views.NewCashFlowGroupAV.as_view(),
        name="new_cash_flow_groups",
    ),
    # cashflowgroup end
    # cost
    path("cost_list/", views.CostListAV.as_view(), name="cost_list"),
    path("cost_list_natur/", views.CostListNatur.as_view(), name="cost_list_natur"),
    path(
        "cost_filter/<int:invoice_id>/<str:from_date>/<str:to_date>",
        views.InvoiceWithCostDateUserFilterAV.as_view(),
        name="cost_filter",
    ),
    # path('cost_search_with_cname/<str:cost_name>',views.CostListWithFilterAV.as_view(), name='cost_search_with_cname'),
    path("cost_search/", views.CostListWithFilterAV.as_view(), name="cost_search"),
    path("sum_all_cost/<str:paid>", views.SumAllCostAV.as_view(), name="sum_all_cost"),
    path(
        "actual_day_cost_filter/<str:actual_day>",
        views.ActualDayPayAmountListAV.as_view(),
        name="actual_day_cost_filter",
    ),
    path("new_cost/", views.NewCost.as_view(), name="new_cost"),
    path(
        "api/cost-summary/", views.MonthlyCostSummaryView.as_view(), name="cost-summary"
    ),
    path("costgroup-cost/", views.CostGroupCostView.as_view(), name="costgroup-cost"),
    path(
        "api/monthly-costs/", views.MonthlyCostAPIView.as_view(), name="monthly-costs"
    ),
    path("test_cost/", views.CostList.as_view()),
    path("test_cost/<int:pk>", views.CostDetail.as_view()),
    path("test_cost_mixins/", views.CostListMixins.as_view()),
    path("test_cost_mixins/<int:pk>", views.CostDetailMixins.as_view()),
    path("test_nested_cost/", views.CostListNestedView.as_view()),
    path("test_nested_cost/<int:pk>", views.CostDetailNestedView.as_view()),
    path("test_nested_invoice/", views.InvoiceListNestedView.as_view()),
    path("test_nested_invoice/<int:pk>", views.InvoiceNestedDetailGenView.as_view()),
    path(
        "current-month-costgroup-5/",
        views.CurrentMonthCostGroup5View.as_view(),
        name="current-month-costgroup-5",
    ),
    path(
        "create-cost/", views.CreateCost.as_view(), name="create_cost"
    ),  # POST új költség hozzáadása
    path(
        "foreignkey-data/", views.ForeignKeyDataView.as_view(), name="foreignkey_data"
    ),
    path("cost-detail/<int:pk>/", views.CostDetail.as_view(), name="cost-detail"),
    path(
        'update-cost-dates/',
        views.MonthlyCostAPIView.as_view(),
        name='update-cost-dates',
    ),
    path(
        'calculate_cash/',
        views.CalculateCash.as_view(),
        name='calculate_cash',
    ),
    path(
        'monthly-cost-forecast/',
        views.MonthlyCostForecastAPIView.as_view(),
        name='monthly-cost-forecast',
    ),
    # cost end
    # costgroup
    path("new_cost_groups/", views.NewCostGroupAV.as_view(), name="new_cost_groups"),
    path(
        "api/cost-summary/<int:costgroup_id>/",
        views.CostRepeatSummaryView.as_view(),
        name="cost-summary",
    ),
    # costgroup end
    path("", include(router.urls)),
    path(
        'api/cost-repeat-summary/',
        views.CostRepeatInvoiceSummaryView.as_view(),
        name='repeated-cost-summary',
    ),
    path(
        "api/upcoming-unpaid-costs/",
        views.UpcomingUnpaidCostsAPIView.as_view(),
        name="upcoming-unpaid-costs",
    ),
    path(
        "api/cib-parse/",
        views.CibStatementUploadView.as_view(),
        name="cib-parse",
    ),
]
