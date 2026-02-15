from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse, path
from django.shortcuts import render
from django import forms
from .models import PaymentMethod, MonthlyInvoice


class MonthInput(forms.DateInput):
    input_type = 'month'
    
    def value_from_datadict(self, data, files, name):
        # Handle the month input format (YYYY-MM)
        if name in data and data[name]:
            try:
                from datetime import datetime
                # Parse YYYY-MM format and set to first day of month
                year_month = data[name]
                if len(year_month) == 7:  # YYYY-MM format
                    year, month = year_month.split('-')
                    return datetime(int(year), int(month), 1).date()
            except (ValueError, TypeError):
                pass
        return super().value_from_datadict(data, files, name)

class InvoiceGenerationForm(forms.Form):
    month = forms.DateField(
        label='Select Month',
        widget=MonthInput(),
        help_text='Choose the month for which to generate invoices'
    )
    regenerate = forms.BooleanField(
        label='Regenerate existing invoices',
        required=False,
        help_text='Check this to overwrite existing invoices for the selected month'
    )

    def clean_month(self):
        month = self.cleaned_data.get('month')
        if month:
            # Ensure it's the first day of the month
            return month.replace(day=1)
        return month


@admin.register(MonthlyInvoice)
class MonthlyInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'invoice_number', 'owner', 'month_display', 'total_reservations', 
        'subtotal', 'total_amount', 'status', 'published_at_display'
    ]
    list_filter = ['status', 'month', ('published_at', admin.DateFieldListFilter), ('paid_date', admin.DateFieldListFilter)]
    search_fields = ['owner__username', 'owner__email', 'month_display', 'invoice_number']
    readonly_fields = ['id', 'invoice_number', 'issue_date', 'published_at', 'paid_date', 'total_reservations', 'subtotal', 'vat_amount', 'total_amount']
    actions = ['publish_invoices', 'mark_as_paid', 'create_invoices']
    change_list_template = 'admin/payments/monthlyinvoice_change_list.html'
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'owner', 'month', 'status', 'period_start', 'period_end', 'due_date')
        }),
        ('Financial Details', {
            'fields': ('total_reservations', 'subtotal', 'vat_amount', 'total_amount'),
            'classes': ('collapse',),
        }),
        ('Dates', {
            'fields': ('issue_date', 'published_at', 'published_by', 'paid_date'),
            'classes': ('collapse',),
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('generate-invoices/', self.admin_site.admin_view(self.generate_invoices_view), name='payments_monthlyinvoice_generate_invoices'),
        ]
        return custom_urls + urls

    def generate_invoices_view(self, request):
        """Custom view to handle invoice generation"""
        if request.method == 'POST':
            form = InvoiceGenerationForm(request.POST)
            if form.is_valid():
                month = form.cleaned_data['month']
                regenerate = form.cleaned_data['regenerate']
                
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                # Get all owners
                owners = User.objects.filter(role='owner')
                
                # Calculate period_start and period_end
                from calendar import monthrange
                last_day = monthrange(month.year, month.month)[1]
                period_start = month
                period_end = month.replace(day=last_day)
                
                count = 0
                skipped = 0
                
                for owner in owners:
                    # Check if invoice already exists
                    existing_invoice = MonthlyInvoice.objects.filter(owner=owner, month=month).first()
                    
                    if existing_invoice and not regenerate:
                        skipped += 1
                        continue
                    
                    if existing_invoice and regenerate:
                        # Delete existing invoice
                        existing_invoice.delete()
                    
                    # Generate invoice number
                    invoice_number = self._generate_invoice_number(month, owner)
                    
                    # Create new invoice
                    invoice = MonthlyInvoice.objects.create(
                        owner=owner,
                        invoice_number=invoice_number,
                        month=month,
                        period_start=period_start,
                        period_end=period_end,
                        status='draft',
                        due_date=period_end  # Will be updated when published
                    )
                    # Calculate totals
                    invoice.calculate_totals()
                    invoice.save()
                    count += 1
                
                action = 'regenerated' if regenerate else 'created'
                message = f'Successfully {action} {count} invoice(s) for {month.strftime("%B %Y")}.'
                if skipped > 0:
                    message += f' {skipped} existing invoice(s) were skipped.'
                
                self.message_user(request, message, messages.SUCCESS)
                return HttpResponseRedirect(reverse('admin:payments_monthlyinvoice_changelist'))
        else:
            form = InvoiceGenerationForm()
            # Set default to current month
            from datetime import date
            form.fields['month'].initial = date.today().replace(day=1)
        
        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'opts': self.model._meta,
            'title': 'Generate Monthly Invoices',
            'has_change_permission': self.has_change_permission(request),
        }
        return render(request, 'admin/payments/generate_invoices.html', context)
    
    def _generate_invoice_number(self, month, owner):
        """Generate a unique invoice number"""
        import uuid
        from datetime import datetime
        # Format: INV-YYYY-MM-OWNERID-UUID
        short_uuid = str(uuid.uuid4())[:8]
        return f"INV-{month.year}-{month.month:02d}-{owner.id}-{short_uuid}"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner')
    
    def published_at_display(self, obj):
        """Display published_at date in a readable format"""
        if obj.published_at:
            return obj.published_at.strftime('%Y-%m-%d %H:%M')
        return 'Not published'
    published_at_display.short_description = 'Published At'
    published_at_display.admin_order_field = 'published_at'
    
    def paid_date_display(self, obj):
        """Display paid_date in a readable format"""
        if obj.paid_date:
            return obj.paid_date.strftime('%Y-%m-%d')
        return 'Not paid'
    paid_date_display.short_description = 'Paid Date'
    paid_date_display.admin_order_field = 'paid_date'
    
    def create_invoices(self, request, queryset):
        """Create invoices for all owners for the selected month"""
        from django.contrib.auth import get_user_model
        import uuid
        User = get_user_model()
        
        # Get all owners
        owners = User.objects.filter(role='owner')
        
        # Get selected month from queryset or use current month
        if queryset.exists():
            month = queryset.first().month
        else:
            from datetime import date
            month = date.today().replace(day=1)
        
        # Calculate period_start and period_end
        from calendar import monthrange
        last_day = monthrange(month.year, month.month)[1]
        period_start = month
        period_end = month.replace(day=last_day)
        
        count = 0
        for owner in owners:
            # Check if invoice already exists
            if MonthlyInvoice.objects.filter(owner=owner, month=month).exists():
                continue
            
            # Generate invoice number
            short_uuid = str(uuid.uuid4())[:8]
            invoice_number = f"INV-{month.year}-{month.month:02d}-{owner.id}-{short_uuid}"
            
            # Create invoice
            invoice = MonthlyInvoice.objects.create(
                owner=owner,
                invoice_number=invoice_number,
                month=month,
                period_start=period_start,
                period_end=period_end,
                status='draft',
                due_date=period_end  # Will be updated when published
            )
            # Calculate totals
            invoice.calculate_totals()
            invoice.save()
            count += 1
        
        self.message_user(
            request, 
            f'Successfully created {count} invoice(s) for {month.strftime("%B %Y")}.', 
            messages.SUCCESS
        )
    create_invoices.short_description = 'Create invoices for selected month'
    
    def publish_invoices(self, request, queryset):
        """Publish selected invoices"""
        from datetime import timedelta
        count = 0
        for invoice in queryset.filter(status='draft'):
            # Recalculate totals before publishing
            invoice.calculate_totals()
            invoice.status = 'published'
            invoice.published_at = timezone.now()
            invoice.published_by = request.user  # Set published_by to current user
            # Set due date to 15 days after published date
            invoice.due_date = (invoice.published_at + timedelta(days=15)).date()
            invoice.save()
            count += 1
        
        self.message_user(
            request, 
            f'Successfully published {count} invoice(s). Due dates set to 15 days after publication.', 
            messages.SUCCESS
        )
    publish_invoices.short_description = 'Publish selected invoices'
    
    def mark_as_paid(self, request, queryset):
        """Mark selected invoices as paid"""
        count = queryset.filter(status='published').update(
            status='paid', 
            paid_date=timezone.now()
        )
        self.message_user(
            request, 
            f'Successfully marked {count} invoice(s) as paid.', 
            messages.SUCCESS
        )
    mark_as_paid.short_description = 'Mark selected invoices as paid'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'owner', 'payment_type', 'is_active', 'is_verified',
        'created_at', 'updated_at'
    ]
    list_filter = ['payment_type', 'is_active', 'is_verified', 'created_at', 'updated_at']
    search_fields = ['owner__username', 'owner__email', 'account_name', 'bank_name']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'payment_type', 'is_active', 'is_verified')
        }),
        ('Bank Transfer Details', {
            'fields': ('account_name', 'account_number', 'bank_name', 'routing_number'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner')

    def owner_username(self, obj):
        return obj.owner.username
    owner_username.short_description = 'Owner Username'

    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner Email'
