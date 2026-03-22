from urllib import request
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from datetime import date
from django.db.models import Prefetch, IntegerField, Q
from django.db.models.functions import Cast, Substr
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            try:
                tech = Technician.objects.get(user=user)
                if tech.role == "Admin":
                    return redirect("dashboard")
                else:
                    return redirect("tech_dashboard")
            except Technician.DoesNotExist:
                messages.error(request,"User has no assigned role")
                return redirect("login")
        else:
            messages.error(request,"Invalid username or password")
            return redirect("login")

    return render(request,"login.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        role = request.POST.get("role")  # Admin or Technician
        specialty = request.POST.get("specialty", "")

        # Validate passwords match
        if password != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        # Create User
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_superuser=True if role=="Admin" else False,
            is_staff=True if role=="Admin" else False
        )

        # Create Technician profile
        Technician.objects.create(
            user=user,
            role=role,
            specialty=specialty,
            status='Active'
        )

        messages.success(request, f"{role} account created successfully!")
        login(request, user)

        # Redirect based on role
        if role=="Admin":
            return redirect("dashboard")
        else:
            return redirect("tech_dashboard")

    return render(request, "register.html")

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard(request):
    total_rooms = LabRoom.objects.count()   
    total_units = ComputerUnit.objects.count()
    total_inspections = Inspection.objects.count()

    rooms_qs = LabRoom.objects.all().order_by('room_name')
    paginator = Paginator(rooms_qs, 10)
    page_number = request.GET.get('page', 1)
    rooms = paginator.get_page(page_number)

    return render(request, 'dashboard.html', {
        'total_rooms': total_rooms,
        'total_units': total_units,
        'total_inspections': total_inspections,
        'rooms': rooms,
    })

def room_detail(request, room_id):
    # Fetch the room
    room = get_object_or_404(LabRoom, pk=room_id)
    
    # Fetch units in this room
    units_list = ComputerUnit.objects.filter(room=room).annotate(
        station_num=Cast(Substr('asset_tag', 45), IntegerField())
    ).order_by('station_num')
    
    # Pagination (10 units per page)
    paginator = Paginator(units_list, 10)
    page_number = request.GET.get('page')
    units = paginator.get_page(page_number)

    # Summary counts
    total_units = units_list.count()
    total_working = units_list.filter(status='Working').count()
    total_defective = units_list.filter(status='Defective').count()
    total_maintenance = units_list.filter(status='Maintenance').count()

    context = {
        'room': room,
        'units': units,
        'total_units': total_units,
        'total_working': total_working,
        'total_defective': total_defective,
        'total_maintenance': total_maintenance,
    }

    return render(request, 'room_detail.html', context)# ---------------------------

def laboratory(request):
    rooms_qs = LabRoom.objects.all().order_by('room_name')
    paginator = Paginator(rooms_qs, 10)
    page_number = request.GET.get('page', 1)
    rooms = paginator.get_page(page_number)
    return render(request, 'laboratory.html', {'rooms': rooms})

def report(request):
    school_year = request.GET.get('school_year')

    # Base rooms query
    rooms = LabRoom.objects.all().order_by('room_name')

    if school_year:
        rooms = rooms.filter(
            computerunit__inspection__period__school_year=school_year
        ).distinct()

    # Prefetch inspections for units
    inspections_prefetch = Prefetch(
        'inspection',
        queryset=Inspection.objects.select_related('technician', 'period').prefetch_related('rating')
    )

    rooms = rooms.prefetch_related(
        Prefetch('computerunit_set', queryset=ComputerUnit.objects.prefetch_related(inspections_prefetch))
    )

    context = {
        'rooms': rooms,
        'school_year': school_year,
    }
    return render(request, 'report.html', context)

def add_lab(request):
    if request.method == "POST":
        room_name = request.POST.get("room_name")
        location = request.POST.get("location")
        capacity = request.POST.get("capacity")

        LabRoom.objects.create(
            room_name=room_name,
            location=location,
            capacity=capacity
        )

    return redirect("dashboard")

def delete_lab(request, room_id):
    room = get_object_or_404(LabRoom, id=room_id)
    room.delete()
    return redirect("laboratory")

def add_unit(request):
    if request.method == "POST":
        asset_tag = request.POST.get("asset_tag")
        room_id = request.POST.get("room_id")
        status = request.POST.get("status") or "Working"

        cpu = request.POST.get("cpu")
        ram = request.POST.get("ram")
        gpu = request.POST.get("gpu")
        storage = request.POST.get("storage")

        os = request.POST.get("os")
        installed_apps = request.POST.get("installed_apps")

        room = get_object_or_404(LabRoom, id=room_id)

        # 1. Create unit
        unit = ComputerUnit.objects.create(
            asset_tag=asset_tag,
            room=room,
            status=status
        )

        # 2. Create hardware and software safely
        Hardware.objects.get_or_create(unit=unit, defaults={
            'cpu': cpu or '-', 'ram': ram or '-', 'gpu': gpu or '-', 'storage': storage or '-'
        })
        Software.objects.get_or_create(unit=unit, defaults={
            'os': os or '-', 'installed_apps': installed_apps or '-'
        })

    return redirect("room", room_id=room.id)

def delete_unit(request, unit_id):
    unit = get_object_or_404(ComputerUnit, id=unit_id)
    room_id = unit.room.id
    unit.delete()
    return redirect("room", room_id=room_id)

def view_unit(request, unit_id):
    unit = get_object_or_404(ComputerUnit, id=unit_id)

    # Safe access (no crash if missing)
    hardware = getattr(unit, 'hardware', None)
    software = getattr(unit, 'software', None)
    all_rooms = LabRoom.objects.all()

    # ------------------------
    # HANDLE POST ACTIONS
    # ------------------------
    if request.method == "POST":

        # ✅ UPDATE UNIT
        if "update" in request.POST:
            unit.asset_tag = request.POST.get("asset_tag", unit.asset_tag)
            unit.status = request.POST.get("status", unit.status)

            # Change room if provided
            room_id = request.POST.get("room_id")
            if room_id:
                unit.room = get_object_or_404(LabRoom, id=room_id)

            unit.save()

            # Update hardware (create if missing)
            hardware, _ = Hardware.objects.get_or_create(unit=unit)
            hardware.cpu = request.POST.get("cpu", hardware.cpu)
            hardware.ram = request.POST.get("ram", hardware.ram)
            hardware.gpu = request.POST.get("gpu", hardware.gpu)
            hardware.storage = request.POST.get("storage", hardware.storage)
            hardware.save()

            # Update software (create if missing)
            software, _ = Software.objects.get_or_create(unit=unit)
            software.os = request.POST.get("os", software.os)
            software.installed_apps = request.POST.get("installed_apps", software.installed_apps)
            software.save()

            messages.success(request, f"{unit.asset_tag} updated successfully.")
            return redirect("room", room_id=unit.room.id)

        # ✅ DELETE UNIT
        elif "delete" in request.POST:
            room_id = unit.room.id
            unit.delete()
            messages.success(request, "Unit deleted successfully.")
            return redirect("room", room_id=room_id)

    # ------------------------
    # FETCH INSPECTIONS (OPTIMIZED)
    # ------------------------
    inspections = (
        Inspection.objects
        .filter(unit=unit)
        .select_related('technician', 'period')
        .prefetch_related('rating')
        .order_by('-date_checked')
    )
    technicians_preview = Technician.objects.filter(status='Active').order_by('name')[:5]
    # Latest inspection (for UI highlight)
    latest_inspection = inspections.first()
    latest_rating = (
        latest_inspection.rating.first()
        if latest_inspection else None
    )

    context = {
        "unit": unit,
        "hardware": hardware,
        "software": software,
        "rooms": all_rooms,
        "technicians_preview": technicians_preview,

        # Inspection data
        "inspections": inspections,
        "latest_inspection": latest_inspection,
        "latest_rating": latest_rating,
    }

    return render(request, "view_unit.html", context)

def inspection_form(request):
    rooms = LabRoom.objects.all().order_by('room_name')
    selected_lab_id = request.GET.get('lab')
    periods = AssessmentPeriod.objects.all().order_by('-date_start')
    
    units = []
    equipments = []

    if selected_lab_id:
        units = ComputerUnit.objects.filter(room_id=selected_lab_id)
        equipments = Equipment.objects.filter(unit__room_id=selected_lab_id).select_related('unit')

    if request.method == "POST":
        room_id = request.POST.get("room")
        period_id = request.POST.get("period_id")
        equipment_id = request.POST.get("equipment_id")
        condition = request.POST.get("condition")
        remarks = request.POST.get("remarks", "")

        room = get_object_or_404(LabRoom, id=room_id)
        period = get_object_or_404(AssessmentPeriod, id=period_id)
        equipment = get_object_or_404(Equipment, id=equipment_id)
        unit = equipment.unit

        # Update unit status
        unit.status = condition
        unit.save()

        # Ensure Hardware and Software exist
        Hardware.objects.get_or_create(unit=unit, defaults={'cpu':'-', 'ram':'-', 'gpu':'-', 'storage':'-'})
        Software.objects.get_or_create(unit=unit, defaults={'os':'-', 'installed_apps':'-'})

        # Use a default technician
        technician = Technician.objects.get(email=request.user.email)
        # Create or get inspection
        inspection, _ = Inspection.objects.get_or_create(
            unit=unit,
            period=period,
            defaults={'technician': technician, 'date_checked': date.today()}
        )

        # Update or create condition rating
        ConditionRating.objects.update_or_create(
            inspection=inspection,
            defaults={
                'hardware_condition': condition,
                'software_condition': condition,
                'remarks': remarks
            }
        )

        messages.success(request, f"Inspection for {unit.asset_tag} recorded successfully.")
        return redirect(f"{reverse('report')}?school_year={period.school_year}")

    return render(request, "technician/form.html", {
        "rooms": rooms,
        "units": units,
        "equipments": equipments,
        "periods": periods,
        "selected_lab_id": int(selected_lab_id) if selected_lab_id else None,
    })

def view_inspection_details(request, room_id):
    school_year = request.GET.get('school_year')
    room = get_object_or_404(LabRoom, id=room_id)

    inspections = Inspection.objects.filter(
        unit__room=room,
        period__school_year=school_year
    ).select_related('unit', 'technician', 'period').prefetch_related('conditionrating_set')

    context = {
        'room': room,
        'inspections': inspections,
        'school_year': school_year,
    }
    return render(request, 'inspection_details.html', context)

def edit_inspection(request, inspection_id):
    inspection = get_object_or_404(Inspection, id=inspection_id)
    rating = inspection.conditionrating_set.first()
    units = ComputerUnit.objects.all()
    periods = AssessmentPeriod.objects.all()

    if request.method == "POST":
        inspection.unit_id = request.POST.get("unit_id")
        inspection.period_id = request.POST.get("period_id")
        inspection.date_checked = request.POST.get("date_checked")
        inspection.save()

        rating.hardware_condition = request.POST.get("condition")
        rating.remarks = request.POST.get("remarks")
        rating.save()

        messages.success(request, "Inspection updated successfully.")
        return redirect("report")

    return render(request, "edit_inspection.html", {
        "inspection": inspection,
        "rating": rating,
        "units": units,
        "periods": periods
    })

def delete_inspections_by_room(request, room_id):
    if request.method == "POST":
        school_year = request.GET.get('school_year')
        room = get_object_or_404(LabRoom, id=room_id)

        inspections = Inspection.objects.filter(unit__room=room)
        if school_year:
            inspections = inspections.filter(period__school_year=school_year)

        count = inspections.count()
        inspections.delete()

        messages.success(request, f"Deleted {count} inspections for {room.room_name} ({school_year}).")
    return redirect('report')

def technician_list(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    technicians_qs = Technician.objects.all()

    if query:
        technicians_qs = technicians_qs.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(specialty__icontains=query)
        )
    if status_filter.lower() == 'active':
        technicians_qs = technicians_qs.filter(status='Active')
    elif status_filter.lower() == 'inactive':
        technicians_qs = technicians_qs.filter(status='Inactive')

    paginator = Paginator(technicians_qs.order_by('name'), 10)
    page_number = request.GET.get('page')
    technicians = paginator.get_page(page_number)

    # Add initials for avatar circles (e.g., "JD" for "Juan Dela Cruz")
    for tech in technicians:
        names = tech.name.split()
        initials = "".join([n[0] for n in names[:2]]).upper()
        tech.initials = initials

    context = {
        'technicians': technicians,
        'total_technicians': technicians_qs.filter(status='Active').count(),
    }
    return render(request, 'technicians.html', context)

def add_technician(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        status = request.POST.get("status") or "Active"

        Technician.objects.create(
            name=name,
            email=email,
            status=status,
        )
        messages.success(request, f"Technician {name} added successfully.")
    return redirect("technicians")

def edit_technician(request, technician_id):
    technician = get_object_or_404(Technician, id=technician_id)

    if request.method == "POST":
        technician.name = request.POST.get("name", technician.name)
        technician.email = request.POST.get("email", technician.email)
        technician.status = request.POST.get("status", technician.status)
        technician.save()

        messages.success(request, f"Technician {technician.name} updated successfully.")
        return redirect("technicians")

    return render(request, "edit_technician", {"technician": technician})

def delete_technician(request, technician_id):
    technician = get_object_or_404(Technician, id=technician_id)
    technician.delete()
    messages.success(request, f"Technician {technician.name} deleted successfully.")
    return redirect("technicians")

def technician_profile(request):
    technician = Technician.objects.get(email=request.user.email)
    name = technician.name
    email = technician.email
    status = technician.status

    context = {
        'technician': technician,
        'name': name,
        'email': email,
        'status': status
    }
    return render(request, 'technician_profile.html', context)

# TECHNICIAN
@login_required
def tech_dashboard(request):
    technician = Technician.objects.get(email=request.user.email)

    assigned_rooms = LabRoom.objects.filter(
        computerunit__inspection__technician=technician
    ).distinct()

    total_labs = assigned_rooms.count()

    total_inspections = Inspection.objects.filter(technician=technician)

    pending_inspections = total_inspections.filter(status='Pending').count()
    completed_inspections = total_inspections.filter(status='Completed').count()

    context = {
        "assigned_rooms": assigned_rooms[:5],
        "total_labs": total_labs,
        "pending_inspections": pending_inspections,
        "completed_inspections": completed_inspections,
    }

    return render(request, 'technician/dashboard.html', context)

def assigned_laboratories(request):
    technician = Technician.objects.get_or_create(name="Default Tech")
    # technician = Technician.objects.get(email=request.user.email)
    assigned_rooms = LabRoom.object.filter(
        computerunit_inspection__technician=technician
    ).distinct()

    return render(request, 'technician/assigned_laboratories.html', {
            'assigned_rooms': assigned_rooms
        })

def unit_inspections(request, room_id):
    technician = Technician.objects.get(email=request.user.email)
    room = get_object_or_404(LabRoom, id=room_id)
    units = ComputerUnit.objects.filter(room=room)

    inspections = Inspection.objects.filter(
        technician=technician,
        unit__in=units
    )

    inspected_unit_ids = inspections.values_list('unit_id', flat=True)

    context = {
        'room': room,
        'units': units,
        'inspected_unit_ids': inspected_unit_ids
    }

    return render(request, 'technician/unit_inspection.html', context)


def inspection_history(request):
    technician = Technician.objects.get(email=request.user.email)

    inspections = Inspection.objects.filter(
        technician=technician
    ).select_related('unit', 'period').order_by('-date_checked')

    return render(request, 'technician/inspection_history.html', {
        "inspections": inspections
    })