from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, ParkingZone, VehicleType, Tariff, ParkingTicket, ActivityLog
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'badge_id', 'role', 'first_name', 'last_name', 'phone', 'assigned_zone', 'is_active')
    list_filter = ('role', 'is_active', 'assigned_zone')
    search_fields = ('username', 'badge_id', 'first_name', 'last_name', 'phone')
    fieldsets = UserAdmin.fieldsets + (
        ('Informations Professionnelles Parking', {
            'fields': ('role', 'badge_id', 'phone', 'assigned_zone')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations Professionnelles Parking', {
            'fields': ('role', 'badge_id', 'phone', 'assigned_zone')
        }),
    )


@admin.register(ParkingZone)
class ParkingZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'total_spots', 'hourly_rate_default', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'description')


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'default_hourly_rate', 'default_daily_rate', 'icon_class', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('vehicle_type', 'zone', 'tariff_type', 'amount_bif', 'grace_period_minutes', 'is_active')
    list_filter = ('tariff_type', 'is_active', 'vehicle_type', 'zone')
    search_fields = ('vehicle_type__name', 'zone__name')


@admin.register(ParkingTicket)
class ParkingTicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number', 'plate_number', 'vehicle_type', 'zone',
        'entry_time', 'exit_time', 'status', 'amount_due', 'amount_paid', 'is_active'
    )
    list_filter = ('status', 'zone', 'vehicle_type', 'payment_method', 'is_active', 'entry_time')
    search_fields = ('ticket_number', 'plate_number')
    readonly_fields = ('ticket_number', 'entry_time')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'target_model', 'target_repr', 'ip_address')
    list_filter = ('action', 'target_model', 'timestamp')
    search_fields = ('target_repr', 'details', 'user__username', 'ip_address')
    readonly_fields = ('timestamp', 'user', 'action', 'target_model', 'target_id', 'target_repr', 'details', 'ip_address')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
