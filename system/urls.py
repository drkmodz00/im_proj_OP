from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('room/<int:room_id>/', views.room_detail, name='room'),
    path('laboratory/', views.laboratory, name='laboratory'),
    path('inspection/', views.inspection_form, name='inspection_form'),
    path('report/', views.report, name='report'),
    path('technicians/', views.technician_list, name='technicians'),

    path('report/room/<int:room_id>/details/', views.view_inspection_details, name='view_inspection_details'),
    path('report/room/<int:room_id>/delete/', views.delete_inspections_by_room, name='delete_inspections_by_room'),
   
    
    path('unit/<int:unit_id>/', views.view_unit, name='view_unit'),

    path("add-lab/", views.add_lab, name="add_lab"),
    path("delete-lab/<int:room_id>/", views.delete_lab, name="delete_lab"),

    path("add-unit/", views.add_unit, name="add_unit"),
    path("delete-unit/<int:unit_id>/", views.delete_unit, name="delete_unit"),

    path("add-technician/", views.add_technician, name="add_technician"),
    path("delete-technician/<int:technician_id>/", views.delete_technician, name="delete_technician"),
    path("edit-technician/<int:technician_id>/", views.edit_technician, name="edit_technician"),
    path('technician-profile/<int:technician_id>/', views.technician_profile, name='technician_profile'),

         
    # urls.py
]