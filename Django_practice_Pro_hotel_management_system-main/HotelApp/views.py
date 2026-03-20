from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging

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

logger = logging.getLogger(__name__)


# =========================
# BASIC PAGES
# =========================


STATIC_CARD_IMAGES = [
    "Allfiles/Photo/room-1.jpg",
    "Allfiles/Photo/room-2.jpg",
    "Allfiles/Photo/room-3.jpg",
    "Allfiles/Photo/room-4.jpg",
    "Allfiles/Photo/room-5.jpg",
    "Allfiles/Photo/room-6.jpg",
]


def home(request):
    if request.user.is_authenticated:
        return redirect("user_home")
    try:
        rooms = list(Room.objects.all().order_by('-id')[:6])
    except (OperationalError, ProgrammingError):
        logger.exception("Failed to load latest rooms for home page. Continuing with empty rooms list.")
        rooms = []

    card_room_ids = [str(room.id) for room in rooms[:6]]
    card_room_ids.extend([""] * max(0, 6 - len(card_room_ids)))

    room_cards = [
        {"room": room, "fallback_img": STATIC_CARD_IMAGES[i]}
        for i, room in enumerate(rooms[:6])
    ]

    return render(request, "Home.html", {
        "rooms": rooms,
        "card_room_ids": card_room_ids,
        "room_cards": room_cards,
    })



# =========================
# AUTH SYSTEM
# =========================

@login_required
def dashboard(request):
    rooms = Room.objects.filter(status='available')[:6]
    return render(request, "dashboard.html", {"rooms": rooms})
@login_required
def user_home(request):
    rooms = Room.objects.all()
    user_bookings = OnlineBooking.objects.filter(user=request.user).select_related('room')

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
            try:
                check_in  = datetime.strptime(check_in, "%Y-%m-%d").date()
                check_out = datetime.strptime(check_out, "%Y-%m-%d").date()
            except (TypeError, ValueError):
                messages.error(request, "Please enter valid dates.")
                return redirect("my_bookings")

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

    bookings = list(OnlineBooking.objects.filter(user=request.user).select_related('room').order_by("-created_at"))
    today = datetime.now().date()
    for b in bookings:
        b.nights = (b.check_out - b.check_in).days
    total_nights = sum(b.nights for b in bookings)
    total_bookings = len(bookings)
    active_bookings = sum(1 for b in bookings if b.check_out >= today)

    return render(request, "my_bookings.html", {
        "bookings": bookings,
        "total_nights": total_nights,
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
    })


@login_required
def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if request.method == "POST":
        check_in_raw = request.POST.get("check_in")
        try:
            stay_duration = int(request.POST.get("stay_duration", 1))
            adults = int(request.POST.get("adults", 1))
            children = int(request.POST.get("children", 0))
        except (TypeError, ValueError):
            messages.error(request, "Please enter valid numeric values.")
            return redirect("book_room", room_id=room.id)

        try:
            check_in = datetime.strptime(check_in_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            messages.error(request, "Please select a valid check-in date.")
            return redirect("book_room", room_id=room.id)

        if stay_duration <= 0:
            messages.error(request, "Stay duration must be at least one night.")
            return redirect("book_room", room_id=room.id)
        if adults <= 0 or children < 0:
            messages.error(request, "Please enter valid occupant counts.")
            return redirect("book_room", room_id=room.id)

        check_out = check_in + timedelta(days=stay_duration)

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
            adults=adults,
            children=children,
            city="N/A",
            country="N/A",
            address="N/A",
        )

        messages.success(request, f"Room {room.room_number} booked successfully!")
        return redirect("my_bookings")

    return render(request, "book_room.html", {"room": room})


# ----------------------------
# MY BOOKINGS — with cancel & modify

def online_booking(request):
    show_form = (not request.user.is_authenticated) or request.GET.get("new") == "1"

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to complete a booking.")
            return redirect("author_login")

        form_data = {
            "room_id": request.POST.get("room_id", "").strip(),
            "check_in": request.POST.get("check_in", "").strip(),
            "check_out": request.POST.get("check_out", "").strip(),
            "adults": request.POST.get("adults", "1").strip(),
            "children": request.POST.get("children", "0").strip(),
            "city": request.POST.get("city", "").strip(),
            "country": request.POST.get("country", "").strip(),
            "address": request.POST.get("address", "").strip(),
        }

        selected_room = None
        if not form_data["room_id"]:
            messages.error(request, "Please select a room.")
        else:
            selected_room = get_object_or_404(Room, id=form_data["room_id"])

        try:
            check_in = datetime.strptime(form_data["check_in"], "%Y-%m-%d").date()
            check_out = datetime.strptime(form_data["check_out"], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            check_in = check_out = None
            messages.error(request, "Please enter valid dates.")

        try:
            adults = int(form_data["adults"])
            children = int(form_data["children"])
        except (TypeError, ValueError):
            adults = children = None
            messages.error(request, "Please enter valid guest counts.")

        if check_in and check_out and check_in >= check_out:
            messages.error(request, "Check-out must be after check-in.")

        if adults is not None and (adults <= 0 or children < 0):
            messages.error(request, "Please enter valid guest counts.")

        if selected_room and check_in and check_out and adults is not None:
            overlapping = OnlineBooking.objects.filter(
                room=selected_room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exists()

            if overlapping:
                messages.error(request, "Room is not available for the selected dates.")
            else:
                OnlineBooking.objects.create(
                    user=request.user,
                    room=selected_room,
                    check_in=check_in,
                    check_out=check_out,
                    adults=adults,
                    children=children,
                    city=form_data["city"],
                    country=form_data["country"],
                    address=form_data["address"],
                )
                messages.success(request, "Booking successful!")
                return redirect("online_booking")

        rooms = Room.objects.all().order_by("room_number")
        return render(request, "online_booking_page.html", {
            "rooms": rooms,
            "room": selected_room,
            "form_data": form_data,
            "show_form": True,
        })

    if not show_form and request.user.is_authenticated:
        today = timezone.now().date()
        bookings = list(
            OnlineBooking.objects.filter(user=request.user, check_out__gte=today)
            .select_related('room', 'user')
            .order_by("-created_at")
        )
        for b in bookings:
            b.nights = (b.check_out - b.check_in).days
        return render(request, "online_booking_page.html", {
            "bookings": bookings,
            "show_form": False,
        })

    rooms = Room.objects.all().order_by("room_number")
    selected_room = None
    form_data = {}

    room_id = request.GET.get("room")
    if room_id:
        selected_room = Room.objects.filter(id=room_id).first()
        if selected_room:
            form_data["room_id"] = str(selected_room.id)

    return render(request, "online_booking_page.html", {
        "rooms": rooms,
        "room": selected_room,
        "form_data": form_data,
        "show_form": True,
    })


def online_booking_list(request):
    bookings = OnlineBooking.objects.all().select_related('user', 'room').order_by("-id")
    return render(request, "admin/Online_Booking.html", {"data": bookings})


@require_POST
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

    customers = OfflineBooking.objects.all().select_related('room').order_by("-id")
    return render(request, "admin/AddCustomer.html", {
        "form": form,
        "data": customers
    })


@require_POST
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


@require_POST
def delete_employee(request, id):
    employee = get_object_or_404(Employee, pk=id)
    employee.delete()
    return redirect("add_employee")

# =========================
# CONTACT PAGE
# =========================
def contact(request):
    return render(request, "contact.html")


# =========================
# THEME API
# =========================


@require_http_methods(["GET", "POST"])
def set_theme(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            return JsonResponse({"theme": request.user.theme})
        return JsonResponse({"theme": None})

    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth required"}, status=401)
    try:
        data = json.loads(request.body.decode())
        theme = data.get("theme")
        if theme not in ["light", "dark"]:
            return JsonResponse({"error": "invalid theme"}, status=400)
        request.user.theme = theme
        request.user.save(update_fields=["theme"])
        return JsonResponse({"theme": theme})
    except Exception:
        return JsonResponse({"error": "bad request"}, status=400)


# =========================
# ROOM
# =========================

# ROOM LIST PAGE
def room_list(request):
    rooms = Room.objects.all().order_by("room_number")
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


@require_POST
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

    salaries = Salary.objects.all().select_related('employee').order_by("-id")
    return render(request, "admin/AddEmployeeSalary.html", {
        "form": form,
        "data": salaries
    })
