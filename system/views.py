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

    units = ComputerUnit.objects.filter(room=room).annotate(
        station_num=Cast(Substr('asset_tag', 45), IntegerField())
    ).order_by('station_num')

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
    room = get_object_or_404(LabRoom, id=room_id)
    room.delete()
    messages.success(request, "Lab deleted")
    return redirect("laboratory")

@login_required
def add_unit(request):
    if request.method == "POST":
        room = get_object_or_404(LabRoom, id=request.POST.get("room_id"))

        unit = ComputerUnit.objects.create(
            asset_tag=request.POST.get("asset_tag"),
            room=room,
            status=request.POST.get("status") or "Working"
        )

        Hardware.objects.create(unit=unit)
        Software.objects.create(unit=unit)

    return redirect("room", room_id=room.id)


@login_required
def view_unit(request, unit_id):
    unit = get_object_or_404(ComputerUnit, id=unit_id)

    if request.method == "POST":

        # UPDATE
        if "update" in request.POST:
            unit.asset_tag = request.POST.get("asset_tag")
            unit.status = request.POST.get("status")
            unit.save()
            messages.success(request, "Updated")

        # DELETE
        elif "delete" in request.POST:
            room_id = unit.room.id
            unit.delete()
            messages.success(request, "Deleted")
            return redirect("room", room_id=room_id)

    inspections = Inspection.objects.filter(unit=unit)

    return render(request, "dashboard/view_unit.html", {
        "unit": unit,
        "hardware": getattr(unit, 'hardware', None),
        "software": getattr(unit, 'software', None),
        "rooms": LabRoom.objects.all(),
        "inspections": inspections,
    })


@login_required
def delete_unit(request, unit_id):
    unit = get_object_or_404(ComputerUnit, id=unit_id)
    room_id = unit.room.id
    unit.delete()
    return redirect("room", room_id=room_id)


# =========================
# REPORT
# =========================

@login_required
def report(request):
    school_year = request.GET.get('school_year')

    rooms = LabRoom.objects.all()

    if school_year:
        rooms = rooms.filter(
            computerunit__inspections__period__school_year=school_year
        ).distinct()

    return render(request, 'dashboard/report.html', {
        'rooms': rooms,
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

    return render(request, 'technician/assigned_laboratories.html', {
        'assigned_rooms': rooms
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

@login_required
def view_inspection(request):
    inspections = Inspection.objects.select_related(
        'unit', 'technician__user', 'period'
    ).order_by('-date_checked')

    paginator = Paginator(inspections, 10)
    page_number = request.GET.get('page', 1)
    inspections_page = paginator.get_page(page_number)

    return render(request, 'dashboard/report.html', {
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
def edit_inspection(request, id):
    inspection = get_object_or_404(Inspection, id=id)
    if request.method == "POST":
        form = InspectionForm(request.POST, instance=inspection)
        if form.is_valid():
            form.save()
            messages.success(request, "Inspection updated successfully")
            return redirect("view_inspection")
    else:
        form = InspectionForm(instance=inspection)

    return render(request, 'dashboard/report.html', {'form': form, 'action': 'Edit', 'inspection': inspection})


@login_required
def delete_inspection(request, id):
    inspection = get_object_or_404(Inspection, id=id)
    inspection.delete()
    messages.success(request, "Inspection deleted successfully")
    return redirect("view_inspection")

@login_required 
def inspection_history(request): 
    inspections = Inspection.objects.select_related( 
        'unit', 
        'technician', 
        'period' 
    ).prefetch_related('rating').order_by('-date_checked') 
    return render(request, 'technician/inspection_history.html', { "inspections": inspections })