import logging
from collections import defaultdict
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.db.models import Q, Sum
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from pigapp_app.serializers import (AllInvoicesTotalAmountSerializer,
                                    CashFlowGroupSerializer,
                                    CashFlowSerializer, CostNestedSerializer,
                                    CostRepeatSerializer, CostSerializer,
                                    CostSerializerNatur, CostSummarySerializer,
                                    ForeignKeyCashFlowGroupSerializer,
                                    ForeignKeyCostRepeatSerializer,
                                    ForeignKeyCostroupSerializer,
                                    ForeignKeyDevSerializer,
                                    ForeignKeyInvoiceSerializer,
                                    InvoiceComboSerializer,
                                    InvoiceNestedSerializer, InvoiceSerializer,
                                    ListCashFlowSerializer,
                                    MonthlyCostSerializer,
                                    NewCashFlowSerializer,
                                    NewCostGroupSerializer,
                                    OnlyCostRepeatSerializer,
                                    OnlyCostSerializer, OnlyInvoiceSerializer,
                                    UserSerializer)
from rest_framework import (filters, generics, mixins,
                            permissions, status, viewsets)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

from .cib_parser import CibStatementParser
from .datefu import DateFu
from .models import (CashFlow, CashFlowGroup, Cost, CostGroup, CostRepeat, Dev,
                     Invoice)
from .serializers import (CostRepeatWithCostsSerializeToSum,
                          MyTokenObtainPairSerializer)

logger = logging.getLogger(__name__)


""" test """


def test(request):
    tst = {"id": "123", "name": "test", "amount": "1000"}
    data = Cost.objects.all()
    response = {"costs": list(data.values("cost_name", "amount"))}
    return JsonResponse(response)


# API view
""" class CostRepeatSummaryView(APIView):
    def get(self, request, costgroup_id=None):
        try:
            queryset = (
                CostRepeat.objects.filter(costrepeat__user=request.user)
                .filter(costrepeat__costgroup_id=costgroup_id, costrepeat__paid=0)
                .distinct()
            )

            if not queryset.exists():
                return Response(
                    {
                        "detail": f"Nincs találat a megadott costgroup_id={costgroup_id} értékre."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = CostRepeatWithCostsSerializeToSum(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Hiba történt: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) """


class CibStatementUploadView(APIView):
    """
    GET: CIB számlakivonat PDF-ek feldolgozása az app/pdf_uploads könyvtárból.
    (Nincs feltöltés, a PDF-eket kézzel másolod oda.)
    """

    def get(self, request, *args, **kwargs):
        try:
            # app/pdf_uploads mappa
            folder = settings.BASE_DIR / "pdf_uploads"

            if not folder.exists():
                return Response(
                    {"detail": f"A könyvtár nem létezik: {folder}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            parser = CibStatementParser()
            summary_dict = parser.parse_path(str(folder))  # több PDF-et feldolgoz

            # Ha több PDF-et adsz meg, parse_path dict-et ad vissza:
            # { "fajlnev1": {...}, "fajlnev2": {...}, ... }
            return Response(summary_dict, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Hiba történt a PDF-ek feldolgozása közben: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MonthlyCostForecastAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            today = date.today()
            end_date = today + relativedelta(months=6)

            # Egyetlen lekérdezés: aktuális hónaptól +6 hónapig
            queryset = (
                Cost.objects.filter(
                    cost_date__gte=today.replace(day=1),
                    cost_date__lte=end_date.replace(day=1)
                    + relativedelta(months=1, days=-1),
                )
                .annotate(
                    year=ExtractYear('cost_date'), month=ExtractMonth('cost_date')
                )
                .values('year', 'month')
            )

            # Összesítések
            monthly_data = {}
            for item in queryset:
                key = f"{item['year']}-{item['month']:02}"
                if key not in monthly_data:
                    monthly_data[key] = {"paid_sum": 0, "unpaid_sum": 0}

            # Lekérdezzük külön a fizetett és nem fizetett összegeket
            costs = (
                Cost.objects.filter(
                    cost_date__gte=today.replace(day=1),
                    cost_date__lte=end_date.replace(day=1)
                    + relativedelta(months=1, days=-1),
                )
                .annotate(
                    year=ExtractYear('cost_date'), month=ExtractMonth('cost_date')
                )
                .values('year', 'month', 'paid')
                .annotate(total_amount=Sum('amount'))
            )

            for cost in costs:
                key = f"{cost['year']}-{cost['month']:02}"
                if cost['paid'] == 1:
                    monthly_data[key]["paid_sum"] += cost['total_amount'] or 0
                else:
                    monthly_data[key]["unpaid_sum"] += cost['total_amount'] or 0

            # Kimenet formázása, teljes összeg kiszámolása
            results = []
            for i in range(7):
                month_date = today + relativedelta(months=i)
                key = month_date.strftime("%Y-%m")
                paid = monthly_data.get(key, {}).get("paid_sum", 0)
                unpaid = monthly_data.get(key, {}).get("unpaid_sum", 0)
                results.append(
                    {
                        "year_month": key,
                        "paid_sum": paid,
                        "unpaid_sum": unpaid,
                        "total_sum": paid + unpaid,
                    }
                )

            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "error": "Hiba történt a havi előrejelzés lekérésekor.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CostRepeatSummaryView(APIView):
    def get(self, request, costgroup_id=None):
        try:
            queryset = (
                CostRepeat.objects.filter(costrepeat__user=request.user)
                .filter(costrepeat__costgroup_id=costgroup_id, costrepeat__paid=0)
                .distinct()
            )

            if not queryset.exists():
                return Response(
                    {
                        "detail": f"Nincs találat a megadott costgroup_id={costgroup_id} értékre."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = CostRepeatWithCostsSerializeToSum(
                queryset, many=True, context={"costgroup_id": costgroup_id}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Hiba történt: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DateRangeHelper:
    @staticmethod
    def get_now():
        return timezone.now()

    @staticmethod
    def get_current_month_range():
        now = DateRangeHelper.get_now()
        first_day = now.replace(day=1)
        if now.month < 12:
            first_day_of_next_month = now.replace(month=now.month + 1, day=1)
        else:
            first_day_of_next_month = now.replace(year=now.year + 1, month=1, day=1)
        last_day = first_day_of_next_month - timedelta(days=1)
        return first_day, last_day

    @staticmethod
    def get_previous_month_range():
        first_day_of_current_month = DateRangeHelper.get_now().replace(day=1)
        last_day = first_day_of_current_month - timedelta(days=1)
        first_day = last_day.replace(day=1)
        return first_day, last_day

    @staticmethod
    def get_current_week_range():
        now = DateRangeHelper.get_now()
        start_of_week = now - timedelta(days=now.weekday())  # hétfő
        end_of_week = start_of_week + timedelta(days=6)  # vasárnap
        return start_of_week.date(), end_of_week.date()

    @staticmethod
    def get_previous_week_range():
        now = DateRangeHelper.get_now()
        start_of_current_week = now - timedelta(days=now.weekday())
        start_of_previous_week = start_of_current_week - timedelta(days=7)
        end_of_previous_week = start_of_previous_week + timedelta(days=6)
        return start_of_previous_week.date(), end_of_previous_week.date()


# views.py
class UpdateInvoiceAmountView(APIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]  # csak bejelentkezett felhasználóknak

    def post(self, request, *args, **kwargs):
        invoice_id = request.data.get("invoice_id")
        amount = request.data.get("amount")

        if not invoice_id or amount is None:
            return Response(
                {"error": "invoice_id és amount megadása kötelező."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = int(amount)
        except ValueError:
            return Response(
                {"error": "Az amount csak szám lehet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice = get_object_or_404(Invoice, id=invoice_id)

        # Ellenőrizzük, hogy a bejelentkezett useré-e a számla
        if invoice.user != request.user:
            return Response(
                {"error": "Nincs jogosultságod ehhez a számlához."},
                status=status.HTTP_403_FORBIDDEN,
            )

        invoice.amount = amount
        invoice.save()

        return Response(
            {
                "message": "Amount frissítve.",
                "invoice_id": invoice.id,
                "new_amount": invoice.amount,
            },
            status=status.HTTP_200_OK,
        )


class CalculateCash(APIView):
    def post(self, request, format=None):
        try:
            cost_ids = request.data.get("cost_ids", [])

            if not cost_ids:
                return Response(
                    {"success": False, "message": "cost_ids parameter is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            costs = Cost.objects.filter(id__in=cost_ids)

            if costs.count() != len(cost_ids):
                found_ids = set(costs.values_list("id", flat=True))
                missing_ids = set(cost_ids) - found_ids
                logger.error(f"Cost(s) with ID(s) {missing_ids} not found.")
                return Response(
                    {
                        "success": False,
                        "message": f"Cost(s) with ID(s) {missing_ids} not found.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            total_amount = costs.aggregate(total=Sum("amount"))["total"] or 0
            latest_cashflow_amount = (
                CashFlow.objects.order_by("-cash_flow_date")
                .values_list("amount", flat=True)
                .first()
                or 0
            )
            total_enabled_invoice_amount = (
                Invoice.objects.filter(enable_invoice=1).aggregate(total=Sum("amount"))[
                    "total"
                ]
                or 0
            )

            return Response(
                {
                    "success": True,
                    "message": "Amounts successfully calculated.",
                    "data": {
                        "total_amount": total_amount,
                        "latest_cashflow_amount": latest_cashflow_amount,
                        "cashflow_minus_total": latest_cashflow_amount - total_amount,
                        "total_enabled_invoice_amount": total_enabled_invoice_amount,
                        "invoice_minus_total": total_enabled_invoice_amount
                        - total_amount,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error while calculating cash: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": f"Error while calculating cash: {str(e)}",
                    "data": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpcomingUnpaidCostsAPIView(APIView):
    """
    API endpoint, amely visszaadja az 5 napon belüli, ki nem fizetett költségeket
    csak a bejelentkezett felhasználónak.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            today = date.today()
            five_days_later = today + timedelta(days=5)

            upcoming_unpaid_costs = Cost.objects.filter(
                user=user, cost_date__range=(today, five_days_later), paid=0
            )

            serializer = CostSerializer(upcoming_unpaid_costs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValidationError as ve:
            return Response(
                {"error": "Érvénytelen lekérdezési paraméter(ek).", "details": str(ve)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError as db_err:
            return Response(
                {"error": "Adatbázis hiba történt.", "details": str(db_err)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": "Váratlan hiba történt.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CostRepeatInvoiceSummaryView(APIView):
    def get(self, request):
        today = date.today()
        first_day = today.replace(day=1)
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(
                days=1
            )
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        filter_conditions = Q(
            costrepeat__isnull=False,
            invoice__enable_invoice=1,
            cost_date__range=(first_day, last_day),
        ) & ~Q(costrepeat__cost_repeat_name__iexact="nincs")

        # Részletes: costrepeat + invoice szint
        detailed_qs = (
            Cost.objects.filter(filter_conditions)
            .values(
                "invoice__id",
                "invoice__invoice_name",
                "costrepeat__id",
                "costrepeat__cost_repeat_name",
            )
            .annotate(total_amount=Sum("amount"))
        )

        # Összesítő: csak invoice szint
        invoice_totals = (
            Cost.objects.filter(filter_conditions)
            .values(
                "invoice__id",
                "invoice__invoice_name",
            )
            .annotate(total_invoice_amount=Sum("amount"))
        )

        # Eredmény összeépítése
        result = []
        for invoice in invoice_totals:
            invoice_id = invoice["invoice__id"]
            invoice_name = invoice["invoice__invoice_name"]
            total_invoice_amount = invoice["total_invoice_amount"]

            details = [
                {
                    "costrepeat_id": item["costrepeat__id"],
                    "costrepeat_name": item["costrepeat__cost_repeat_name"],
                    "total_amount": item["total_amount"],
                }
                for item in detailed_qs
                if item["invoice__id"] == invoice_id
            ]

            result.append(
                {
                    "invoice_id": invoice_id,
                    "invoice_name": invoice_name,
                    "total_invoice_amount": total_invoice_amount,
                    "details": details,
                }
            )

        return Response(result)


class InvoiceComboAPIView(generics.ListAPIView):
    queryset = Invoice.objects.filter(enable_invoice=1)  # ha csak az aktívakat kéred
    serializer_class = InvoiceComboSerializer


class MonthlyCostAPIView(APIView):
    def get(self, request, format=None):
        try:
            today = date.today()
            costs = Cost.objects.filter(
                cost_date__year=today.year, cost_date__month=today.month
            ).select_related("invoice")

            serializer = MonthlyCostSerializer(costs, many=True)

            return Response(
                {
                    "success": True,
                    "message": "Monthly costs retrieved successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error while retrieving monthly costs: {str(e)}",
                    "data": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, format=None):
        try:
            cost_ids = request.data.get("cost_ids", [])

            if not cost_ids:
                return Response(
                    {"success": False, "message": "cost_ids parameter is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            updated_costs = []
            for cost_id in cost_ids:
                try:
                    cost = Cost.objects.get(id=cost_id)

                    old_cost_date = cost.cost_date
                    logger.info(f"Old cost date for cost ID {cost_id}: {old_cost_date}")

                    # Már datetime.date típus, nem kell parse-olni
                    new_cost_date = old_cost_date + relativedelta(months=1)
                    logger.info(f"New cost date for cost ID {cost_id}: {new_cost_date}")

                    cost.pk = None  # új rekord készül
                    cost.cost_date = new_cost_date
                    cost.paid_date = new_cost_date
                    cost.create_cost_date = timezone.now()
                    cost.paid = 0
                    cost.save()

                    updated_costs.append(MonthlyCostSerializer(cost).data)

                except Cost.DoesNotExist:
                    logger.error(f"Cost with ID {cost_id} not found.")
                    return Response(
                        {
                            "success": False,
                            "message": f"Cost with ID {cost_id} not found.",
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

            return Response(
                {
                    "success": True,
                    "message": "Costs updated and new records created successfully.",
                    "data": updated_costs,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error while updating costs: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": f"Error while updating costs: {str(e)}",
                    "data": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Egyedi lekérés, módosítás, törlés
class CashFlowDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CashFlow.objects.all()
    serializer_class = CashFlowSerializer
    permission_classes = [IsAuthenticated]


class InvoiceAmountTransferAPIView(APIView):
    """
    API View for transferring an amount from one invoice (szamla1) to another (szamla2).
    The amount will be deducted from szamla1 and added to szamla2.
    """

    def patch(self, request, szamla1_id, szamla2_id, *args, **kwargs):
        # A serializer nem szükséges már, mivel az adatokat az URL-ből vesszük
        amount = request.data.get("amount")

        # Ellenőrizzük, hogy az amount létezik és nagyobb, mint 0
        if amount is None or amount <= 0:
            return Response(
                {"detail": "Amount must be greater than 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lekérdezzük a számlákat
        try:
            szamla1 = Invoice.objects.get(id=szamla1_id)
            szamla2 = Invoice.objects.get(id=szamla2_id)
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "One of the invoices does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ellenőrizzük, hogy szamla1-nek van elég pénze
        if szamla1.amount < amount:
            return Response(
                {"detail": "Insufficient funds on the first invoice."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Levonjuk az összeget szamla1-ből és hozzáadjuk szamla2-höz
        szamla1.amount -= amount
        szamla2.amount += amount

        # Mentjük az új adatokat
        szamla1.save()
        szamla2.save()

        # Válasz
        return Response(
            {
                "message": "Amount successfully transferred.",
                "szamla1": {"id": szamla1.id, "amount": szamla1.amount},
                "szamla2": {"id": szamla2.id, "amount": szamla2.amount},
            },
            status=status.HTTP_200_OK,
        )


class CurrentMonthCostGroup5View(APIView):
    def get(self, request):
        now = timezone.now()
        first_day = now.replace(day=1)
        if now.month == 12:
            last_day = first_day.replace(
                year=now.year + 1, month=1
            ) - timezone.timedelta(days=1)
        else:
            last_day = first_day.replace(month=now.month + 1) - timezone.timedelta(
                days=1
            )

        queryset = Cost.objects.filter(
            costgroup_id=5, cost_date__gte=first_day, cost_date__lte=last_day
        ).order_by("-cost_date")

        serializer = CostSerializerNatur(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CostGroupCostView(APIView):
    def get(self, request):
        # Aktuális időpont
        now = timezone.now()

        # Aktuális hónap kezdete és vége
        first_day_of_current_month = now.replace(day=1)
        if now.month < 12:
            first_day_of_next_month = now.replace(month=now.month + 1, day=1)
        else:
            first_day_of_next_month = now.replace(year=now.year + 1, month=1, day=1)
        last_day_of_current_month = first_day_of_next_month - timedelta(days=1)

        # Előző hónap kezdete és vége
        first_day_of_previous_month = (
            first_day_of_current_month - timedelta(days=1)
        ).replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)

        # Szűrés cost_date mező alapján
        cost_group_data = (
            Cost.objects.filter(
                cost_date__gte=first_day_of_current_month,
                cost_date__lte=last_day_of_current_month,
            )
            .values("costgroup__id", "costgroup__cost_group_name")
            .annotate(total_amount=Sum("amount"))
            .order_by("costgroup__id")
        )

        # Formázás
        result = defaultdict(list)
        for cost in cost_group_data:
            costgroup_id = cost["costgroup__id"]
            result[costgroup_id].append(
                {
                    "costgroup_name": cost["costgroup__cost_group_name"],
                    "total_amount": cost["total_amount"],
                }
            )

        response_data = {
            "filtered_dates": {
                "current_month_start": first_day_of_current_month.strftime("%Y-%m-%d"),
                "current_month_end": last_day_of_current_month.strftime("%Y-%m-%d"),
                "previous_month_start": first_day_of_previous_month.strftime(
                    "%Y-%m-%d"
                ),
                "previous_month_end": last_day_of_previous_month.strftime("%Y-%m-%d"),
            },
            "cost_groups": result,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class CostList(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        costs = Cost.objects.all()
        serializer = OnlyCostSerializer(costs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OnlyCostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)


class CreateCost(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Új költség hozzáadása."""
        serializer = OnlyCostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            invoice_id = request.data.get("invoice")
            amount = request.data.get("amount")
            paid = request.data.get("paid")  # Itt javítva volt a paid lekérdezése
            logger.info(f"invoice_id: {invoice_id}, amount: {amount}, paid: {paid}")

            if invoice_id and amount is not None and paid == 1:
                try:
                    invoice = Invoice.objects.get(id=invoice_id)
                    invoice.amount -= float(
                        amount
                    )  # konvertálás, hogy ne legyen típushiba
                    invoice.save()
                    logger.info(
                        f"Inovice update - invoice_id: {invoice_id}, new amount: {invoice.amount}"
                    )
                except Invoice.DoesNotExist:
                    logger.error("Invoice rekord nem található a megadott ID-vel")
                    return Response(
                        {"message": "Invoice rekord nem található a megadott ID-vel."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                except Exception as e:
                    logger.error(f"Ismeretlen hiba történt: {str(e)}")
                    return Response(
                        {"message": "Hiba történt a számla frissítésekor."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            return Response(
                {"message": "Költség sikeresen létrehozva.", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"message": "Hibás adatok.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class CostDetail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            cost = Cost.objects.get(pk=pk)
            if cost.user != self.request.user:
                raise Http404  # Nem a saját költsége
            return cost
        except Cost.DoesNotExist:
            raise Http404  # Nem létezik a költség

    def get(self, request, pk):
        cost = self.get_object(pk)
        serializer = OnlyCostSerializer(cost)
        return Response(serializer.data)

    def put(self, request, pk):
        cost = self.get_object(pk)
        serializer = OnlyCostSerializer(cost, data=request.data)
        if serializer.is_valid():
            invoice_id = cost.invoice.id
            amount = cost.amount
            paid = cost.paid
            logger.info(f"invoice_id: {invoice_id}, amount: {amount}, paid: {paid}")
            """ csak akkor vonja le ha paid 0 """
            if invoice_id and amount is not None and paid == 0:
                try:
                    invoice = Invoice.objects.get(id=invoice_id)
                    invoice.amount -= float(
                        amount
                    )  # konvertálás, hogy ne legyen típushiba
                    invoice.save()
                    logger.info(
                        f"Inovice update - invoice_id: {invoice_id}, new amount: {invoice.amount}"
                    )
                except Invoice.DoesNotExist:
                    logger.error("Invoice rekord nem található a megadott ID-vel")
                    return Response(
                        {"message": "Invoice rekord nem található a megadott ID-vel."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                except Exception as e:
                    logger.error(f"Ismeretlen hiba történt: {str(e)}")
                    return Response(
                        {"message": "Hiba történt a számla frissítésekor."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        cost = self.get_object(pk)
        cost.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


""" test """

""" test 2 mixins"""


class CostListMixins(
    mixins.ListModelMixin, mixins.CreateModelMixin, generics.GenericAPIView
):
    queryset = Cost.objects.all()
    serializer_class = OnlyCostSerializer

    def get(self, request):
        return self.list(request)

    def post(self, request):
        return self.create(request)


class CostDetailMixins(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    queryset = Cost.objects.all()
    serializer_class = OnlyCostSerializer

    def get(self, request, pk):
        return self.retrieve(request, pk)

    def put(self, request, pk):
        return self.update(request, pk)

    def delete(self, request, pk):
        return self.destroy(request, pk)


""" test 2 mixins"""

""" test 3 generics view """


class CostListGenView(generics.ListCreateAPIView):
    queryset = Cost.objects.all()
    serializer_class = OnlyCostSerializer


class CostDetailGenView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cost.objects.all()
    serializer_class = OnlyCostSerializer


""" test 3 generics view """

""" test 4 generics view """


class CostViewSet(viewsets.ModelViewSet):
    queryset = Cost.objects.all()
    serializer_class = OnlyCostSerializer


""" test 4 generics view """

""" test 5 generics view """


class CostListNestedView(generics.ListCreateAPIView):
    queryset = Cost.objects.all()
    serializer_class = CostNestedSerializer


class CostDetailNestedView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cost.objects.all()
    serializer_class = CostNestedSerializer


class InvoiceListNestedView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceNestedSerializer


class InvoiceNestedDetailGenView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceNestedSerializer


""" test 5 generics view """


# CostRepeat
class NewCostRepeatAV(APIView):
    """új costrepeat"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = OnlyCostRepeatSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


#
class AllCostRepeatListAV(APIView):
    """costrepeat alapján lista ami még nincs fizetve"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        costRepeat = (
            CostRepeat.objects.all()
            .filter(user=self.request.user)
            .filter(paid=0)
            .order_by("-expire_date")
        )
        serializer = CostRepeatSerializer(costRepeat, many=True)
        return Response(serializer.data)


class AllCostRepeatSumCostAV(APIView):
    """costrepeat id alapján sum a kifizetett cost
    melyikből costrepeat -ból mennyi van fizetve
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, paid):
        try:
            datefu = DateFu()
            if paid == "true":
                costs = (
                    Cost.objects.all()
                    .values("costrepeat")
                    .filter(costrepeat__isnull=False)
                    .filter(user=self.request.user)
                    .filter(paid=1)
                    .annotate(amount=Sum("amount"))
                )
            elif paid == "false":
                costs = (
                    Cost.objects.all()
                    .values("costrepeat")
                    .filter(costrepeat__isnull=False)
                    .filter(user=self.request.user)
                    .filter(paid=0)
                    .annotate(amount=Sum("amount"))
                )
            elif paid == "all":
                costs = (
                    Cost.objects.all()
                    .values("costrepeat")
                    .filter(costrepeat__isnull=False)
                    .filter(user=self.request.user)
                    .annotate(amount=Sum("amount"))
                )
            else:
                return Response(
                    {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
                )
        except Cost.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(costs)


# CostRepeat end
# CashFlow
class NewCashFlowAV(APIView):
    """új NewCashFlowSerializer"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NewCashFlowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


#
"""_summary_

Returns:
    _type_: _description_
"""


# list cashflow
class ListCashFlowAV(APIView):
    """list chasflow"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cashFlow = (
            CashFlow.objects.all()
            .filter(user=self.request.user)
            .order_by("-cash_flow_date")[:10]
        )
        serializer = ListCashFlowSerializer(cashFlow, many=True)
        return Response(serializer.data)


"""_summary_

Returns:
    _type_: _description_
"""
# list cashflow last rekord


class ListCashFlowLastAV(APIView):
    """list chasflow"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cashFlow = (
            CashFlow.objects.all()
            .filter(user=self.request.user)
            .order_by("-cash_flow_date")
            .first()
        )
        serializer = ListCashFlowSerializer(cashFlow, many=False)
        return Response(serializer.data)


# list cashflow filter date
class ListCashFlowFilterDateAV(APIView):
    """list chasflow date filter cash_flow_date
    havi fizrtések és becvételek lista
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, from_date):
        try:
            obj = (
                CashFlow.objects.all()
                .filter(user=self.request.user)
                .filter(cash_flow_date__qte__exact=from_date)
                .order_by("-cash_flow_date")
            )
        except CashFlow.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ListCashFlowSerializer(obj, many=True)
        return Response(serializer.data)


# CashFlow end
# CostGroup

"""_summary_

Returns:
    _type_: _description_
"""


class NewCostGroupAV(APIView):
    """új NewCostGroupAV"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NewCostGroupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


# CostGroup end
# CashFlowGroup
"""_summary_

Returns:
    _type_: _description_
"""


class NewCashFlowGroupAV(APIView):
    """új CashFlowGroup"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CashFlowGroupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)

    def get(self, request, paid):
        try:
            datefu = DateFu()
            if paid == "true":
                costRepeat = (
                    CostRepeat.objects.all()
                    .filter(user=self.request.user)
                    .filter(paid=1)
                )
                serializer = CostRepeatSerializer(costRepeat, many=True)
            elif paid == "false":
                costRepeat = (
                    CostRepeat.objects.all()
                    .filter(user=self.request.user)
                    .filter(paid=0)
                )
                serializer = CostRepeatSerializer(costRepeat, many=True)
            else:
                return Response(
                    {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
                )
        except CostRepeat.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.data)


# CashFlowGroup end

# Invoice


# invoice id at adja vissza
class AllInvoiceIDs(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = (
            Invoice.objects.filter(user=request.user)
            .filter(enable_invoice=1)
            .values("id", "invoice_name")
        )
        return Response({"invoices": list(data)})


# összes számla összegét összeadja


class AllInvoiceSumAmountObject(object):
    def __init__(self, totalAmountInvoice):
        self.totalAmountInvoice = totalAmountInvoice


"""_summary_

Returns:
    _type_: _description_
"""


class AllAmountInvoicesAPIView(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = (
            Invoice.objects.all()
            .filter(enable_invoice=1)
            .filter(user=self.request.user)
            .aggregate(total=Sum("amount"))["total"]
        )
        totalAmountInvoice = AllInvoiceSumAmountObject(data)
        serializer = AllInvoicesTotalAmountSerializer(totalAmountInvoice)
        return Response(serializer.data)


"""_summary_

Returns:
    _type_: _description_
"""


class OnlyInvoiceListAV(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invoices = (
            Invoice.objects.all()
            .filter(user=self.request.user)
            .filter(enable_invoice=1)
        )
        serializer = OnlyInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OnlyInvoiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


#
"""_summary_

Returns:
    _type_: _description_
"""


class InvoiceListAV(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invoices = (
            Invoice.objects.all()
            .filter(user=self.request.user)
            .filter(enable_invoice=1)
        )
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = InvoiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


"""_summary_

Returns:
    _type_: _description_
"""


class AllInvoiceSumCostAV(APIView):
    """kiadas összegezve összes számlára egy lekérdezésben"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, paid):
        try:
            datefu = DateFu()
            if paid == "true":
                costs = (
                    Cost.objects.all()
                    .values("invoice")
                    .filter(user=self.request.user)
                    .filter(paid=1)
                    .filter(
                        cost_date__gte=datefu.get_first_day(),
                        cost_date__lte=datefu.get_last_day(),
                    )
                    .annotate(amount=Sum("amount"))
                )
            elif paid == "false":
                costs = (
                    Cost.objects.all()
                    .values("invoice")
                    .filter(user=self.request.user)
                    .filter(paid=0)
                    .filter(
                        cost_date__gte=datefu.get_first_day(),
                        cost_date__lte=datefu.get_last_day(),
                    )
                    .annotate(amount=Sum("amount"))
                )
            elif paid == "all":
                costs = (
                    Cost.objects.all()
                    .values("invoice")
                    .filter(user=self.request.user)
                    .filter(
                        cost_date__gte=datefu.get_first_day(),
                        cost_date__lte=datefu.get_last_day(),
                    )
                    .annotate(amount=Sum("amount"))
                )
            else:
                return Response(
                    {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
                )
        except Cost.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(costs)


# számlánként külön rekordban fizteve, nem fizetve sum cost
class MonthlyCostSummaryView__(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_invoice_data(self, invoice_id):
        invoice = Invoice.objects.get(id=invoice_id)
        return {
            "id": invoice.id,
            "invoice_name": invoice.invoice_name,
            "invoice_note": invoice.invoice_note,
            "create_invoice_date": invoice.create_invoice_date,
            "enable_invoice": invoice.enable_invoice,
            "amount": invoice.amount,
        }


class MonthlyCostSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        datefu = DateFu()
        first_day = datefu.get_first_day()
        last_day = datefu.get_last_day()

        # Lekérdezzük az összes invoice-t, amiben van költség az adott hónapban
        invoice_ids = (
            Cost.objects.filter(user=user, cost_date__range=(first_day, last_day))
            .values_list("invoice", flat=True)
            .distinct()
        )

        invoices = Invoice.objects.filter(id__in=invoice_ids)

        results = []

        for invoice in invoices:
            total_paid = (
                Cost.objects.filter(
                    user=user,
                    invoice=invoice,
                    paid=1,
                    cost_date__range=(first_day, last_day),
                ).aggregate(Sum("amount"))["amount__sum"]
                or 0
            )

            total_unpaid = (
                Cost.objects.filter(
                    user=user,
                    invoice=invoice,
                    paid=0,
                    cost_date__range=(first_day, last_day),
                ).aggregate(Sum("amount"))["amount__sum"]
                or 0
            )

            results.append(
                {
                    "invoice": {
                        "id": invoice.id,
                        "invoice_name": invoice.invoice_name,
                        "invoice_note": invoice.invoice_note,
                        "create_invoice_date": invoice.create_invoice_date,
                        "enable_invoice": invoice.enable_invoice,
                        "amount": invoice.amount,
                    },
                    "total_paid": total_paid,
                    "total_unpaid": total_unpaid,
                }
            )

        serializer = CostSummarySerializer(results, many=True)
        return Response(serializer.data)


#


class InvoiceSumCostAV(APIView):
    """kiadas összegezve szamla id szerint"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id, paid):
        try:
            datefu = DateFu()
            if paid == "true":
                costs = (
                    Cost.objects.all()
                    .values()
                    .filter(invoice=invoice_id)
                    .filter(user=self.request.user)
                    .filter(paid=1)
                    .filter(
                        cost_date__gte=datefu.get_first_day(),
                        cost_date__lte=datefu.get_last_day(),
                    )
                    .aggregate(total=Sum("amount"))["total"]
                )
            if paid == "false":
                costs = (
                    Cost.objects.all()
                    .values()
                    .filter(invoice=invoice_id)
                    .filter(user=self.request.user)
                    .filter(paid=0)
                    .filter(
                        cost_date__gte=datefu.get_first_day(),
                        cost_date__lte=datefu.get_last_day(),
                    )
                    .aggregate(total=Sum("amount"))["total"]
                )
            if paid == "all":
                costs = (
                    Cost.objects.all()
                    .values()
                    .filter(invoice=invoice_id)
                    .filter(user=self.request.user)
                    .filter(
                        cost_date__gte=datefu.get_first_day(),
                        cost_date__lte=datefu.get_last_day(),
                    )
                    .aggregate(total=Sum("amount"))["total"]
                )
        except Cost.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "amount": costs,
                "get_first_day": datefu.get_first_day(),
                "get_last_day": datefu.get_last_day(),
                "invoice": invoice_id,
            }
        )


class InvoiceListWithFilterAV(generics.ListAPIView):
    queryset = Invoice.objects.all().filter(enable_invoice=1)
    serializer_class = InvoiceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["invoice_name", "invoice_note"]


class InvoiceListOrderingDate(generics.ListAPIView):
    queryset = Invoice.objects.all().filter(enable_invoice=1)
    serializer_class = InvoiceSerializer
    filter_backends = [filters.OrderingFilter]
    search_fields = ["create_invoice_date", "invoice_name"]


""" class InvoiceDetailAV(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data) """


class InvoiceDetailAV(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        three_months_ago = timezone.now() - timedelta(days=90)

        # Lekérjük az eredeti invoice-ot
        # Lekérjük a szűrt költségeket külön
        cost_invoices = invoice.cost_invoice.filter(
            cost_date__gte=three_months_ago
        ).order_by('-cost_date')

        # Átadjuk a serializernek plusz contextban
        serializer = InvoiceSerializer(
            invoice, context={"cost_invoices": cost_invoices}
        )
        return Response(serializer.data)


#
class OnlyInvoiceDetailAV(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OnlyInvoiceSerializer(invoice)
        return Response(serializer.data)

    def put(self, request, pk):
        invoice = Invoice.objects.get(pk=pk)
        serializer = OnlyInvoiceSerializer(invoice, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)

    def delete(self, request, pk):
        platform = OnlyInvoiceSerializer.objects.get(pk=pk)
        platform.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


#


class InvoiceWithCostDateUserFilterAV(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id, from_date, to_date):
        try:
            obj = (
                Cost.objects.all()
                .filter(invoice_id=invoice_id)
                .filter(user=self.request.user)
                .filter(paid_date__gte=from_date, paid_date__lte=to_date)
            )
        except Cost.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CostSerializer(obj, many=True)
        return Response(serializer.data)
        # Invoice end
        # Cost
        """_summary_
        Cost  classes
        Returns:
            _type_: _description_
        """


class NewCost(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = OnlyCostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


# parameterben megadott nap van e fizetendő kiadas


class ActualDayPayAmountListAV(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, actual_day):
        costs = (
            Cost.objects.all()
            .filter(user=self.request.user)
            .filter(paid_date=actual_day)
        )
        serializer = CostSerializer(costs, many=True)
        return Response(serializer.data)


class SumAllCostAV(APIView):
    """nem fizetett kiadasok"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, paid):
        try:
            if paid == "true":
                costs = (
                    Cost.objects.all()
                    .values()
                    .filter(user=self.request.user)
                    .filter(paid=1)
                    .aggregate(total=Sum("amount"))["total"]
                )
            if paid == "false":
                costs = (
                    Cost.objects.all()
                    .values()
                    .filter(user=self.request.user)
                    .filter(paid=0)
                    .aggregate(total=Sum("amount"))["total"]
                )
        except Cost.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"amount": costs, "paid": paid})


class CostListAV(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        costs = Cost.objects.all().filter(user=self.request.user)
        serializer = CostSerializer(costs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


class CostPagination(PageNumberPagination):
    page_size = 10  # oldalankénti elemek száma
    page_size_query_param = "page_size"
    max_page_size = 100


class ForeignKeyDataView(APIView):
    def get(self, request):
        invoices = (
            Invoice.objects.all()
            .filter(enable_invoice=1)
            .filter(user=self.request.user)
        )
        devs = Dev.objects.all()
        costrepeats = (
            CostRepeat.objects.all().filter(user=self.request.user).filter(paid=0)
        )
        costgroups = CostGroup.objects.all().filter(user=self.request.user)
        cashflowGroup = CashFlowGroup.objects.all()
        cash_flow_group_data = ForeignKeyCashFlowGroupSerializer(
            cashflowGroup, many=True
        ).data
        invoices_data = ForeignKeyInvoiceSerializer(invoices, many=True).data
        devs_data = ForeignKeyDevSerializer(devs, many=True).data
        costrepeats_data = ForeignKeyCostRepeatSerializer(costrepeats, many=True).data
        costgroups_data = ForeignKeyCostroupSerializer(costgroups, many=True).data

        return Response(
            {
                "invoices": invoices_data,
                "devs": devs_data,
                "costrepeats": costrepeats_data,
                "costgroups": costgroups_data,
                "cashflowgroup": cash_flow_group_data,
            },
            status=status.HTTP_200_OK,
        )


class CostListNatur(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        start_act, end_act = DateRangeHelper.get_current_month_range()
        start_prev, end_prev = DateRangeHelper.get_previous_month_range()
        costs = (
            Cost.objects.all()
            .filter(user=self.request.user)
            .filter(paid_date__gte=start_prev, paid_date__lte=end_act)
            .order_by("-cost_date")
        )
        paginator = CostPagination()
        result_page = paginator.paginate_queryset(costs, request)
        serializer = OnlyCostSerializer(result_page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["date_range"] = {
            "start_prev": start_prev.isoformat(),
            "end_act": end_act.isoformat(),
        }
        return response

    def post(self, request):
        serializer = OnlyCostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


class CostListWithFilterAV(generics.ListAPIView):
    queryset = Cost.objects.all()
    serializer_class = CostSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["cost_name", "cost_note", "cost_date"]

    # def get_queryset(self):
    #     cost_name = self.kwargs['cost_name']
    #     return Cost.objects.filter(cost_name = cost_name)


# # Cost end
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
