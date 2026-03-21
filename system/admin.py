from django.contrib import admin
from .models import *

admin.site.register(LabRoom)
admin.site.register(ComputerUnit)
admin.site.register(Hardware)
admin.site.register(Software)
admin.site.register(Technician)
admin.site.register(AssessmentPeriod)
admin.site.register(Inspection)
admin.site.register(ConditionRating)
admin.site.register(Equipment)