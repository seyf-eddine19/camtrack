from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django_select2.forms import Select2Widget
from .models import Contract, ContractItem, Zone, Warehouse, DeviceCategory, Device, DeviceProperty, MaintenanceCard, CoordinationRequest, Task

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Current Password")
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="New Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirm New Password")

    def clean(self):
        cleaned_data = super().clean()
        new = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')
        if new and confirm and new != confirm:
            raise forms.ValidationError("New passwords do not match.")
        return cleaned_data


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ['contract_number', 'name', 'start_date', 'end_date', 'notes']
        widgets = {
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
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
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class ZoneForm(forms.ModelForm):
    class Meta:
        model = Zone
        fields = ['name', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
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


ContractItemFormSet = inlineformset_factory(Contract, ContractItem, form=ContractItemForm, extra=1, can_delete=True)
ZoneFormSet = inlineformset_factory(Contract, Zone, form=ZoneForm, extra=1, can_delete=True)


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['name', 'zone', 'deadline', 'actual_delivery_date', 'status', 'notes']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'actual_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.fields['zone'].queryset = Zone.objects.filter(contract=contract).order_by('name') if contract else Zone.objects.none()
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class DevicePropertyForm(forms.ModelForm):
    class Meta:
        model = DeviceProperty
        fields = ['key', 'value', 'is_required']
        widgets = {
            'key': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.TextInput(attrs={'class': 'form-control'}),
        }


DevicePropertyFormSet = inlineformset_factory(Device, DeviceProperty, form=DevicePropertyForm, extra=1, can_delete=True)


class MaintenanceCardForm(forms.ModelForm):
    class Meta:
        model = MaintenanceCard
        fields = ['report_date', 'issue_type', 'repair_date', 'technician', 'notes']
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
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
