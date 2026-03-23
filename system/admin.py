from django.contrib import admin
from .models import *

# ------------------------
# Inline ratings in inspections
# ------------------------
@admin.register(ConditionRating)
class ConditionRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'inspection', 'hardware_condition', 'software_condition')
# ------------------------
# Inspections admin
# ------------------------
@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'unit', 'technician', 'period', 'date_checked', 'status')
    list_filter = ('technician', 'period', 'status')
    search_fields = ('unit__asset_tag', 'technician__name')
# ------------------------
# Inline inspections inside units
# ------------------------
class InspectionInline(admin.TabularInline):
    model = Inspection
    extra = 0
    readonly_fields = ('technician', 'period', 'date_checked', 'status')
    show_change_link = True  # allow admin to jump to full inspection

@admin.register(ComputerUnit)
class ComputerUnitAdmin(admin.ModelAdmin):
    list_display = ('asset_tag', 'room', 'status')
    list_filter = ('room', 'status')
    search_fields = ('asset_tag',)
    inlines = [InspectionInline]

# ------------------------
# Other models
# ------------------------
@admin.register(LabRoom)
class LabRoomAdmin(admin.ModelAdmin):
    list_display = ('room_name', 'location', 'capacity', 'status')
    search_fields = ('room_name', 'location')

@admin.register(Hardware)
class HardwareAdmin(admin.ModelAdmin):
    list_display = ('unit', 'cpu', 'ram', 'gpu', 'storage', 'condition')
    search_fields = ('unit__asset_tag',)

@admin.register(Software)
class SoftwareAdmin(admin.ModelAdmin):
    list_display = ('unit', 'os')
    search_fields = ('unit__asset_tag', 'os')

@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'role', 'status')
    list_filter = ('role', 'status')
    search_fields = ('name', 'email')

@admin.register(AssessmentPeriod)
class AssessmentPeriodAdmin(admin.ModelAdmin):
    list_display = ('semester', 'school_year', 'date_start', 'date_end')
    search_fields = ('semester', 'school_year')

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('device_type', 'brand', 'unit', 'lab', 'condition')
    search_fields = ('device_type', 'brand', 'unit__asset_tag', 'lab__room_name')