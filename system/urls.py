from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('room/<int:room_id>/', views.room_detail, name='room'),

    path('laboratory/', views.laboratory, name='laboratory'),
    path('add-lab/', views.add_laboratory, name='add_laboratory'),
    path('delete-lab/<int:room_id>/', views.delete_laboratory, name='delete_laboratory'),

    path('unit/<int:unit_id>/', views.view_unit, name='view_unit'),
    path('add-unit/', views.add_unit, name='add_unit'),
    path('delete-unit/<int:unit_id>/', views.delete_unit, name='delete_unit'),

    path('report/', views.report, name='report'),
    path('view-inspection/', views.view_inspection, name='view_inspection'),
    path('add-inspection/', views.add_inspection, name='add_inspection'),
    path('edit-inspection/<int:id>/', views.edit_inspection, name='edit_inspection'),
    path('delete-inspection/<int:id>/', views.delete_inspection, name='delete_inspection'),

    path('technicians/', views.technician_list, name='technicians'),
    path('delete-technician/<int:id>/', views.delete_technician, name='delete_technician'),

    path('tech-dashboard/', views.tech_dashboard, name='tech_dashboard'),
    path('assigned-laboratories/', views.assigned_laboratories, name='assigned_laboratories'),
    path('inspection/', views.inspection_form, name='inspection_form'),
    path('history/', views.inspection_history, name='inspection_history'),
]