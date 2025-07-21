from django import forms
from django.forms import inlineformset_factory
from django_select2.forms import Select2Widget
from .models import Contract, DeviceCategory, ContractItem, Zone, Warehouse, Device, MaintenanceCard, CoordinationRequest, Task


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ['contract_number', 'name', 'start_date', 'end_date', 'notes']
        widgets = {
            'contract_number': forms.DateInput(attrs={'class': 'form-control'}),
            'name': forms.DateInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class DeviceCategoryForm(forms.ModelForm):
    class Meta:
        model = DeviceCategory
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
        }


class ContractItemForm(forms.ModelForm):
    class Meta:
        model = ContractItem
        fields = ['category', 'quantity', 'notes']
        widgets = {
            'category': Select2Widget(attrs={'class': 'form-select select2'}),
            'quantity': forms.DateInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class ZoneForm(forms.ModelForm):
    class Meta:
        model = Zone
        fields = ['name', 'notes']
        widgets = {
            'name': forms.DateInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }


ContractItemFormSet = inlineformset_factory(
    Contract, ContractItem, form=ContractItemForm,
    extra=1, can_delete=True
)

ZoneFormSet = inlineformset_factory(
    Contract, Zone, form=ZoneForm,
    extra=1, can_delete=True
)


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['name', 'zone', 'deadline', 'status', 'notes']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'actual_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔽 تحسين واجهة الحقول
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [ 
            'serial_number', 'name', 'invoice_number', 'device_category', 
            'zone', 'status', 'ip_address', 'responsible_person', 
            'transfer_date', 'installation_date', 'notes',
        ]
        widgets = {
            'transfer_date': forms.DateInput(attrs={'type': 'date'}),
            'installation_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        contract = kwargs.pop('contract', None)
        super().__init__(*args, **kwargs)

        if contract:
            self.fields['zone'].queryset = Zone.objects.filter(contract=contract).order_by('name')
        else:
            self.fields['zone'].queryset = Zone.objects.none()

        # 🔽 تحسين واجهة الحقول
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class MaintenanceCardForm(forms.ModelForm):
    class Meta:
        model = MaintenanceCard
        fields = ['report_date', 'issue_type', 'repair_date', 'technician', 'notes']  # حذف حقل device
        widgets = {
            'report_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'repair_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'issue_type': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'technician': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class CoordinationRequestForm(forms.ModelForm):
    class Meta:
        model = CoordinationRequest
        fields = '__all__'
        widgets = {
            'request_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_execution_date': forms.DateInput(attrs={'type': 'date'}),
            'email_sent_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'work_details': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔽 تحسين واجهة الحقول
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'