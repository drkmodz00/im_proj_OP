from django.utils import timezone
from datetime import date
from django.db import models
from django.forms import ValidationError
from django.contrib.auth.models import User

class LabRoom(models.Model):
    room_name = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    capacity = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=[('Operational', 'Operational'), ('Maintenance', 'Maintenance')],
        default='Operational'
    )

    def __str__(self):
        return self.room_name


class ComputerUnit(models.Model):
    room = models.ForeignKey(LabRoom, on_delete=models.CASCADE)
    asset_tag = models.CharField(max_length=50)
    STATUS_CHOICES = {
        'Working': 'Working',
        'Defective': 'Defective',
        'Maintenance': 'Maintenance'
    }
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    def __str__(self):
        return self.asset_tag


class Hardware(models.Model):
    unit = models.ForeignKey(ComputerUnit, on_delete=models.CASCADE)
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    cpu = models.CharField(max_length=50)
    ram = models.CharField(max_length=50)
    storage = models.CharField(max_length=50)
    gpu = models.CharField(max_length=50)
    network_adapter = models.CharField(max_length=100, blank=True)

    purchase_date = models.DateField(null=True, blank=True)
    warranty_status = models.CharField(max_length=50, blank=True)

    CONDITION_CHOICES = [
        ('Good', 'Good'),
        ('Fair', 'Fair'),
        ('Poor', 'Poor'),
    ]
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='Good')

    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.unit} Hardware"


class Software(models.Model):
    unit = models.ForeignKey(ComputerUnit, on_delete=models.CASCADE)
    os = models.CharField(max_length=50)
    installed_apps = models.TextField()

    def __str__(self):
        return f"{self.unit} Software"


class Technician(models.Model):
    ROLE_CHOICES = [('Admin','Admin'),('Technician','Technician')]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.CASCADE,)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Technician')

    name = models.CharField(max_length=100)
    email = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    specialty = models.CharField(max_length=100, blank=True)

    def __str__(self):
        try:
            return self.user.get_full_name() or self.user.username
        except:
            return f"Technician #{self.id} (No User)"    
        
class AssessmentPeriod(models.Model):
    semester = models.CharField(max_length=20)
    school_year = models.CharField(max_length=20)
    date_start = models.DateField()
    date_end = models.DateField()

    def __str__(self):
        return f"{self.semester} {self.school_year}"


class Inspection(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    ]

    unit = models.ForeignKey(ComputerUnit, on_delete=models.CASCADE, related_name='inspections')
    technician = models.ForeignKey(Technician, on_delete=models.CASCADE)
    period = models.ForeignKey(AssessmentPeriod, on_delete=models.CASCADE)
    date_checked = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    created_at = models.DateTimeField(default=timezone.now)    
    def __str__(self):
        return f"{self.unit.asset_tag} - {self.technician.name} ({self.period})"

class ConditionRating(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='rating')
    hardware_condition = models.CharField(max_length=50)
    software_condition = models.CharField(max_length=50)
    remarks = models.TextField()

    def __str__(self):
        return f"Rating {self.id}"

class Equipment(models.Model):
    # Temporarily allow null
    lab = models.ForeignKey(LabRoom, on_delete=models.CASCADE, null=True)
    unit = models.ForeignKey(ComputerUnit, on_delete=models.CASCADE)
    device_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    serial_number = models.CharField(max_length=100)
    condition = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)

    def clean(self):
        if self.unit.room != self.lab:
            raise ValidationError("Unit must belong to the same lab as the equipment.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Equipment {self.id} - {self.device_type} ({self.lab.room_name if self.lab else 'No Lab'})"