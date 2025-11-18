import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from pigapp_app import serializers
from pigapp_app.models import (CashFlow, CashFlowGroup, Cost, CostGroup,
                               CostRepeat, Dev, Invoice)
from pigapp_app.serializers import (AuthTokenSerializer, UserSerializer)
from rest_framework import (authentication, filters, generics, mixins,
                            permissions, viewsets)
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from .datefu import DateFu

logger = logging.getLogger(__name__)

#


class AllInvoiceSumAmount(object):

    def __init__(self, totalAmountInvoice):
        self.totalAmountInvoice = totalAmountInvoice


class AllAmountInvoicesAPIView(APIView):

    def get(self, request):
        data = Invoice.objects.all().aggregate(total=Sum('amount'))['total']
        totalAmountCost = AllInvoiceSumAmount(data)
        serializer = serializers.AllInvoicesTotalAmountSerializer(totalAmountCost)
        return Response(serializer.data)


class AllInvoiceSumAmountAPIView(APIView):

    def get(self, request, invoice_id):
        try:
            resultAmount = (
                Invoice.objects.all().values().filter(id=invoice_id)[0]['amount']
            )
            resultInvoiceName = (
                Invoice.objects.all().values("invoice_name").filter(id=invoice_id)
            )
            notPaidCost = (
                Cost.objects.values('id', 'invoice_id', 'paid')
                .filter(paid=0)
                .filter(invoice_id=invoice_id)
                .count()
            )
            if type(notPaidCost) == type(None):
                notPaidCost = 0
            if type(resultAmount) == type(None):
                resultAmount = 0
            if type(resultInvoiceName) == type(None):
                resultInvoiceName = ""
            return Response(
                {
                    'Invoice': resultInvoiceName,
                    'amount': str(resultAmount),
                    'not paid count': str(notPaidCost),
                }
            )
        except ObjectDoesNotExist as error:
            logger.error(error)
            return Response({'result': str(error)})
        except Exception as error:
            logger.error(error)
            return Response({'result': str(error)})


class RestMoneyAPIView(APIView):

    def get(self, request, invoice_id):
        param = invoice_id
        try:
            invoiceAmount = Invoice.objects.all().values().filter(id=param)[0]['amount']
            allCost = (
                Cost.objects.all()
                .values()
                .filter(invoice=param)
                .filter(paid=0)
                .aggregate(total=Sum('amount'))['total']
            )
            if type(invoiceAmount) == type(None):
                result = 0
            elif type(allCost) == type(None):
                result = 0
            else:
                result = invoiceAmount - allCost
            return Response({'result': str(result)})
        except ObjectDoesNotExist as error:
            logger.error(error)
            return Response({'result': str(error)})
        except TypeError as error:
            logger.error(str(error))
            return Response({'result': +str(error)})
        except Exception as error:
            logger.error(error)
            return Response({'result': +str(error)})


class GetActualMonthLastFivePayAPIView(APIView):
    def get(self, request, invoice_id):
        param = invoice_id
        try:
            # result = Cost.objects.all().filter(paid =1).filter(invoice_id = param).order_by('-cost_date')[:5:1]
            result = (
                Cost.objects.values(
                    'id',
                    'invoice_id',
                    'cost_name',
                    'cost_note',
                    'amount',
                    'cost_date',
                    'dev',
                    'costrepeat',
                    'costgroup',
                    'paid',
                    'paid_date',
                )
                .filter(paid=1)
                .filter(invoice_id=param)
                .order_by('-cost_date')[:5:1]
            )
            if type(result) == type(None):
                result = 0
            return Response(result)
        except ObjectDoesNotExist as error:
            logger.error(error)
            return Response({'result': +str(error)})
        except Exception as error:
            logger.error(error)
            return Response({'result': +str(error)})


class GetActualMonthNextDayPayAPIView(APIView):
    def get(self, request, invoice_id):
        try:
            datefu = DateFu()
            result = (
                Cost.objects.values(
                    'id',
                    'invoice_id',
                    'cost_name',
                    'cost_note',
                    'amount',
                    'cost_date',
                    'dev',
                    'costrepeat',
                    'costgroup',
                    'paid',
                    'paid_date',
                )
                .filter(
                    paid_date__gte=datefu.get_first_day(),
                    paid_date__lte=datefu.get_last_day(),
                )
                .filter(paid=0)
                .filter(invoice_id=invoice_id)
                .order_by('-paid_date')[:5:1]
            )
            if type(result) == type(None):
                result = 0
            return Response(result)
        except ObjectDoesNotExist as error:
            logger.error(error)
            return Response({'result': +str(error)})
        except Exception as error:
            logger.error(error)
            return Response({'result': +str(error)})


#
class InvoiceWithCostFilterInvIdUserAPIView(APIView):

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id):
        # obj = Cost.objects.filter(invoice_id=invoice_id).filter(user=self.request.user )
        # obj = Cost.objects.all().filter(invoice_id=invoice_id).filter(user=self.request.user )
        obj = (
            Cost.objects.values(
                'id',
                'invoice_id',
                'cost_name',
                'cost_note',
                'amount',
                'cost_date',
                'dev',
                'costrepeat',
                'costgroup',
                'paid',
                'paid_date',
            )
            .filter(invoice_id=invoice_id)
            .filter(user=self.request.user)
        )
        # obj = serializers.InvoiceWithCostBaseObject([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        # serializer = serializers.InvoiceWithCostSerializer(obj)
        # return Response(serializer.data)
        return Response(obj)


class InvoiceWithCostFilterInvIdUserActualFromDToDAPIView(APIView):

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id, fromd, tod):

        try:
            obj = (
                Cost.objects.values(
                    'id',
                    'invoice_id',
                    'cost_name',
                    'cost_note',
                    'amount',
                    'cost_date',
                    'dev',
                    'costrepeat',
                    'costgroup',
                    'paid',
                    'paid_date',
                )
                .filter(invoice_id=invoice_id)
                .filter(user=self.request.user)
                .filter(paid_date__gte=fromd, paid_date__lte=tod)
            )
            return Response(obj)
        except Exception as e:
            logger.error(str(e))

        return Response("error")


class InvoiceWithCostFilterInvIdUserFirstLastDayWithPaidAPIView(APIView):

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id, paid):
        datefu = DateFu()
        try:
            obj = (
                Cost.objects.values(
                    'id',
                    'invoice_id',
                    'cost_name',
                    'cost_note',
                    'amount',
                    'cost_date',
                    'dev',
                    'costrepeat',
                    'costgroup',
                    'paid',
                    'paid_date',
                )
                .filter(invoice_id=invoice_id)
                .filter(paid=paid)
                .filter(user=self.request.user)
                .filter(
                    paid_date__gte=datefu.get_first_day(),
                    paid_date__lte=datefu.get_last_day(),
                )
            )
            return Response(obj)
        except Exception as e:
            logger.error(str(e))

        return Response("error")


class TotalAmountCost(object):
    """_summary_
    use CostTotalAmountView
    Args:
        object (_type_): _description_
    """

    def __init__(self, totalAmountCost):
        self.totalAmountCost = totalAmountCost


class CostTotalAmountView(APIView):
    """_summary_
    get total a,amount invoice and paid filter + user
    Args:
        APIView (_type_): _description_
    """

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id, paid):
        invoice_id = invoice_id
        paid = paid
        data = (
            Cost.objects.filter(invoice_id=invoice_id)
            .filter(paid=paid)
            .filter(user=self.request.user)
            .aggregate(total=Sum('amount'))['total']
        )
        totalAmountCost = TotalAmountCost(data)
        serializer = serializers.CostTotalAmountSerializer(totalAmountCost)
        return Response(serializer.data)


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


class InvoiceListView(generics.ListAPIView):
    queryset = Invoice.objects.all()
    serializer_class = serializers.InvoiceSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['invoice_name', 'create_invoice_date']
    ordering = ['invoice_name']


class CashFlowListView(generics.ListAPIView):
    queryset = CashFlow.objects.all()
    serializer_class = serializers.CashFlowSerializer


class CostSerializerListView(generics.ListAPIView):
    """_summary_
        invoice filter add 4!!!!!
    Args:
        generics (_type_): _description_
    """

    queryset = Cost.objects.all()
    serializer_class = serializers.CostSerializer


class CreateTokenView(ObtainAuthToken):
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CostViewSet(viewsets.ModelViewSet):
    """View for manage PigApp APIs."""

    serializer_class = serializers.CostSerializer
    queryset = Cost.objects.all()
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CostSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CostGroupViewSet(viewsets.ModelViewSet):
    """Manage CostGroup"""

    serializer_class = serializers.CostGroupSerializer
    queryset = CostGroup.objects.all()
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.all().order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CostGroupSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CashFlowGroupViewSet(
    viewsets.ModelViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    """Manage CashFlowGroup"""

    serializer_class = serializers.CashFlowGroupSerializer
    queryset = CashFlowGroup.objects.all()
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CashFlowGroupSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DevViewSet(
    viewsets.ModelViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    """Manage Dev"""

    serializer_class = serializers.DevSerializer
    queryset = Dev.objects.all()
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.DevSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save()


class InvoiceViewSet(viewsets.ModelViewSet):
    """Manage Invoice"""

    serializer_class = serializers.InvoiceSerializer
    queryset = Invoice.objects.all()
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.InvoiceSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CashFlowViewSet(
    viewsets.ModelViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    """Manage CashFlow"""

    serializer_class = serializers.CashFlowSerializer
    queryset = CashFlow.objects.all()
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CashFlowSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CostRepeatFlowViewSet(viewsets.ModelViewSet):
    """Manage CostRepeat"""

    serializer_class = serializers.CostRepeatSerializer
    queryset = CostRepeat.objects.all()
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CostRepeatSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
