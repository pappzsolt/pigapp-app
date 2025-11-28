from django.contrib.auth import authenticate, get_user_model
from django.db.models import Sum
from django.utils.translation import gettext as _
from pigapp_app.models import (CashFlow, CashFlowGroup, Cost, CostGroup,
                               CostRepeat, Dev, Invoice)
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Invoice

# serializers.py


class CibSummarySerializer(serializers.Serializer):
    """
    A CibStatementParser.parse_pdf() által visszaadott dict szerializálása.
    """

    all_transactions = serializers.ListField(child=serializers.DictField())
    outgoing_by_iban = serializers.DictField()
    daily_spending = serializers.DictField()
    internal_transfers = serializers.DictField()
    category_totals = serializers.DictField()


class CostSerializerToSum(serializers.ModelSerializer):
    class Meta:
        model = Cost
        fields = "__all__"


""" class CostRepeatWithCostsSerializeToSum(serializers.ModelSerializer):
    costs = CostSerializerToSum(many=True, source="costrepeat")
    total_amount = serializers.SerializerMethodField()
    cost_count = serializers.SerializerMethodField()

    class Meta:
        model = CostRepeat
        fields = "__all__"  # minden CostRepeat mező
        extra_fields = ["costs", "total_amount"]

    def get_total_amount(self, obj):
        return obj.costrepeat.aggregate(total=Sum("amount"))["total"] or 0

    def get_cost_count(self, obj):
        return obj.costrepeat.count() """


#
class CostRepeatWithCostsSerializeToSum(serializers.ModelSerializer):
    costs = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    cost_count = serializers.SerializerMethodField()

    class Meta:
        model = CostRepeat
        fields = "__all__"

    def get_costs(self, obj):
        costgroup_id = self.context.get("costgroup_id")
        qs = obj.costrepeat.all()
        if costgroup_id:
            qs = qs.filter(costgroup_id=costgroup_id)
        return CostSerializerToSum(qs, many=True).data

    def get_total_amount(self, obj):
        costgroup_id = self.context.get("costgroup_id")
        qs = obj.costrepeat.all()
        if costgroup_id:
            qs = qs.filter(costgroup_id=costgroup_id)
        return qs.aggregate(total=Sum("amount"))["total"] or 0

    def get_cost_count(self, obj):
        costgroup_id = self.context.get("costgroup_id")
        qs = obj.costrepeat.all()
        if costgroup_id:
            qs = qs.filter(costgroup_id=costgroup_id)
        return qs.count()


class CostRepeatTotalAmountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    total_amount = serializers.IntegerField()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # További mezők a JWT tokenbe:
        token["email"] = user.email
        token["username"] = user.username
        return token


class InvoiceAmountTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["amount"]


class MonthlyCostSerializer(serializers.ModelSerializer):
    invoice_name = serializers.CharField(source="invoice.name", read_only=True)

    class Meta:
        model = Cost
        fields = ["id", "cost_name", "cost_date", "amount", "invoice_name"]


class CashFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlow
        fields = "__all__"


class InvoiceComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "invoice_name"]


class ForeignKeyCashFlowGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlowGroup
        fields = ["id", "cash_flow_group_name"]


class ForeignKeyInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "invoice_name"]


class ForeignKeyDevSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dev
        fields = ["id", "dev_name"]


1


class ForeignKeyCostRepeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostRepeat
        fields = ["id", "cost_repeat_name"]


class ForeignKeyCostroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostGroup
        fields = ["id", "cost_group_name"]


class InvoiceSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    invoice_name = serializers.CharField()
    invoice_note = serializers.CharField()
    create_invoice_date = serializers.DateTimeField()
    enable_invoice = serializers.IntegerField()
    invoice_amount = serializers.IntegerField(
        source="amount"
    )  # Invoice összeg átnevezve


class CostSummarySerializer(serializers.Serializer):
    invoice = serializers.DictField()
    total_paid = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    total_unpaid = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )


class CostNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cost
        fields = "__all__"


class InvoiceNestedSerializer(serializers.ModelSerializer):
    costs = CostNestedSerializer(read_only=True, many=True)

    class Meta:
        model = Invoice
        fields = "__all__"


#
class AllInvoicesTotalAmountSerializer(serializers.Serializer):
    totalAmountInvoice = serializers.IntegerField()


#


class CostSerializerNatur(serializers.ModelSerializer):
    class Meta:
        model = Cost
        fields = "__all__"


class CostSerializer(serializers.ModelSerializer):
    invoice = serializers.StringRelatedField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    dev = serializers.StringRelatedField(read_only=True)
    costrepeat = serializers.StringRelatedField(read_only=True)
    costgroup = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Cost
        fields = "__all__"


#
class OnlyCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cost
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    len_name = serializers.SerializerMethodField()
    cost_invoice = serializers.SerializerMethodField()
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"

    def get_len_name(self, object):
        return len(object.invoice_name)

    def get_cost_invoice(self, obj):
        # A contextból vesszük ki a szűrt költségeket
        cost_invoices = self.context.get("cost_invoices")
        if cost_invoices is not None:
            return CostSerializer(cost_invoices, many=True).data
        # ha nincs szűrés, akkor minden költséget ad vissza
        return CostSerializer(obj.cost_invoice.all(), many=True).data


#
class OnlyInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"


#
class OnlyInvoiceSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"


class CostRepeatSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CostRepeat
        fields = "__all__"


class OnlyCostRepeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostRepeat
        fields = "__all__"


#
class CostGroupSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CostGroup
        fields = "__all__"


class NewCostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostGroup
        fields = "__all__"


class CashFlowGroupSerializer(serializers.ModelSerializer):
    # user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = CashFlowGroup
        fields = "__all__"


class NewCashFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlow
        fields = "__all__"


class ListCashFlowSerializer(serializers.ModelSerializer):
    cashflowgroup = serializers.StringRelatedField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    invoice = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CashFlow
        fields = "__all__"


#
class UserSerializer(serializers.ModelSerializer):
    """Model definition for MODELNAME."""

    class Meta:
        model = get_user_model()
        fields = ["email", "password", "name"]
        extra_kwargs = {"password": {"write_only": True, "min_length": 5}}

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class AuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        style={"input_type": "password"},
        trim_whitespace=False,
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )
        if not user:
            msg = _("Unable to authenticate")
            raise serializers.ValidationError(msg, code="authorization")
        attrs["user"] = user
        return attrs
        attrs["user"] = user
        return attrs
