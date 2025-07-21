from django.contrib import admin
from .models import (
    Contract, Warehouse, Zone, Device, DeviceCategory,
    MaintenanceCard, Task, CoordinationRequest, ContractItem
)


# ✅ Inline for Warehouses inside Contract
class WarehouseInline(admin.TabularInline):
    model = Warehouse
    extra = 0


# ✅ Inline for Zones inside Contract
class ZoneInline(admin.TabularInline):
    model = Zone
    extra = 0


# ✅ Inline لعرض البنود داخل العقد
class ContractItemInline(admin.TabularInline):
    model = ContractItem
    extra = 1
    min_num = 1
    verbose_name = "Contract Item"
    verbose_name_plural = "Contract Items"
    # fields = ['category', 'quantity', 'notes']
    autocomplete_fields = []


# ✅ عقد مع البنود
@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'name', 'start_date', 'end_date']
    search_fields = ['contract_number', 'name']
    list_filter = ['start_date', 'end_date']
    inlines = [WarehouseInline, ZoneInline, ContractItemInline]


# ✅ تسجيل ContractItem مستقل أيضًا
@admin.register(ContractItem)
class ContractItemAdmin(admin.ModelAdmin):
    list_display = ['contract', 'get_category', 'quantity']
    list_filter = ['category__name']
    search_fields = ['contract__name']

    def get_category(self, obj):
        return obj.category.name
    get_category.short_description = 'Item Category'


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'contract')
    search_fields = ('name', 'location')
    list_filter = ('contract',)


# ✅ Inline for Devices in Zone
class DeviceInline(admin.TabularInline):
    model = Device
    extra = 0


# ✅ Inline for Tasks in Zone
class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


# ✅ Inline for CoordinationRequests in Zone
class CoordinationRequestInline(admin.TabularInline):
    model = CoordinationRequest
    extra = 0


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'contract')
    search_fields = ('id', 'name')
    list_filter = ('contract',)
    inlines = [DeviceInline, TaskInline, CoordinationRequestInline]


@admin.register(DeviceCategory)
class DeviceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    

# ✅ Inline for MaintenanceCard in Zone
class MaintenanceCardInline(admin.StackedInline):
    model = MaintenanceCard
    extra = 0

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'name', 'get_device_category', 'current_location', 'status', 'warehouse', 'zone', 'responsible_person')
    search_fields = ('serial_number', 'name', 'device_category__name', 'invoice_number', 'ip_address')
    list_filter = ('status', 'device_category', 'current_location', 'zone')
    list_editable = ('status', 'zone')
    inlines = [MaintenanceCardInline]
    fieldsets = (
    (None, {
        'fields': ('serial_number', 'name', 'device_category', 'invoice_number')
    }),
    ('Status and Location', {
        'fields': ('status', 'current_location', 'warehouse', 'zone', 'ip_address')
    }),
    ('Responsibility', {
        'fields': ('responsible_person', 'transfer_date', 'installation_date')
    }),
    ('Notes', {
        'fields': ('notes',)
    }),
    )

    def get_device_category(self, obj):
        return obj.device_category.name
    get_device_category.short_description = 'Device Category'


@admin.register(MaintenanceCard)
class MaintenanceCardAdmin(admin.ModelAdmin):
    list_display = ('device', 'report_date', 'issue_type', 'repair_date', 'technician')
    search_fields = ('device__serial_number', 'technician', 'issue_type')
    list_filter = ('technician', 'report_date', 'repair_date')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone', 'deadline', 'actual_delivery_date', 'status', 'remaining_days', 'delay_days')
    search_fields = ('name', 'zone__name')
    list_filter = ('status', 'deadline', 'zone')
    readonly_fields = ('remaining_days', 'delay_days')


@admin.register(CoordinationRequest)
class CoordinationRequestAdmin(admin.ModelAdmin):
    list_display = ('zone', 'target_department', 'work_type', 'expected_execution_date', 'responsible_person', 'email_sent_date')
    search_fields = ('target_department', 'responsible_person', 'work_type')
    list_filter = ('zone', 'target_department', 'expected_execution_date')
