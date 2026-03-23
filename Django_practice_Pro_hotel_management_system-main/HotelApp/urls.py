from django.urls import path
from . import views

urlpatterns = [
    # BASIC PAGES
    path('', views.home, name='home'),
    path('rooms/', views.room_list, name='room_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('home/', views.user_home, name='user_home'),
    path('book/<int:room_id>/', views.book_room, name='book_room'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('profile/', views.user_profile, name='user_profile'),
    path('contact/', views.contact, name='contact'),
    path('api/theme/', views.set_theme, name='set_theme'),

    # AUTH SYSTEM
    path('login/', views.author_login, name='author_login'),
    path('logout/', views.author_logout, name='auth_logout'),
    path('register/', views.author_register, name='author_register'),
    path('forgotpassword/', views.author_forgot_password, name='author_forgot_password'),

    # ONLINE BOOKING
    path('online-booking/', views.online_booking, name='online_booking'),
    path('online-booking/list/', views.online_booking_list, name='online_booking_list'),
    path('online-booking/edit/<int:id>/', views.online_booking_list, name='edit_online_booking'),
    path('online-booking/delete/<int:id>/', views.delete_online_booking, name='delete_online_booking'),

    # OFFLINE BOOKING
    path('offline-booking/', views.add_customer, name='add_customer'),
    path('offline-booking/edit/<int:id>/', views.add_customer, name='edit_customer'),
    path('offline-booking/delete/<int:id>/', views.delete_customer, name='delete_customer'),

    # EMPLOYEE MANAGEMENT
    path('employee/add/', views.add_employee, name='add_employee'),
    path('employee/edit/<str:id>/', views.add_employee, name='edit_employee'),
    path('employee/delete/<str:id>/', views.delete_employee, name='delete_employee'),

    # ROOM MANAGEMENT
    path('room/add/', views.add_room, name='add_room'),
    path('room/edit/<int:id>/', views.add_room, name='edit_room'),
    path('room/delete/<int:id>/', views.delete_room, name='delete_room'),

    # SALARY MANAGEMENT
    path('salary/add/', views.add_salary, name='add_salary'),
    path('salary/edit/<int:id>/', views.add_salary, name='edit_salary'),
    path('salary/delete/<int:id>/', views.delete_salary, name='delete_salary'),

    # USER MANAGEMENT
    path('users/', views.manage_users, name='manage_users'),
    path('users/edit/<int:id>/', views.manage_users, name='edit_user'),
    path('users/delete/<int:id>/', views.delete_user, name='delete_user'),
]
