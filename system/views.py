from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from datetime import date
from django.db.models import Prefetch, IntegerField, Q, Count, Max
from django.db.models.functions import Cast, Substr
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# =========================
# AUTH
# =========================

def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )

        if user:
            login(request, user)
            tech = Technician.objects.filter(user=user).first()

            if tech and tech.role == "Admin":
                return redirect("dashboard")
            elif tech:
                return redirect("tech_dashboard")

            messages.error(request, "No role assigned")
        else:
            messages.error(request, "Invalid login")

        return redirect("login")

    return render(request, "login.html")


def register_view(request):
    if request.method == "POST":
        if request.POST.get("password") != request.POST.get("password2"):
            messages.error(request, "Passwords do not match")
            return redirect("register")

        if User.objects.filter(username=request.POST.get("username")).exists():
            messages.error(request, "Username exists")
            return redirect("register")

        role = request.POST.get("role")

        user = User.objects.create_user(
            username=request.POST.get("username"),
            password=request.POST.get("password"),
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            email=request.POST.get("email"),
            is_staff=(role == "Admin"),
            is_superuser=(role == "Admin")
        )

        Technician.objects.create(
            user=user,
            role=role,
            name=f"{user.first_name} {user.last_name}",
            email=user.email,
            status="Active"
        )

        login(request, user)
        return redirect("dashboard" if role == "Admin" else "tech_dashboard")

    return render(request, "register.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# =========================
# DASHBOARD
# =========================

@login_required
def dashboard(request):
    rooms = LabRoom.objects.all().order_by('room_name')
    paginator = Paginator(rooms, 10)

    return render(request, 'dashboard/dashboard.html', {
        'total_rooms': LabRoom.objects.count(),
        'total_units': ComputerUnit.objects.count(),
        'total_inspections': Inspection.objects.count(),
        'rooms': paginator.get_page(request.GET.get('page', 1)),
    })


@login_required
def room_detail(request, room_id):
    room = get_object_or_404(LabRoom, id=room_id)

    units = ComputerUnit.objects.filter(room=room).order_by('asset_tag')    

    # Attach hardware (first hardware object per unit)
    for unit in units:
        unit.hardware = unit.hardware_set.first()  # hardware_set is the reverse FK

    paginator = Paginator(units, 10)

    return render(request, 'dashboard/room_detail.html', {
        'room': room,
        'units': paginator.get_page(request.GET.get('page')),
        'total_units': units.count(),
        'total_working': units.filter(status='Working').count(),
        'total_defective': units.filter(status='Defective').count(),
        'total_maintenance': units.filter(status='Maintenance').count(),
    })

# =========================
# LABORATORY CRUD
# =========================

@login_required
def laboratory(request):
    rooms = LabRoom.objects.all().order_by('room_name')
    paginator = Paginator(rooms, 10)

    return render(request, 'dashboard/laboratory.html', {
        'rooms': paginator.get_page(request.GET.get('page', 1))
    })


@login_required
def add_laboratory(request):
    if request.method == "POST":
        LabRoom.objects.create(
            room_name=request.POST.get("room_name"),
            location=request.POST.get("location"),
            capacity=request.POST.get("capacity") or 0
        )
        messages.success(request, "Lab added")

    return redirect("laboratory")


@login_required
def delete_laboratory(request, room_id):
    if request.method == "POST":
        room = get_object_or_404(LabRoom, id=room_id)
        room.delete()
    return redirect("laboratory")


# STILL IN DEBUGGING
@login_required
def add_unit(request):
    if request.method == "POST":
        room_id = request.POST.get("room_id")
        room = get_object_or_404(LabRoom, id=room_id)  # Correct model

        # Create the unit
        unit = ComputerUnit.objects.create(
            room=room,
            asset_tag=request.POST.get("asset_tag"),
            status=request.POST.get("status"),
        )

        # Create or update hardware if any field is provided
        cpu = request.POST.get("cpu")
        ram = request.POST.get("ram")
        storage = request.POST.get("storage")
        gpu = request.POST.get("gpu")
        os_field = request.POST.get("os")
        installed_apps = request.POST.get("installed_apps")

        if cpu or ram or storage or gpu or os_field or installed_apps:
            Hardware.objects.create(
                unit=unit,
                cpu=cpu or "",
                ram=ram or "",
                storage=storage or "",
                gpu=gpu or "",
            )
            Software.objects.create(
                os=os_field or "",
                installed_apps=installed_apps or "",
            )

        messages.success(request, f"Unit {unit.asset_tag} added successfully.")
        return redirect("room", room_id=room.id)

@login_required
def view_unit(request, unit_id):
    unit = get_object_or_404(ComputerUnit, id=unit_id)
    hardware, _ = Hardware.objects.get_or_create(unit=unit)
    software, _ = Software.objects.get_or_create(unit=unit)

    if request.method == "POST":
        if "update" in request.POST:
            unit.asset_tag = request.POST.get("asset_tag")
            unit.status = request.POST.get("status")
            unit.save()

            hardware.cpu = request.POST.get("cpu", hardware.cpu)
            hardware.ram = request.POST.get("ram", hardware.ram)
            hardware.storage = request.POST.get("storage", hardware.storage)
            hardware.gpu = request.POST.get("gpu", hardware.gpu)
            hardware.save()

            software.os = request.POST.get("os", software.os)
            software.installed_apps = request.POST.get("installed_apps", software.installed_apps)
            software.save()

            # Update rating/inspection if selected
            condition = request.POST.get("condition")
            remarks = request.POST.get("remarks", "")
            if condition:
                # Assuming you have a Rating model linked to unit
                rating, _ = Rating.objects.get_or_create(unit=unit)
                rating.hardware_condition = condition
                rating.remarks = remarks
                rating.save()

            messages.success(request, "Unit, hardware, software, and integrity updated successfully.")

        elif "delete" in request.POST:
            room_id = unit.room.id
            unit.delete()
            messages.success(request, "Unit deleted successfully.")
            return redirect("room", room_id=room_id)

        return redirect("view_unit", unit_id=unit.id)

    inspections = Inspection.objects.filter(unit=unit).order_by('-date_checked')
    rating = ConditionRating.objects.filter(unit=unit).last()  # Get latest rating for system integrity

    return render(request, "dashboard/view_unit.html", {
        "unit": unit,
        "hardware": hardware,
        "software": software,
        "rooms": LabRoom.objects.all(),
        "inspections": inspections,
        "rating": rating,  # pass rating to template
    })

@login_required
def report(request):
    school_year = request.GET.get('school_year')

    # Fetch inspections with related objects to reduce queries
    inspections = Inspection.objects.select_related(
        'unit', 'unit__room', 'technician', 'technician__user', 'period'
    ).order_by('-date_checked')

    # Filter by school year if provided
    if school_year:
        inspections = inspections.filter(period__school_year=school_year)

    # Paginate inspections (10 per page)
    paginator = Paginator(inspections, 10)
    page_number = request.GET.get('page')
    inspections_page = paginator.get_page(page_number)

    return render(request, 'dashboard/report.html', {
        'inspections': inspections_page,
        'school_year': school_year,
    })
    
    # =========================
# TECHNICIAN CRUD
# =========================

@login_required
def technician_list(request):
    techs = Technician.objects.all()
    paginator = Paginator(techs, 10)

    return render(request, 'dashboard/technicians.html', {
        'technicians': paginator.get_page(request.GET.get('page'))
    })


@login_required
def delete_technician(request, technician_id):
    tech = get_object_or_404(Technician, id=technician_id)
    tech.delete()
    messages.success(request, "Deleted")
    return redirect("technicians")


# =========================
# TECHNICIAN SIDE
# =========================

@login_required
def tech_dashboard(request):
    # Get the logged-in technician
    try:
        technician = Technician.objects.get(user=request.user)
    except Technician.DoesNotExist:
        messages.error(request, "Technician profile not found.")
        return redirect("login")

    # Labs where this technician has inspections
    assigned_rooms = LabRoom.objects.filter(
        computerunit__inspections__technician=technician
    ).distinct()

    # Annotate each lab with stats
    assigned_rooms = assigned_rooms.annotate(
        total_units=Count('computerunit', distinct=True),
        working_units=Count('computerunit', filter=Q(computerunit__status='Working')),
        defective_units=Count('computerunit', filter=Q(computerunit__status='Defective')),
        maintenance_units=Count('computerunit', filter=Q(computerunit__status='Maintenance')),
        last_inspected=Max('computerunit__inspections__date_checked')
    )

    # Inspections assigned to this technician
    inspections = Inspection.objects.filter(technician=technician)

    # Counts for dashboard summary
    pending_count = inspections.filter(status='Pending').count()
    completed_count = inspections.filter(status='Completed').count()

    context = {
        "technician": technician,
        "assigned_rooms": assigned_rooms,
        "total_labs": assigned_rooms.count(),
        "pending_inspections": pending_count,
        "completed_inspections": completed_count,
    }

    return render(request, "technician/dashboard.html", context)   
         
@login_required
def assigned_laboratories(request):
    tech = get_object_or_404(Technician, user=request.user)

    rooms = LabRoom.objects.filter(
        computerunit__inspections__technician=tech
    ).distinct()

    labs_info = []

    for room in rooms:
        units = ComputerUnit.objects.filter(room=room)

        inspections = Inspection.objects.filter(
            unit__room=room,
            technician=tech
        ).order_by('-date_checked')

        last_inspection = inspections.first()

        # Determine status
        if not last_inspection:
            status = "NO INSPECTION"
        else:
            days_passed = (date.today() - last_inspection.date_checked).days

            if days_passed <= 30:
                status = "COMPLIANT"
            elif days_passed <= 60:
                status = "WARNING"
            else:
                status = "OVERDUE"

        labs_info.append({
            "lab": room,
            "total_computers": units.count(),
            "last_inspected_date": last_inspection.date_checked if last_inspection else None,
            "last_inspector": last_inspection.technician.name if last_inspection else None,
            "status": status
        })

    return render(request, 'technician/assigned_laboratories.html', {
        'labs_info': labs_info,
        'total_labs': len(labs_info)
    })

@login_required
def inspection_form(request):
    labs = LabRoom.objects.all().order_by('room_name')
    periods = AssessmentPeriod.objects.all().order_by('-date_start')

    selected_lab_id = request.POST.get("lab") or request.GET.get("lab")
    units = ComputerUnit.objects.filter(room_id=selected_lab_id) if selected_lab_id else []

    selected_unit_id = request.POST.get("unit")
    selected_period_id = request.POST.get("period")

    if request.method == "POST":
        if not selected_unit_id or not selected_period_id:
            messages.error(request, "Please select a unit and period.")
            return redirect("inspection_form")

        unit = get_object_or_404(ComputerUnit, id=selected_unit_id)
        period = get_object_or_404(AssessmentPeriod, id=selected_period_id)
        technician = get_object_or_404(Technician, user=request.user)

        # Create a new inspection every time
        inspection = Inspection.objects.create(
            unit=unit,
            period=period,
            technician=technician,
            date_checked=date.today()
        )

        # Create rating for this inspection
        ConditionRating.objects.create(
            inspection=inspection,
            hardware_condition=request.POST.get("hardware", "-"),
            software_condition=request.POST.get("software", "-"),
            remarks=request.POST.get("remarks", "")
        )

        messages.success(request, f"Inspection for {unit.asset_tag} saved successfully.")
        return redirect("assigned_laboratories")

    return render(request, "technician/form.html", {
        "labs": labs,
        "units": units,
        "periods": periods,
        "selected_lab_id": int(selected_lab_id) if selected_lab_id else None,
        "selected_unit_id": int(selected_unit_id) if selected_unit_id else None,
        "selected_period_id": int(selected_period_id) if selected_period_id else None,
    })

def inspection_detail(request, room_id):
    room = get_object_or_404(LabRoom, id=room_id)

    inspections = Inspection.objects.filter(unit__room=room).select_related(
        'unit', 'technician', 'period'
    ).prefetch_related(
        'rating',
        'unit__equipment_set'
    ).order_by('date_checked')

    latest_period = inspections.last()  # because already ordered by date_checked ascending
    school_year = latest_period.period.school_year if latest_period else "N/A"

    return render(request, 'dashboard/inspection_details.html', {
        'room': room,
        'inspections': inspections,
        'school_year': school_year
    })
    
@login_required
def view_inspection(request):
    inspections = Inspection.objects.select_related(
        'unit', 'unit__room', 'technician__user', 'period'
    ).prefetch_related('conditionrating_set').order_by('-date_checked')

    paginator = Paginator(inspections, 10)
    page_number = request.GET.get('page', 1)
    inspections_page = paginator.get_page(page_number)

    return render(request, 'dashboard/inspection_list.html', {
        'inspections': inspections_page
    })
@login_required
def add_inspection(request):
    if request.method == "POST":
        form = InspectionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Inspection added successfully")
            return redirect("view_inspection")
    else:
        form = InspectionForm()

    return render(request, 'dashboard/report.html', {'form': form, 'action': 'Add'})



@login_required
def delete_inspection(request, id):
    inspection = get_object_or_404(Inspection, id=id)
    inspection.delete()
    messages.success(request, "Inspection deleted successfully")
    return redirect("report")

@login_required 
def inspection_history(request): 
    inspections = Inspection.objects.select_related( 
        'unit', 
        'technician', 
        'period' 
    ).prefetch_related('rating').order_by('-date_checked') 
    return render(request, 'technician/inspection_history.html', { "inspections": inspections })