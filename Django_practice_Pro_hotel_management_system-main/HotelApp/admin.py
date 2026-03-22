from django.contrib import admin
from .models import Authorregis, Room, OnlineBooking, OfflineBooking, Employee, Salary


@admin.register(Authorregis)
class AuthorregisAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone_number', 'theme', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active', 'theme')
    ordering = ('-date_joined',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'room_type', 'floor', 'price', 'status', 'created_at')
    search_fields = ('room_number',)
    list_filter = ('room_type', 'status', 'floor')
    ordering = ('room_number',)


@admin.register(OnlineBooking)
class OnlineBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'check_in', 'check_out', 'adults', 'children', 'created_at')
    list_select_related = ('user', 'room')
    search_fields = ('user__email', 'room__room_number')
    list_filter = ('check_in', 'check_out')
    ordering = ('-created_at',)


@admin.register(OfflineBooking)
class OfflineBookingAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'room', 'check_in', 'check_out', 'created_at')
    list_select_related = ('room',)
    search_fields = ('first_name', 'last_name', 'email', 'room__room_number')
    list_filter = ('check_in', 'check_out')
    ordering = ('-created_at',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'email', 'department', 'joining_date')
    search_fields = ('employee_id', 'first_name', 'last_name', 'email')
    list_filter = ('department', 'gender')
    ordering = ('first_name',)


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'salary', 'created_at')
    list_select_related = ('employee',)
    search_fields = ('employee__first_name', 'employee__last_name')
    ordering = ('-created_at',)
