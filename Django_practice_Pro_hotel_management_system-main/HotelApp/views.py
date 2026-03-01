from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponse
from .models import Room, OnlineBooking
from django.shortcuts import get_object_or_404, redirect
from datetime import datetime

from .models import (
    OnlineBooking,
    OfflineBooking,
    Employee,
    Room,
    Salary,
    Authorregis
)

from .forms import (
    OnlineBookingForm,
    OfflineBookingForm,
    EmployeeForm,
    RoomForm,
    SalaryForm
)


# =========================
# BASIC PAGES
# =========================


def home(request):
    rooms = Room.objects.all().order_by('-id')[:6]  # Show latest 6 rooms
    return render(request, "Home.html", {"rooms": rooms})



# =========================
# AUTH SYSTEM
# =========================

@login_required
def dashboard(request):
    rooms = Room.objects.filter(status='available')[:6]
    return render(request, "dashboard.html", {"rooms": rooms})
from django.contrib.auth.decorators import login_required

@login_required
def user_home(request):
    rooms = Room.objects.all()
    user_bookings = OnlineBooking.objects.filter(user=request.user)

    return render(request, "user_home.html", {
        "rooms": rooms,
        "user_bookings": user_bookings
    })

def author_register(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")  # match your form fields
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone_number")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("author_register")

        if Authorregis.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("author_register")

        user = Authorregis.objects.create_user(
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        user.phone_number = phone
        user.save()

        messages.success(request, "Registration successful!")
        return redirect("author_login")

    return render(request, "author_register.html")

def author_login(request):
    if request.method == "POST":
        email = request.POST.get("username")  # your form input is named "username"
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("user_home")
        else:
            messages.error(request, "Invalid credentials.")

    return render(request, "author_login.html")

def author_forgot_password(request):
    # You can add actual reset logic later
    return render(request, "author_forgot_password.html")


def author_logout(request):
    logout(request)
    return redirect("home")

# =========================
# USER PROFILE
# =========================
@login_required
def user_profile(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            request.user.first_name   = request.POST.get("first_name", "")
            request.user.last_name    = request.POST.get("last_name", "")
            request.user.phone_number = request.POST.get("phone_number", "")
            request.user.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("user_profile")

        elif action == "change_password":
            current  = request.POST.get("current_password")
            new_pw1  = request.POST.get("new_password1")
            new_pw2  = request.POST.get("new_password2")

            if not request.user.check_password(current):
                messages.error(request, "Current password is incorrect.")
                return redirect("user_profile")

            if new_pw1 != new_pw2:
                messages.error(request, "New passwords do not match.")
                return redirect("user_profile")

            if len(new_pw1) < 8:
                messages.error(request, "Password must be at least 8 characters.")
                return redirect("user_profile")

            request.user.set_password(new_pw1)
            request.user.save()
            # Keep user logged in after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully.")
            return redirect("user_profile")

    return render(request, "user_profile.html")

# =========================
# ONLINE BOOKING
# =========================
@login_required
def my_bookings(request):
    if request.method == "POST":
        action     = request.POST.get("action")
        booking_id = request.POST.get("booking_id")
        booking    = get_object_or_404(OnlineBooking, id=booking_id, user=request.user)

        if action == "cancel":
            booking.delete()
            messages.success(request, "Booking cancelled successfully.")
            return redirect("my_bookings")

        elif action == "modify":
            check_in  = request.POST.get("check_in")
            check_out = request.POST.get("check_out")
            check_in  = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out, "%Y-%m-%d").date()

            if check_in >= check_out:
                messages.error(request, "Check-out must be after check-in.")
                return redirect("my_bookings")

            # Check overlap excluding this booking
            overlapping = OnlineBooking.objects.filter(
                room=booking.room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(id=booking.id).exists()

            if overlapping:
                messages.error(request, "Room is not available for the new dates.")
                return redirect("my_bookings")

            booking.check_in  = check_in
            booking.check_out = check_out
            booking.save()
            messages.success(request, "Booking updated successfully.")
            return redirect("my_bookings")

    bookings = OnlineBooking.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "my_bookings.html", {"bookings": bookings})


@login_required
def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if request.method == "POST":
        check_in  = request.POST.get("check_in")
        check_out = request.POST.get("check_out")
        adults    = request.POST.get("adults", 1)
        children  = request.POST.get("children", 0)
        city      = request.POST.get("city", "")
        country   = request.POST.get("country", "")
        address   = request.POST.get("address", "")

        check_in  = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out, "%Y-%m-%d").date()

        if check_in >= check_out:
            messages.error(request, "Check-out must be after check-in.")
            return redirect("book_room", room_id=room.id)

        # Check for overlapping bookings
        overlapping = OnlineBooking.objects.filter(
            room=room,
            check_in__lt=check_out,
            check_out__gt=check_in
        ).exists()

        if overlapping:
            messages.error(request, "Room is not available for the selected dates.")
            return redirect("book_room", room_id=room.id)

        OnlineBooking.objects.create(
            user=request.user,
            room=room,
            check_in=check_in,
            check_out=check_out,
            adults=int(adults),
            children=int(children),
            city=city,
            country=country,
            address=address,
        )

        messages.success(request, f"Room {room.room_number} booked successfully!")
        return redirect("my_bookings")

    return render(request, "book_room.html", {"room": room})


# ----------------------------
# MY BOOKINGS — with cancel & modify

def online_booking(request):
    if request.method == "POST":
        form = OnlineBookingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Booking successful!")
            return redirect("online_booking")
    else:
        form = OnlineBookingForm()

    return render(request, "online_booking_page.html", {"form": form})


def online_booking_list(request):
    bookings = OnlineBooking.objects.all().order_by("-id")
    return render(request, "admin/Online_Booking.html", {"data": bookings})


def delete_online_booking(request, id):
    booking = get_object_or_404(OnlineBooking, pk=id)
    booking.delete()
    return redirect("online_booking_list")


# =========================
# OFFLINE BOOKING
# =========================

def add_customer(request):
    if request.method == "POST":
        form = OfflineBookingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer added successfully!")
            return redirect("add_customer")
    else:
        form = OfflineBookingForm()

    customers = OfflineBooking.objects.all().order_by("-id")
    return render(request, "admin/AddCustomer.html", {
        "form": form,
        "data": customers
    })


def delete_customer(request, id):
    customer = get_object_or_404(OfflineBooking, pk=id)
    customer.delete()
    return redirect("add_customer")


# =========================
# EMPLOYEE
# =========================

def add_employee(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee added successfully!")
            return redirect("add_employee")
    else:
        form = EmployeeForm()

    employees = Employee.objects.all().order_by("-employee_id")
    return render(request, "admin/addemployee.html", {
        "form": form,
        "data": employees
    })


def delete_employee(request, id):
    employee = get_object_or_404(Employee, pk=id)
    employee.delete()
    return redirect("add_employee")


# =========================
# ROOM
# =========================

# ROOM LIST PAGE
def room_list(request):
    rooms = Room.objects.filter(status='available')
    return render(request, "rooms_list.html", {"rooms": rooms})

def add_room(request):
    if request.method == "POST":
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Room added successfully!")
            return redirect("add_room")
    else:
        form = RoomForm()

    rooms = Room.objects.all().order_by("-id")
    return render(request, "admin/AddRoom.html", {
        "form": form,
        "data": rooms
    })


def delete_room(request, id):
    room = get_object_or_404(Room, pk=id)
    room.delete()
    return redirect("add_room")


# =========================
# SALARY
# =========================

def add_salary(request):
    if request.method == "POST":
        form = SalaryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Salary added successfully!")
            return redirect("add_salary")
    else:
        form = SalaryForm()

    salaries = Salary.objects.all().order_by("-id")
    return render(request, "admin/AddEmployeeSalary.html", {
        "form": form,
        "data": salaries
    })