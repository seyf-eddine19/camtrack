import os
from io import BytesIO
from datetime import datetime, date
from decimal import Decimal

from django.http import HttpResponse
from django.utils.text import slugify
from django.conf import settings

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle

import arabic_reshaper
from bidi.algorithm import get_display

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, DeleteView, CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Count, Q, F
from .forms import (
    ContractForm, DeviceCategoryForm, ContractItemFormSet, ZoneFormSet, WarehouseForm, TaskForm, DeviceForm, MaintenanceCardForm, CoordinationRequestForm 
)
from .models import (
    Contract, DeviceCategory, ContractItem, Warehouse, Zone, Task, Device, DeviceCategory, MaintenanceCard, CoordinationRequest
) 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from svglib.svglib import svg2rlg


# Export Excels & PDFs
class ExportMixin:
    """Mixin to export any ListView data to an Excel or PDF file with proper Arabic support."""
    def get(self, request, *args, **kwargs):
        """Export data when 'export' is in request GET parameters."""
        if "export" in request.GET:
            export_format = request.GET.get("format", "excel")  # Default to 'excel'
            queryset = self.get_queryset()

            if not queryset.exists():
                return HttpResponse("No data available for export.", content_type="text/plain")

            if export_format == "pdf":
                return self.export_to_pdf(queryset)
            else:
                return self.export_to_excel(queryset)

        return super().get(request, *args, **kwargs)

    def prepare_export_response(self, content, file_type, model_name):
        """Prepare and return a file response with a timestamped filename."""
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        safe_model_name = slugify(model_name) or "export"
        filename = f"export_{safe_model_name}_{timestamp}.{file_type}"

        content_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
        }

        response = HttpResponse(content, content_type=content_types.get(file_type, "application/octet-stream"))
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def export_to_excel(self, queryset):
        """Generate an Excel file from a queryset with all fields, modern style."""
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = f"{queryset.model._meta.verbose_name_plural}"

        # Get field names dynamically
        fields = [field.name for field in queryset.model._meta.fields[1:]]
        fields1 = [field.verbose_name for field in queryset.model._meta.fields[1:]]

        # Set modern header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = openpyxl.styles.PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        # Write headers with styles
        for col_num, field_name in enumerate(fields1, 1):
            cell = sheet.cell(row=1, column=col_num, value=field_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # Set the column width dynamically based on the length of the content
        for col_num, field_name in enumerate(fields1, 1):
            column_width = max(len(field_name), 15)  # Ensure a minimum width of 15
            sheet.column_dimensions[get_column_letter(col_num)].width = column_width

        # Write rows
        for obj in queryset:
            row = []
            for field in fields:
                value = getattr(obj, field, "")

                # Handle related fields (ForeignKey, ManyToMany, etc.)
                if isinstance(value, str):
                    row.append(value)
                elif hasattr(value, 'get_FOO_display'):  # For choices-based fields
                    row.append(value.get_FOO_display())
                else:
                    # Check if the field is a related object (e.g., ForeignKey)
                    related_object = getattr(obj, field, None)
                    if related_object:
                        row.append(str(related_object))  # Get the string representation
                    else:
                        row.append("")

            sheet.append(row)

        # Apply border style for all cells
        border_style = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

        for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
            for cell in row:
                cell.border = border_style

        # Save workbook to memory
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        content = output.read()
        file_type = "xlsx"
        model_name = queryset.model._meta.model_name
        return self.prepare_export_response(content, file_type, model_name)

    def export_to_pdf(self, queryset):
        """Generate a properly formatted PDF with RTL Arabic support and custom font."""
        model_name = queryset.model._meta.model_name

        # Create an in-memory buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=10, leftMargin=10, topMargin=20, bottomMargin=20)


        # Load Arabic font
        font_path = os.path.abspath(os.path.join(settings.STATIC_ROOT, "contracts", "fonts", "Janna LT Bold", "Janna LT Bold.ttf"))
        pdfmetrics.registerFont(TTFont("Janna", font_path))

        elements = []
        # Table Headers (Right-aligned for Arabic)
        fields = [[field.name, field.verbose_name] for field in queryset.model._meta.fields[-1:0:-1]]
        headers = [get_display(arabic_reshaper.reshape(field[1])) for field in fields]
        table_data = [headers]  # Table header

        max_col_lengths = [len(header) for header in headers]
        # Table Rows
        for obj in queryset:
            row = []
            for i, field in enumerate(fields):
                value = getattr(obj, field[0], "")

                if isinstance(value, bool):
                    value = "نعم" if value else "لا"
                elif isinstance(value, (float, Decimal)):
                    value = "{:,.2f}".format(value)
                elif isinstance(value, (datetime, date)):
                    value = value.strftime("%Y-%m-%d")
                elif hasattr(obj, f"get_{field[0]}_display"):
                    value = getattr(obj, f"get_{field[0]}_display")()  # Choice fields

                value = str(value) if value else ""

                # Fix Arabic text order
                if any("\u0600" <= c <= "\u06FF" for c in value):
                    value = get_display(arabic_reshaper.reshape(value))

                row.append(value)
                max_col_lengths[i] = max(max_col_lengths[i], len(value))  # Track longest text

            table_data.append(row)

        # Calculate column widths dynamically
        total_width = 780  # Approximate A4 width in landscape mode (in points)
        min_width = 80  # Minimum column width
        max_width = 220  # Maximum column width
        scale_factor = total_width / sum(max_col_lengths)  # Normalize sizes

        col_widths = [max(min_width, min(int(l * scale_factor), max_width)) for l in max_col_lengths]

        # Create Table
        table = Table(table_data, colWidths=col_widths)


        # Create Table
        # table = Table(table_data, colWidths=[len(fields)-20] * len(fields))
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Janna"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ]))

        # **Title (Centered and Bold)**
        title_text = get_display(arabic_reshaper.reshape(f"تقرير {queryset.model._meta.verbose_name_plural}"))
        title_style = ParagraphStyle(name="Title", fontName="Janna", fontSize=16, alignment=1, spaceAfter=20)

        # **Subtitle (Smaller text under the title)**
        subtitle_text = get_display(arabic_reshaper.reshape(f"قائمة {queryset.model._meta.verbose_name_plural} المصدرة من النظام"))
        subtitle_style = ParagraphStyle(name="Subtitle", fontName="Janna", fontSize=10, alignment=1, textColor=colors.grey)

        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 20))
        elements.append(table)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(subtitle_text, subtitle_style))


        doc.build(elements)

        # Get PDF content from buffer
        pdf_content = buffer.getvalue()
        buffer.close()

        # Use `prepare_export_response` for consistent file handling
        return self.prepare_export_response(pdf_content, "pdf", model_name)

class ExportMixin:
    def get(self, request, *args, **kwargs):
        if "export" in request.GET:
            export_format = request.GET.get("format", "excel")
            queryset = self.get_queryset()

            if not queryset.exists():
                return HttpResponse("لا توجد بيانات للتصدير", content_type="text/plain")

            if export_format == "pdf":
                return self.export_to_pdf(queryset)
            else:
                return self.export_to_excel(queryset)

        return super().get(request, *args, **kwargs)

    def prepare_export_response(self, content, file_type, model_name):
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        safe_model_name = slugify(model_name) or "export"
        filename = f"export_{safe_model_name}_{timestamp}.{file_type}"

        content_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
        }

        response = HttpResponse(content, content_type=content_types.get(file_type, "application/octet-stream"))
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def export_to_excel(self, queryset):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = f"{queryset.model._meta.verbose_name_plural}"

        fields = [field.name for field in queryset.model._meta.fields[1:]]
        headers = [field.verbose_name for field in queryset.model._meta.fields[1:]]

        # Header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = openpyxl.styles.PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        for col_num, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            sheet.column_dimensions[get_column_letter(col_num)].width = max(15, len(header) + 2)

        for obj in queryset:
            row = []
            for field in fields:
                value = getattr(obj, field, "")
                if hasattr(value, "get_FOO_display"):
                    value = value.get_FOO_display()
                elif hasattr(value, "__str__"):
                    value = str(value)
                row.append(value)
            sheet.append(row)

        # Apply border to all cells
        border = Border(left=Side(style="thin"), right=Side(style="thin"),
                        top=Side(style="thin"), bottom=Side(style="thin"))

        for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row,
                                   min_col=1, max_col=sheet.max_column):
            for cell in row:
                cell.border = border

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        return self.prepare_export_response(output.read(), "xlsx", queryset.model._meta.model_name)

    def export_to_pdf(self, queryset):
        model_name = queryset.model._meta.model_name
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=10,
            leftMargin=10,
            topMargin=4,
            bottomMargin=20
        )

        font_path = os.path.join(settings.STATIC_ROOT, "contracts/fonts/Janna LT Bold/Janna LT Bold.ttf")
        pdfmetrics.registerFont(TTFont("Janna", font_path))

        elements = []

        # ✅ إضافة صورة SVG
        svg_path = os.path.join(settings.STATIC_ROOT, "contracts/img/logo-1.svg")

        drawing = svg2rlg(svg_path)
        drawing.scale(1, 1)  # التحكم بالحجم
        drawing.hAlign = "LEFT"

        # إعداد العنوان
        title_text = get_display(arabic_reshaper.reshape(f"تقرير {queryset.model._meta.verbose_name_plural}"))
        title_style = ParagraphStyle(name="Title", fontName="Janna", fontSize=20, alignment=1, spaceAfter=0)
        title_paragraph = Paragraph(title_text, title_style)

        # إنشاء جدول مكون من عمودين: [الصورة, العنوان]
        title_table = Table(
            data=[[drawing, title_paragraph]],
            colWidths=[80, 650],  # يمكنك تعديل العرض حسب حجم الصورة والعنوان
            hAlign='RIGHT'
        )
        title_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "RIGHT"),  # الصورة
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),  # العنوان
        ]))

        elements.append(title_table)
        elements.append(Spacer(1, 25))

        # ✅ جدول البيانات
        fields = [[field.name, field.verbose_name] for field in queryset.model._meta.fields[-1:0:-1]]
        headers = [get_display(arabic_reshaper.reshape(field[1])) for field in fields]
        table_data = [headers]
        max_col_lengths = [len(h) for h in headers]

        for obj in queryset:
            row = []
            for i, field in enumerate(fields):
                value = getattr(obj, field[0], "")
                if hasattr(obj, f"get_{field[0]}_display"):
                    value = getattr(obj, f"get_{field[0]}_display")()
                elif isinstance(value, (datetime, date)):
                    value = value.strftime("%Y-%m-%d")
                elif isinstance(value, bool):
                    value = "نعم" if value else "لا"
                else:
                    value = str(value)

                if any("\u0600" <= c <= "\u06FF" for c in value):
                    value = get_display(arabic_reshaper.reshape(value))

                max_col_lengths[i] = max(max_col_lengths[i], len(value))
                row.append(value)
            table_data.append(row)

        # ✅ تحديد عرض الأعمدة تلقائيًا
        total_width = 780
        min_width = 55
        max_width = 220 
        col_widths = []
        sum_lengths = sum(max_col_lengths) or 1 
        col_widths = [
          max(min_width, min((length / sum_lengths) * total_width, max_width)) 
          for length in max_col_lengths
        ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), "Janna"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 16))

        doc.build(elements)
        return self.prepare_export_response(buffer.getvalue(), "pdf", model_name)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user
        context['groups'] = user.groups.all()
        return context


class LogoutView(DjangoLogoutView):
    next_page = reverse_lazy('login')


class DashboardView(TemplateView):
    template_name = "contracts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['contracts_count'] = Contract.objects.count()
        context['devices_count'] = Device.objects.count()
        context['damaged_devices'] = Device.objects.filter(status='damaged').count()
        context['tasks_delayed'] = Task.objects.filter(status='delayed').count()
        context['tasks_ongoing'] = Task.objects.filter(status='ongoing').count()
        context['maintenance_count'] = MaintenanceCard.objects.count()

        # توزيع الأجهزة حسب الموقع
        # context['devices_by_location'] = Device.objects.values('current_location').annotate(total=models.Count('serial_number'))

        # # توزيع الأجهزة حسب الحالة
        # context['devices_by_status'] = Device.objects.values('status').annotate(total=models.Count('serial_number'))

        return context


class DashboardView(TemplateView):
    template_name = 'contracts/tasks_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        contract_id = self.request.GET.get('contract')
        zone_id = self.request.GET.get('zone')
        status = self.request.GET.get('status')
        filter_type = self.request.GET.get('filter')

        tasks = Task.objects.all()

        if contract_id:
            tasks = tasks.filter(zone__contract__contract_number=contract_id)
        else:
            last_contract = Contract.objects.last()
            if last_contract:
                contract_id = last_contract.contract_number
                tasks = tasks.filter(zone__contract=last_contract)

        if zone_id:
            tasks = tasks.filter(zone_id=zone_id)

        if status:
            tasks = tasks.filter(status=status)

        if filter_type == 'late_only':
            tasks = tasks.filter(deadline__lt=timezone.now().date(), status__in=['not_started', 'ongoing'])

        elif filter_type == 'completed_after_deadline':
            tasks = tasks.filter(actual_delivery_date__gt=models.F('deadline'), status='completed')

        context.update({
            'contracts': Contract.objects.all(),
            'zones': Zone.objects.filter(contract__contract_number=contract_id),
            'filter_contract': contract_id,
            'filter_zone': zone_id,
            'filter_status': status,
            'filter_type': filter_type,
            'tasks': tasks,

            # إحصائيات
            'total_tasks': tasks.count(),
            'late_tasks': tasks.filter(deadline__lt=timezone.now().date(), status__in=['not_started', 'ongoing']).count(),
            'completed_late': tasks.filter(actual_delivery_date__gt=F('deadline'), status='completed').count(),
        })
        return context


class DashboardView(TemplateView):
    template_name = 'contracts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        total_contracts = Contract.objects.count()
        total_devices = Device.objects.count()
        total_tasks = Task.objects.count()
        late_tasks = Task.objects.filter(deadline__lt=timezone.now().date(), status__in=['not_started', 'ongoing']).count()
        maintenance_count = MaintenanceCard.objects.count()
        coordination_count = CoordinationRequest.objects.count()

        context.update({
            'total_contracts': total_contracts,
            'total_devices': total_devices,
            'total_tasks': total_tasks,
            'late_tasks': late_tasks,
            'maintenance_count': maintenance_count,
            'coordination_count': coordination_count,
            'latest_contracts': Contract.objects.order_by('-start_date')[:5],
            'latest_tasks': Task.objects.order_by('-deadline')[:5],
        })

        return context


class ContractListView(ListView):
    model = Contract
    template_name = 'contracts/contracts/list.html'
    context_object_name = 'contracts'


class ContractDeleteView(DeleteView):
    model = Contract
    template_name = 'contracts/contracts/delete.html'
    context_object_name = 'contracts'
    success_url = reverse_lazy('contract_list')
    
    def delete(self, request, *args, **kwargs):
        contract = self.get_object()
        messages.success(request, f"Contract '{contract.name}' was deleted successfully.")
        return super().delete(request, *args, **kwargs)


class ContractDetailView(DetailView):
    model = Contract
    template_name = 'contracts/contracts/detail.html'
    context_object_name = 'contract'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.object

        context["items"] = contract.items.all()
        context["zones"] = contract.zones.all()
        context["warehouse"] = getattr(contract, 'warehouse', None)
        context["devices"] = Device.objects.filter(zone__contract=contract)
        context["maintenance_cards"] = MaintenanceCard.objects.filter(device__zone__contract=contract)
        context["coordination_requests"] = CoordinationRequest.objects.filter(zone__contract=contract)
        context["tasks"] = Task.objects.filter(zone__contract=contract)

        category_data = []
        for item in context["items"]:
            device_count = Device.objects.filter(device_category=item.category, zone__contract=contract).count()
            percentage = (device_count / item.quantity * 100) if item.quantity else 0
            category_data.append({
                "category_label": item.category.name,
                "required": item.quantity,
                "available": device_count,
                "percentage": round(percentage, 1)
            })
        context["category_stats"] = category_data

        zone_stats = []
        for zone in context["zones"]:
            devices = zone.devices.all()
            zone_stats.append({
                'zone': zone,
                'installed': devices.filter(status='installed').count(),
                'available': devices.filter(status='available').count(),
                'damaged': devices.filter(status='damaged').count(),
                'total': devices.count(),
            })
        context["zone_stats"] = zone_stats

        tasks = context["tasks"]
        context["task_summary"] = {
            'total': tasks.count(),
            'completed': tasks.filter(status='completed').count(),
            'ongoing': tasks.filter(status='ongoing').count(),
            'not_started': tasks.filter(status='not_started').count(),
            'delayed': tasks.filter(status='delayed').count(),
        }

        maintenance = context["maintenance_cards"]
        context["maintenance_summary"] = {
            'total': maintenance.count(),
            'repaired': maintenance.exclude(repair_date__isnull=True).count(),
            'pending': maintenance.filter(repair_date__isnull=True).count(),
        }

        coordination = context["coordination_requests"]
        context["coordination_summary"] = {
            'total': coordination.count(),
            'last_date': coordination.order_by("-request_date").first().request_date if coordination.exists() else "—"
        }

        return context


class ContractFormView(CreateView, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contracts/form.html'
    success_url = reverse_lazy('contract_list')

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        if pk:
            return get_object_or_404(Contract, pk=pk)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.get_object()

        if self.request.POST:
            context['item_formset'] = ContractItemFormSet(self.request.POST, instance=contract, prefix='items')
            context['zone_formset'] = ZoneFormSet(self.request.POST, instance=contract, prefix='zones')
            context['warehouse_form'] = WarehouseForm(self.request.POST, instance=getattr(contract, 'warehouse', None), prefix='warehouse')
        else:
            context['item_formset'] = ContractItemFormSet(instance=contract, prefix='items')
            context['zone_formset'] = ZoneFormSet(instance=contract, prefix='zones')
            context['warehouse_form'] = WarehouseForm(instance=getattr(contract, 'warehouse', None), prefix='warehouse')

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        zone_formset = context['zone_formset']
        warehouse_form = context['warehouse_form']

        forms_valid = all([
            form.is_valid(),
            item_formset.is_valid(),
            zone_formset.is_valid(),
            warehouse_form.is_valid(),
        ])

        if forms_valid:
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()

            zone_formset.instance = self.object
            zone_formset.save()

            warehouse = warehouse_form.save(commit=False)
            warehouse.contract = self.object
            warehouse.save()

            messages.success(self.request, "Contract, items, zones, and warehouse saved successfully.")
            return HttpResponseRedirect(self.get_success_url())

        if not item_formset.is_valid():
            messages.error(self.request, "There are errors in the contract items:")
            for form in item_formset:
                for field, errors in form.errors.items():
                    messages.error(self.request, f"• {field}: {errors.as_text()}")

        if not zone_formset.is_valid():
            messages.error(self.request, "There are errors in the contract zones:")
            for form in zone_formset:
                for field, errors in form.errors.items():
                    messages.error(self.request, f"• {field}: {errors.as_text()}")

        if not warehouse_form.is_valid():
            messages.error(self.request, "There are errors in the warehouse form:")
            for field, errors in warehouse_form.errors.items():
                messages.error(self.request, f"• {field}: {errors.as_text()}")

        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "An error occurred while saving the contract.")
        return super().form_invalid(form)

from django.db.models import ProtectedError

def manage_device_categories(request):
    categories = DeviceCategory.objects.all().order_by('id')

    if request.method == "POST":
        if 'save' in request.POST:
            category_id = request.POST.get("category_id")
            if category_id:
                category = get_object_or_404(DeviceCategory, id=category_id)
                form = DeviceCategoryForm(request.POST, instance=category)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Category updated successfully.")
                    return redirect('manage_device_categories')
            else:
                form = DeviceCategoryForm(request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Category added successfully.")
                    return redirect('manage_device_categories')

        elif 'delete' in request.POST:
            category_id = request.POST.get("category_id")
            category = get_object_or_404(DeviceCategory, id=category_id)
            try:
                category.delete()
                messages.success(request, "Category deleted successfully.")
            except ProtectedError:
                messages.error(request, f"Cannot delete category '{category.name}' because it is used by other records.")
            return redirect('manage_device_categories')

    form = DeviceCategoryForm()
    return render(request, 'contracts/device_categories/manage.html', {
        'categories': categories,
        'form': form,
    })

class WarehouseListView(ListView):
    model = Warehouse
    template_name = 'contracts/warehouses/list.html'
    context_object_name = 'warehouses'


class WarehouseDetailView(DetailView):
    model = Warehouse
    template_name = 'contracts/warehouses/detail.html'
    context_object_name = 'warehouse'

    def get_queryset(self):
        return Warehouse.objects.select_related("contract").prefetch_related("devices")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if request.GET.get("export") == "true":
            format_ = request.GET.get("format")
            queryset = self.get_filtered_devices()
            if format_ == "excel":
                return self.export_to_excel(queryset)
            elif format_ == "pdf":
                return self.export_to_pdf(queryset)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        warehouse = self.object

        # فلترة
        devices = self.get_filtered_devices()
        context['devices'] = devices

        context['filter_status'] = self.request.GET.get('status')
        context['filter_zone'] = self.request.GET.get('zone')
        context['search_query'] = self.request.GET.get('q')
        context['zones'] = Zone.objects.filter(contract=warehouse.contract)

        context['total_devices'] = devices.count()
        context['category_counts'] = devices.values('device_category__name').annotate(total=Count('serial_number'))
        return context

    def get_filtered_devices(self):
        warehouse = self.object
        devices = warehouse.devices.all()

        filter_status = self.request.GET.get('status')
        if filter_status:
            devices = devices.filter(status=filter_status)

        zone_id = self.request.GET.get('zone')
        if zone_id == "warehouse":
            devices = devices.filter(current_location="warehouse")
        elif zone_id:
            devices = devices.filter(zone_id=zone_id)

        search_name = self.request.GET.get('q')
        if search_name:
            devices = devices.filter(name__icontains=search_name)

        return devices

    def export_to_excel(self, queryset):
        warehouse = self.object
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Devices"

        # Header
        sheet.merge_cells("A1:E1")
        sheet["A1"] = f"Warehouse: {warehouse.name} ({warehouse.location})"
        sheet["A1"].font = Font(bold=True)

        if warehouse.contract:
            sheet.merge_cells("A2:E2")
            sheet["A2"] = f"Linked Contract: {warehouse.contract.name} ({warehouse.contract.contract_number})"
            sheet["A2"].font = Font(bold=True)

        sheet.append([])

        stats = [
            ("Total Zones", warehouse.count_zones),
            ("Total Devices", warehouse.count_devices),
            ("In Warehouse", warehouse.count_in_warehouse),
            ("Installed", warehouse.count_installed),
            ("Damaged", warehouse.count_damaged),
        ]
        sheet.append(["Statistics", "Count"])
        for label, count in stats:
            sheet.append([label, count])

        sheet.append([])

        headers = [
            "Serial", "Name", "Category", "Status", "IP",
            "Transfer Date", "Installation Date", "Responsible", "Notes"
        ]
        sheet.append(headers)

        for device in queryset:
            row = [
                device.serial_number,
                device.name,
                device.device_category.name if device.device_category else "",
                dict(Device.DEVICE_STATUS_CHOICES).get(device.status, ""),
                device.ip_address,
                device.transfer_date.strftime("%Y-%m-%d") if device.transfer_date else "",
                device.installation_date.strftime("%Y-%m-%d") if device.installation_date else "",
                device.responsible_person,
                device.notes or ""
            ]
            sheet.append(row)

        for col in range(1, sheet.max_column + 1):
            sheet.column_dimensions[get_column_letter(col)].width = 20

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        filename = f"devices_{slugify(warehouse.name)}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    def export_to_pdf(self, queryset):
        warehouse = self.object
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)

        font_path = os.path.join(settings.BASE_DIR, "static", "contracts", "fonts", "Janna LT Bold", "Janna LT Bold.ttf")
        pdfmetrics.registerFont(TTFont("Janna", font_path))

        content = []

        # ✅ إضافة صورة SVG
        svg_path = os.path.join(settings.STATIC_ROOT, "contracts/img/logo-1.svg")

        drawing = svg2rlg(svg_path)
        drawing.scale(1, 1)  # التحكم بالحجم
        drawing.hAlign = "LEFT"

        # إعداد العنوان
        contract_info = f"تقرير أجهزة العقد  : {warehouse.contract.name} - {warehouse.contract.contract_number}"
        title_text = get_display(arabic_reshaper.reshape(contract_info))
        title_style = ParagraphStyle(name="Title", fontName="Janna", fontSize=20, alignment=1, spaceAfter=0)
        title_paragraph = Paragraph(title_text, title_style)

        # إنشاء جدول مكون من عمودين: [الصورة, العنوان]
        title_table = Table(
            data=[[drawing, title_paragraph]],
            colWidths=[80, 650],  # يمكنك تعديل العرض حسب حجم الصورة والعنوان
            hAlign='RIGHT'
        )
        title_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "RIGHT"),  # الصورة
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),  # العنوان
        ]))

        content.append(title_table)
        content.append(Spacer(1, 25))

        
        title_text = f""
        if any("\u0600" <= c <= "\u06FF" for c in title_text):
            title_text = get_display(arabic_reshaper.reshape(title_text))

        title = Paragraph(title_text, ParagraphStyle("title", fontName="Janna", fontSize=14, alignment=1))
        content.append(title)
        content.append(Spacer(1, 10))

        # إنشاء الفقرات
        stats = [
            f"عدد الأجهزة في المخزن: {warehouse.count_in_warehouse}",
            f"المخزن: {warehouse.name} - {warehouse.location}",
            f"إجمالي المناطق: {warehouse.count_zones}",
            f"إجمالي الأجهزة: {warehouse.count_devices}",
            f"عدد الأجهزة المركبة: {warehouse.count_installed}",
            f"عدد الأجهزة المعطلة: {warehouse.count_damaged}",
        ]
        
        # إعادة تشكيل كل عنصر بالعربية وإضافته في صف واحد
        reshaped_stats = [
            Paragraph(get_display(arabic_reshaper.reshape(s)), ParagraphStyle("stat_text", fontName="Janna", fontSize=11, alignment=2))
            for s in stats
        ]
        
        # تقسيمها إلى صفوف حسب عدد الأعمدة (مثلاً 3 أعمدة)
        row_size = 2
        stat_rows = [reshaped_stats[i:i+row_size] for i in range(0, len(reshaped_stats), row_size)]
        
        # إنشاء الجدول
        stats_table = Table(stat_rows, colWidths=[380] * row_size, hAlign='RIGHT')
        stats_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), "Janna"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        
        content.append(stats_table)
        content.append(Spacer(1, 20))

        
        headers = [
            "ملاحظات",
            "المنطقة",
            "تاريخ التركيب",
            "تاريخ النقل",
            "المسؤول",
            "IP",
            "الحالة",
            "الفئة",
            "الاسم",
            "الرقم التسلسلي"
        ]
        data = [[get_display(arabic_reshaper.reshape(h)) for h in headers]]

        for device in queryset:
            row = [
                device.notes or "",
                device.zone.name if device.zone else "المخزن",
                device.responsible_person or "",
                device.installation_date.strftime("%Y-%m-%d") if device.installation_date else "",
                device.transfer_date.strftime("%Y-%m-%d") if device.transfer_date else "",
                device.ip_address or "",
                dict(Device.DEVICE_STATUS_CHOICES).get(device.status, ""),
                device.device_category.name if device.device_category else "",
                device.name,
                device.serial_number
            ]
            row = [get_display(arabic_reshaper.reshape(str(col))) if any('\u0600' <= c <= '\u06FF' for c in str(col)) else str(col) for col in row]
            data.append(row)

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Janna"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ]))
        content.append(table)

        doc.build(content)
        filename = f"devices_{slugify(warehouse.name)}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return HttpResponse(buffer.getvalue(), content_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

# views.py
from django.views import View
# from django.core.exceptions import ObjectDoesNotExist


import pandas as pd

class DeviceImportView(View):
    template_name = "contracts/devices/import_devices.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        excel_file = request.FILES.get("file")
        if not excel_file:
            messages.error(request, "Please upload an Excel file.")
            return redirect("import_devices")

        try:
            df = pd.read_excel(excel_file, engine="openpyxl")

            for index, row in df.iterrows():
                # --- Safe extract strings ---
                category_name = str(row.get("device_category") or "").strip()
                warehouse_name = str(row.get("warehouse_name") or "").strip()
                zone_name = str(row.get("zone_name") or "").strip()

                if not category_name or not warehouse_name:
                    continue  # Skip incomplete rows

                # --- Device Category ---
                category, _ = DeviceCategory.objects.get_or_create(name=category_name)

                # --- Contract ---
                contract_name = f"AutoContract-{warehouse_name}"
                contract, _ = Contract.objects.get_or_create(
                    name=contract_name,
                    defaults={
                        "contract_number": f"CN-{warehouse_name[:5]}-{index}",
                        "start_date": timezone.now().date(),
                        "end_date": None,
                        "notes": "Auto-generated contract for import"
                    }
                )

                # --- Warehouse ---
                warehouse, _ = Warehouse.objects.get_or_create(
                    name=warehouse_name,
                    defaults={
                        "location": "Auto-Imported",
                        "contract": contract
                    }
                )

                # --- Zone ---
                zone = None
                if zone_name:
                    zone, _ = Zone.objects.get_or_create(
                        name=zone_name,
                        contract=contract,
                        defaults={"notes": "Auto-created via import"}
                    )

                # --- Contract Item ---
                ContractItem.objects.get_or_create(
                    contract=contract,
                    category=category,
                    defaults={"quantity": 1, "notes": "Auto-added on import"}
                )

                # --- Create/Update Device ---
                Device.objects.update_or_create(
                    serial_number=str(row.get("serial_number")).strip(),
                    defaults={
                        "name": str(row.get("name") or "").strip(),
                        "invoice_number": str(row.get("invoice_number") or "").strip(),
                        "device_category": category,
                        "warehouse": warehouse,
                        "zone": zone,
                        "status": str(row.get("status") or "").strip(),
                        "current_location": str(row.get("current_location") or "").strip(),
                        "ip_address": row.get("ip_address") or None,
                        "responsible_person": str(row.get("responsible_person") or "").strip(),
                        "transfer_date": row.get("transfer_date") if not pd.isna(row.get("transfer_date")) else None,
                        "installation_date": row.get("installation_date") if not pd.isna(row.get("installation_date")) else None,
                        "notes": str(row.get("notes") or "").strip(),
                    }
                )

            messages.success(request, "Devices imported successfully.")

        except Exception as e:
            messages.error(request, f"An error occurred during import: {str(e)}")

        return redirect("import_devices")


class DeviceCreateView(CreateView):
    model = Device
    form_class = DeviceForm
    template_name = 'contracts/devices/form.html'

    def dispatch(self, request, *args, **kwargs):
        self.warehouse = get_object_or_404(Warehouse, pk=self.kwargs['warehouse_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.warehouse = self.warehouse
        messages.success(self.request, f"Device '{form.instance.name}' has been successfully added.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouse_id'] = self.warehouse.pk
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['contract'] = self.warehouse.contract
        return kwargs

    def get_success_url(self):
        return reverse_lazy('warehouse_detail', kwargs={'pk': self.warehouse.pk})


class DeviceUpdateView(UpdateView):
    model = Device
    form_class = DeviceForm
    template_name = 'contracts/devices/form.html'
    pk_url_kwarg = 'pk'

    def form_valid(self, form):
        messages.success(self.request, f"Device '{form.instance.name}' has been successfully updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouse_id'] = self.object.warehouse.pk
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['contract'] = self.object.warehouse.contract
        return kwargs

    def get_success_url(self):
        return reverse_lazy('warehouse_detail', kwargs={'pk': self.object.warehouse.pk})


class DeviceDeleteView(DeleteView):
    model = Device
    template_name = 'contracts/devices/delete.html'
    pk_url_kwarg = 'pk'

    def get_success_url(self):
        return reverse_lazy('warehouse_detail', kwargs={'pk': self.object.warehouse.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouse_id'] = self.object.warehouse.pk
        return context


class DeviceDetailView(DetailView):
    model = Device
    template_name = 'contracts/devices/detail.html'
    context_object_name = 'device'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


@require_POST
@csrf_exempt
def update_device_status(request, pk):
    device = get_object_or_404(Device, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Device.DEVICE_STATUS_CHOICES):
        device.status = new_status
        device.save()
        return redirect('warehouse_detail', pk=device.warehouse.pk)
    return HttpResponseBadRequest("Invalid status")


class MaintenanceListView(ExportMixin, TemplateView):
    template_name = 'contracts/maintenance/list.html'

    def get_queryset(self):
        contracts = Contract.objects.all()
        last_contract = contracts.last()

        contract_id = self.request.GET.get('contract') or (last_contract.pk if last_contract else None)
        zone_id = self.request.GET.get('zone')
        category_id = self.request.GET.get('category')
        status = self.request.GET.get('status')

        queryset = MaintenanceCard.objects.filter(device__zone__contract_id=contract_id)

        if zone_id:
            if zone_id == "warehouse":
                queryset = queryset.filter(device__current_location="warehouse")
            else:
                queryset = queryset.filter(device__zone_id=zone_id)

        if category_id:
            queryset = queryset.filter(device__device_category_id=category_id)

        if status:
            queryset = queryset.filter(device__status=status)

        return queryset, contract_id, zone_id, category_id, status, contracts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        maintenance_cards, contract_id, zone_id, category_id, status, contracts = self.get_queryset()

        context.update({
            'contracts': contracts,
            'zones': Zone.objects.filter(contract_id=contract_id),
            'categories': DeviceCategory.objects.all(),
            'maintenance_cards': maintenance_cards,
            'filter_contract': str(contract_id) if contract_id else '',
            'filter_zone': zone_id,
            'filter_category': category_id,
            'filter_status': status,
        })
        return context

class MaintenanceListView(ExportMixin, TemplateView):
    template_name = 'contracts/maintenance/list.html'

    def get_queryset(self):
        contract_number = self.request.GET.get('contract')
        contract = None

        if contract_number:
            contract = Contract.objects.filter(contract_number=contract_number).first()
        else:
            contract = Contract.objects.last()

        if not contract:
            return MaintenanceCard.objects.none()

        queryset = MaintenanceCard.objects.filter(device__zone__contract=contract)

        zone_id = self.request.GET.get('zone')
        if zone_id == "warehouse":
            queryset = queryset.filter(device__current_location="warehouse")
        elif zone_id:
            queryset = queryset.filter(device__zone_id=zone_id)

        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(device__device_category_id=category_id)

        status = self.request.GET.get('status')
        if status and status.lower() != "none":
            queryset = queryset.filter(device__status=status)

        return queryset

    def get_filter_context(self):
        return {
            "filter_contract": self.request.GET.get('contract'),
            "filter_zone": self.request.GET.get('zone'),
            "filter_category": self.request.GET.get('category'),
            "filter_status": self.request.GET.get('status'),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_context = self.get_filter_context()

        contract = Contract.objects.filter(contract_number=filter_context["filter_contract"]).first()
        if not contract:
            contract = Contract.objects.last()

        context.update(filter_context)
        context.update({
            'contracts': Contract.objects.all(),
            'zones': Zone.objects.filter(contract=contract) if contract else Zone.objects.none(),
            'categories': DeviceCategory.objects.all(),
            'maintenance_cards': self.get_queryset(),
        })
        return context


class MaintenanceCreateView(CreateView):
    model = MaintenanceCard
    form_class = MaintenanceCardForm
    template_name = 'contracts/maintenance/form.html'

    def dispatch(self, request, *args, **kwargs):
        self.device = get_object_or_404(Device, serial_number=self.kwargs['device_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {'device': self.device}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['device'] = self.device
        return context

    def form_valid(self, form):
        form.instance.device = self.device
        messages.success(self.request, "Maintenance card created successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error creating the maintenance card. Please check the form.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('device_detail', kwargs={'pk': self.device.serial_number})


class MaintenanceUpdateView(UpdateView):
    model = MaintenanceCard
    form_class = MaintenanceCardForm
    template_name = 'contracts/maintenance/form.html'
    pk_url_kwarg = 'pk'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.device = self.object.device  # This line sets self.device properly
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['device'] = self.device  # For use in the template
        return context

    def form_valid(self, form):
        messages.success(self.request, "Maintenance card updated successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the maintenance card.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('device_detail', kwargs={'pk': self.device.serial_number})


class MaintenanceDeleteView(DeleteView):
    model = MaintenanceCard
    template_name = 'contracts/maintenance/delete.html'
    pk_url_kwarg = 'pk'

    def get_success_url(self):
        return reverse_lazy('maintenancecard_list', kwargs={'contract_id': self.kwargs['contract_id']})


class CoordinationListView(ExportMixin, ListView):
    model = CoordinationRequest
    template_name = 'contracts/coordination/list.html'
    context_object_name = 'coordination'
    paginate_by = 25  # يمكن تعديل العدد حسب الحاجة

    def get_queryset(self):
        queryset = CoordinationRequest.objects.all()
        contract_id = self.request.GET.get('contract')
        zone_id = self.request.GET.get('zone')

        # فلترة حسب العقد
        if contract_id:
            queryset = queryset.filter(zone__contract_id=contract_id)
        else:
            last_contract = Contract.objects.last()
            if last_contract:
                queryset = queryset.filter(zone__contract=last_contract)

        # فلترة حسب المنطقة
        if zone_id and zone_id.isdigit():
            queryset = queryset.filter(zone_id=int(zone_id))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract_id = self.request.GET.get('contract')
        zone_id = self.request.GET.get('zone')

        # تمرير العقود لجميعها
        context['contracts'] = Contract.objects.all()
        
        # تمرير المناطق حسب العقد المحدد
        if contract_id:
            context['zones'] = Zone.objects.filter(contract_id=contract_id)
        else:
            context['zones'] = Zone.objects.none()

        context['filter_contract'] = contract_id
        context['filter_zone'] = zone_id if zone_id and zone_id.isdigit() else ''

        return context


class CoordinationCreateView(CreateView):
    model = CoordinationRequest
    form_class = CoordinationRequestForm
    template_name = 'contracts/coordination/form.html'
    success_url = reverse_lazy('coordination_list')

    def form_valid(self, form):
        messages.success(self.request, "Coordination request created successfully.")
        return super().form_valid(form)


class CoordinationUpdateView(UpdateView):
    model = CoordinationRequest
    form_class = CoordinationRequestForm
    template_name = 'contracts/coordination/form.html'
    success_url = reverse_lazy('coordination_list')

    def form_valid(self, form):
        messages.success(self.request, "Coordination request updated successfully.")
        return super().form_valid(form)


class CoordinationDeleteView(DeleteView):
    model = CoordinationRequest
    template_name = 'contracts/coordination/delete.html'
    success_url = reverse_lazy('coordination_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Coordination request deleted successfully.")
        return super().delete(request, *args, **kwargs)


class TaskListView(ListView):
    model = Task
    template_name = 'contracts/tasks/list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('zone', 'zone__contract')

        contract_id = self.request.GET.get('contract')
        zone_id = self.request.GET.get('zone')
        status = self.request.GET.get('status')

        if contract_id:
            queryset = queryset.filter(zone__contract_id=contract_id)
        else:
            last_contract = Contract.objects.last()
            if last_contract:
                queryset = queryset.filter(zone__contract=last_contract)

        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('deadline')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract_id = self.request.GET.get('contract')

        context['contracts'] = Contract.objects.all()

        # تحديد العقد الحالي أو الأخير
        if contract_id:
            context['filter_contract'] = str(contract_id)
            context['zones'] = Zone.objects.filter(contract_id=contract_id)
        else:
            last_contract = Contract.objects.last()
            context['filter_contract'] = last_contract.pk if last_contract else None
            context['zones'] = Zone.objects.filter(contract=last_contract) if last_contract else []

        context['selected_zone'] = self.request.GET.get('zone')
        context['selected_status'] = self.request.GET.get('status')

        return context


def task_change_status(request, pk, status):
    task = get_object_or_404(Task, pk=pk)
    valid_statuses = [s[0] for s in Task.TASK_STATUS_CHOICES]

    if status in valid_statuses:
        task.status = status
        if status == 'completed':
            task.actual_delivery_date = timezone.now().date()
        else:
            task.actual_delivery_date = None 
        task.save()
        messages.success(request, f"Task status updated to {task.get_status_display()}.")
    else:
        messages.error(request, "Invalid status selected.")

    return redirect('task_list')


class TaskCreateView(CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'contracts/tasks/form.html'

    def form_valid(self, form):
        messages.success(self.request, f"Task '{form.instance.name}' has been created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('task_list')


class TaskUpdateView(UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'contracts/tasks/form.html'

    def form_valid(self, form):
        messages.success(self.request, f"Task '{form.instance.name}' has been updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('task_list')


class TaskDeleteView(DeleteView):
    model = Task
    template_name = 'contracts/tasks/delete.html'
    success_url = reverse_lazy('task_list')

    def delete(self, request, *args, **kwargs):
        task = self.get_object()
        messages.success(request, f"Task '{task.name}' has been deleted successfully.")
        return super().delete(request, *args, **kwargs)
