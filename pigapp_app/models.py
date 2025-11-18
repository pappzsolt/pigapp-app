from datetime import date

from django.conf import settings
from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin, User)
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.authtoken.models import Token


class UserManager(BaseUserManager):
    """_summary_

    Args:
        BaseUserManager (_type_): _description_
    """

    def create_user(self, email, password=None, **extra_fields):
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """_summary_

    Args:
        AbstractBaseUser (_type_): _description_
        PermissionsMixin (_type_): _description_
    """

    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"


# Create your models here.


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def createAuthToken(sender, instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)


class CostGroup(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    id = models.AutoField(primary_key=True)
    cost_group_name = models.CharField(max_length=255)
    cost_group_note = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return self.cost_group_name

    def display_cost_group_name(self):
        return self.cost_group_name

    display_cost_group_name.short_description = "Cost group name"

    def display_cost_group_note(self):
        return self.cost_group_note

    display_cost_group_note.short_description = "Note"


class CashFlowGroup(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    id = models.AutoField(primary_key=True)
    cash_flow_group_name = models.CharField(max_length=255)
    cash_flow_group_note = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return self.cash_flow_group_name

    def display_cash_flow_group_name(self):
        return self.cash_flow_group_name

    display_cash_flow_group_name.short_description = "name"

    def display_cash_flow_group_note(self):
        return self.cash_flow_group_note

    display_cash_flow_group_note.short_description = "Note"


class Dev(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    id = models.AutoField(primary_key=True)
    dev_name = models.CharField(max_length=255)

    def __str__(self):
        return self.dev_name

    def display_dev_name(self):
        return self.dev_name

    display_dev_name.short_description = "Name"


class Invoice(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    id = models.AutoField(primary_key=True)
    invoice_name = models.CharField(max_length=255)
    invoice_note = models.CharField(max_length=255)
    create_invoice_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    enable_invoice = models.IntegerField(default=0, blank=True, null=True)
    amount = models.IntegerField(default=0, blank=True, null=True)

    def create_invoice(self):
        self.create_invoice_date = timezone.now()
        self.save()

    def __str__(self):
        return self.invoice_name

    def display_invoice_name(self):
        return self.invoice_name

    display_invoice_name.short_description = "Name"

    def display_create_invoice_date(self):
        return self.create_invoice_date.strftime("%Y-%m-%d")

    display_create_invoice_date.short_description = "Date"

    def display_enable_invoice(self):
        return self.enable_invoice

    display_enable_invoice.short_description = "Enable"

    def display_user(self):
        user = User.objects.all().filter(id=self.user.id)
        return user[0].username

    display_user.short_description = "User"


class CashFlow(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    id = models.AutoField(primary_key=True)
    cash_flow_name = models.CharField(max_length=255)
    cash_flow_note = models.CharField(max_length=255)
    amount = models.IntegerField(default=0, blank=True, null=True)
    invoice = models.ForeignKey(
        Invoice, related_name="cashflow_invoice", on_delete=models.CASCADE
    )
    dev = models.ForeignKey(Dev, related_name="dev", on_delete=models.CASCADE)
    cashflowgroup = models.ForeignKey(
        CashFlowGroup, related_name="cashflowgroup", on_delete=models.CASCADE
    )
    cash_flow_date = models.DateField()
    create_cash_flow_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def create_cash_flow(self):
        self.create_cash_flow_date = timezone.now()
        self.save()

    def __str__(self):
        return self.cash_flow_name

    @property
    def year_month_cash_flow_date(self):
        return self.cash_flow_date.strftime("%Y-%m")

    def display_cash_flow_name(self):
        return self.cash_flow_name[:15]

    display_cash_flow_name.short_description = "Name"

    def display_cash_flow_note(self):
        return self.cash_flow_note[:40]

    display_cash_flow_note.short_description = "Note"

    def display_cash_flow_date(self):
        return self.cash_flow_date.strftime("%Y-%m-%d")[:10]

    display_cash_flow_date.short_description = "Date"

    def display_create_cash_flow_date(self):
        return self.create_cash_flow_date.strftime("%Y-%m-%d")[:10]

    display_create_cash_flow_date.short_description = "Create date"

    def display_amount(self):
        return self.amount

    display_amount.short_description = "Amount"


class CostRepeat(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    id = models.AutoField(primary_key=True)
    cost_repeat_name = models.CharField(max_length=255)
    cost_repeat_note = models.CharField(max_length=255)
    amount = models.IntegerField(default=0, blank=True, null=True)
    cost_repeat_date = models.DateField()
    paid = models.IntegerField(default=0, blank=True, null=True)
    paid_date = models.DateField()
    expire_date = models.DateField(blank=True, null=True)
    create_cost_repeat_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def create_cost(self):
        self.create_cost_repeat_date = timezone.now()
        self.save()

    def __str__(self):
        return self.cost_repeat_name

    @property
    def days(self):
        return (self.cost_repeat_date - date.today()).days

    @property
    def year_month_cost_repeat_date(self):
        return self.cost_repeat_date.strftime("%Y-%m")

    def display_cost_repeat_name(self):
        return self.cost_repeat_name

    display_cost_repeat_name.short_description = "Name"

    def display_cost_repeat_date(self):
        return self.cost_repeat_date.strftime("%Y-%m-%d")[:10]

    display_cost_repeat_date.short_description = "Date"

    def display_paid_date(self):
        return self.paid_date.strftime("%Y-%m-%d")[:10]

    display_paid_date.short_description = "Paid Date"

    def display_create_cost_repeat_date(self):
        return self.create_cost_repeat_date.strftime("%Y-%m-%d")[:10]

    display_create_cost_repeat_date.short_description = "Create  Date"


class Cost(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """

    id = models.AutoField(primary_key=True)
    cost_name = models.CharField(max_length=255)
    cost_note = models.CharField(max_length=255)
    amount = models.IntegerField(default=0, blank=True, null=True)
    cost_date = models.DateField()
    invoice = models.ForeignKey(
        Invoice, related_name="cost_invoice", on_delete=models.CASCADE
    )
    dev = models.ForeignKey(Dev, on_delete=models.CASCADE)
    costrepeat = models.ForeignKey(
        CostRepeat, related_name="costrepeat", on_delete=models.CASCADE, null=True
    )
    costgroup = models.ForeignKey(
        CostGroup, related_name="costgroup", on_delete=models.CASCADE
    )
    paid = models.IntegerField(default=0, blank=True, null=True)
    paid_date = models.DateField()
    create_cost_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    static_pay = 0

    @staticmethod
    def set_pay(value):
        Cost.static_pay -= value

    @property
    def calculate_money(self):
        Cost.set_pay(self.amount)
        return Cost.static_pay

    @property
    def paid_date_diff(self):
        return (self.paid_date - date.today()).days

    def create_cost(self):
        self.create_cost_date = timezone.now()
        self.save()

    def __str__(self):
        return self.cost_name

    def display_cost_name(self):
        return self.cost_name[:15]

    display_cost_name.short_description = "Name"

    def display_cost_note(self):
        return self.cost_note

    display_cost_note.short_description = "Note"

    def display_cost_amount(self):
        return self.amount

    display_cost_amount.short_description = "Amount(Ft)"

    def display_cost_create_cost_date(self):
        return self.create_cost_date.strftime("%Y-%m-%d")[:10]

    display_cost_create_cost_date.short_description = "Create"

    def display_cost_date_ymd(self):
        return self.cost_date.strftime("%Y-%m-%d")[:10]

    display_cost_date_ymd.short_description = "Cost date"

    def display_paid_date_ymd(self):
        return self.paid_date.strftime("%Y-%m-%d")[:10]

    display_paid_date_ymd.short_description = "Paid date"

    @property
    def days(self):
        return (self.cost_date - date.today()).days

    @property
    def year_month_cost_date(self):
        return self.cost_date.strftime("%Y-%m")


class CostSum(Cost):
    """_summary_

    Args:
        Cost (_type_): _description_
    """

    def show_sum_amount(self, obj):
        result = Cost.objects.aggregate(Sum("amount"))
        return result["amount__sum"]
