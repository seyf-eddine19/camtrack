from django.db import models
from django.utils import timezone
from datetime import date
from django.db.models import Count

# 1. Contracts Table
class Contract(models.Model):
    contract_number = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    @property
    def tasks(self):
        return Task.objects.filter(zone__contract=self)

    @property
    def devices(self):
        return Device.objects.filter(zone__contract=self)

    @property
    def maintenance_cards(self):
        return MaintenanceCard.objects.filter(device__zone__contract=self)

    @property
    def coordination_requests(self):
        return CoordinationRequest.objects.filter(zone__contract=self)

    def __str__(self):
        return f"{self.contract_number} - {self.name}"

    class Meta:
        ordering = ['-start_date']


# 2. Devices Category Table
class DeviceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# 3. Contracts Items Table
class ContractItem(models.Model):
    contract = models.ForeignKey('Contract', to_field='contract_number', on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey('DeviceCategory', on_delete=models.PROTECT, related_name='contract_items')
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.contract.name} - {self.category} ({self.quantity})"


# 4. Warehouses Table
class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    contract = models.OneToOneField('Contract', to_field='contract_number', on_delete=models.CASCADE, related_name='warehouse')
   
    @property
    def count_zones(self):
        return self.contract.zones.count()

    @property
    def count_devices(self):
        return self.devices.count()

    @property
    def count_damaged(self):
        return self.devices.filter(status='damaged').count()

    @property
    def count_installed(self):
        return self.devices.filter(status='installed').count()

    @property
    def count_available(self):
        return self.devices.filter(status='available').count()

    @property
    def count_in_warehouse(self):
        return self.devices.filter(current_location='warehouse').count()
 
    @property
    def count_in_zones(self):
        return self.devices.filter(current_location='zone').count()

    @property
    def count_by_status(self):
        status_counts = self.devices.values('status').annotate(total=Count('serial_number'))
        return status_counts  # قالبك يعرضهم باستخدام for loop

    def __str__(self):
        return self.name


# 5. Zones Table
class Zone(models.Model):
    name = models.CharField(max_length=255)
    contract = models.ForeignKey('Contract', to_field='contract_number', on_delete=models.CASCADE, related_name='zones')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.contract.pk} | {self.name}"


# 6. Devices Table
class DeviceProperty(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='properties')
    key = models.CharField(max_length=100)  # مثل "mac_address", "serial_number", "firmware"
    value = models.CharField(max_length=255)  # قيمة الخاصية
    is_required = models.BooleanField(default=False)  # إذا أردت التحكم في هل هي مطلوبة أم لا

    class Meta:
        unique_together = ('device', 'key')

    def __str__(self):
        return f"{self.device.serial_number} - {self.key}: {self.value}"


class Device(models.Model):
    DEVICE_STATUS_CHOICES = [
        ('installed', 'Installed'),
        ('available', 'Available'),
        ('damaged', 'Damaged'),
    ]

    DEVICE_LOCATION_CHOICES = [
        ('warehouse', 'Warehouse'),
        ('zone', 'Zone'),
    ]

    serial_number = models.CharField(max_length=100, null=True, blank=True, unique=True)
    name = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=100)
    device_category = models.ForeignKey('DeviceCategory', on_delete=models.PROTECT, related_name='devices')
    warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name='devices')  # ✅ ربط الجهاز بالمخزن
    current_location = models.CharField(max_length=20, choices=DEVICE_LOCATION_CHOICES)
    zone = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    status = models.CharField(max_length=20, choices=DEVICE_STATUS_CHOICES)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    responsible_person = models.CharField(max_length=255)
    transfer_date = models.DateField(blank=True, null=True)
    installation_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    @property
    def count_maintenance_cards(self):
        return self.maintenance_cards.count()

    def save(self, *args, **kwargs):
        self.current_location = 'zone' if self.zone else 'warehouse'
        super().save(*args, **kwargs)

    def __str__(self):
        location = self.zone.name if self.zone else (self.warehouse.name if self.warehouse else "—")
        return f"{self.name} ({self.serial_number}) → {location}"


# 7. Maintenance Cards Table
class MaintenanceCard(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='maintenance_cards', verbose_name='الجهاز')
    report_date = models.DateField(blank=True, null=True, verbose_name='تاريخ البلاغ')
    issue_type = models.TextField(verbose_name='نوع المشكلة')
    repair_date = models.DateField(blank=True, null=True, verbose_name='تاريخ الإصلاح')
    technician = models.CharField(max_length=255, verbose_name='الفني المسؤول')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    
    class Meta:
        verbose_name = 'بطاقة صيانة'
        verbose_name_plural = 'بطاقات الصيانة'

    def save(self, *args, **kwargs):
        if self.repair_date:
            self.device.status = 'installed'
        else:
            self.device.status = 'damaged'
        self.device.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"الصيانة للجهاز {self.device.serial_number}"


# 8. Tasks (Timeline) Table
class Task(models.Model):
    TASK_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ]

    name = models.CharField(max_length=255)
    zone = models.ForeignKey('Zone', on_delete=models.CASCADE, related_name='tasks')
    deadline = models.DateField(default=date.today)
    actual_delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    
    @property
    def remaining_days(self):
        """حساب عدد الأيام المتبقية أو التأخير (بالموجب أو السالب)."""
        if not self.deadline:
            return 0
        reference_date = self.actual_delivery_date or timezone.now().date()
        return (self.deadline - reference_date).days
    
    @property
    def delay_days(self):
        """حساب عدد أيام التأخير إذا تم التسليم بعد الموعد."""
        if self.actual_delivery_date and self.deadline and self.actual_delivery_date > self.deadline:
            return (self.actual_delivery_date - self.deadline).days
        return 0

    def __str__(self):
        return f"{self.name} ({self.zone.name})"


# 9. Coordination Requests Table
class CoordinationRequest(models.Model):
    zone = models.ForeignKey('Zone', on_delete=models.CASCADE, related_name='coordination_requests', verbose_name='المنطقة')
    request_date = models.DateField(blank=True, null=True, verbose_name='تاريخ الطلب')
    target_department = models.CharField(max_length=255, verbose_name='الجهة المستهدفة')
    work_type = models.CharField(max_length=255, verbose_name='نوع العمل')
    location = models.CharField(max_length=255, verbose_name='الموقع')
    work_details = models.TextField(verbose_name='تفاصيل العمل')
    expected_execution_date = models.DateField(blank=True, null=True, verbose_name='تاريخ التنفيذ المتوقع')
    responsible_person = models.CharField(max_length=255, verbose_name='الشخص المسؤول')
    phone_number = models.CharField(max_length=20, verbose_name='رقم الهاتف')
    email_sent_date = models.DateField(blank=True, null=True, verbose_name='تاريخ إرسال البريد')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'طلب تنسيق'
        verbose_name_plural = 'طلبات التنسيق'

    def __str__(self):
        return f"Coordination for {self.zone.name} - {self.work_type}"
