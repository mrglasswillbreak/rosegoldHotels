from functools import wraps
from urllib.parse import urlencode
import json
import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from pypaystack2 import PaystackClient

from .models import (
    OnlineBooking,
    OfflineBooking,
    Employee,
    Room,
    Salary,
    Authorregis,
    Payment,
    HousekeepingTask,
    ActivityLog
)

from .forms import (
    AdminUserCreateForm,
    AdminUserUpdateForm,
    OnlineBookingForm,
    OfflineBookingForm,
    EmployeeForm,
    RoomForm,
    SalaryForm,
    booking_window_has_conflict,
)

logger = logging.getLogger(__name__)


def get_post_login_route_name(user):
    if user.is_receptionist:
        return "receptionist_dashboard"
    elif user.is_staff:
        return "dashboard"
    else:
        return "user_home"


def get_safe_next_url(request):
    """Return the ?next= redirect target if it is safe, otherwise return ''."""
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


def get_post_login_redirect(request, user):
    next_url = get_safe_next_url(request)
    return next_url or reverse(get_post_login_route_name(user))


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("author_login")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")
        if not request.user.is_staff:
            messages.error(request, "You do not have permission to access the admin dashboard.")
            return redirect("user_home")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def build_admin_context(active_admin_section, **context):
    context["active_admin_section"] = active_admin_section
    return context


def apply_admin_search(queryset, query, fields):
    if not query:
        return queryset

    search_query = Q()
    for field in fields:
        search_query |= Q(**{f"{field}__icontains": query})
    return queryset.filter(search_query)


def shift_month(month_start, delta):
    total_months = (month_start.year * 12) + (month_start.month - 1) + delta
    year, month_index = divmod(total_months, 12)
    return date(year, month_index + 1, 1)


def recent_month_starts(count=6):
    current_month = timezone.localdate().replace(day=1)
    return [shift_month(current_month, -offset) for offset in range(count - 1, -1, -1)]


def monthly_totals(queryset, date_field="created_at", count=6):
    month_starts = recent_month_starts(count=count)
    totals = {month_start: 0 for month_start in month_starts}

    for row in queryset.annotate(month=TruncMonth(date_field)).values("month").annotate(total=Count("id")).order_by("month"):
        month_value = row["month"]
        if hasattr(month_value, "date"):
            month_key = month_value.date().replace(day=1)
        else:
            month_key = month_value.replace(day=1)
        if month_key in totals:
            totals[month_key] = row["total"]

    labels = [month_start.strftime("%b %Y") for month_start in month_starts]
    values = [totals[month_start] for month_start in month_starts]
    return labels, values


def calculate_booking_revenue(bookings):
    total = Decimal("0")
    for booking in bookings:
        nights = max((booking.check_out - booking.check_in).days, 0)
        total += booking.room.price * nights
    return total


def format_naira(amount):
    value = Decimal(str(amount))
    rounded = value.quantize(Decimal("0.01"))
    if rounded == rounded.to_integral():
        return f"₦{int(rounded):,}"
    return f"₦{rounded:,.2f}"


# =========================
# BASIC PAGES
# =========================


def home(request):
    if request.user.is_authenticated:
        return redirect(get_post_login_route_name(request.user))
    try:
        rooms = list(Room.objects.all().order_by('-id')[:6])
    except (OperationalError, ProgrammingError):
        logger.exception("Failed to load latest rooms for home page. Continuing with empty rooms list.")
        rooms = []

    card_room_ids = [str(room.id) for room in rooms[:6]]
    card_room_ids.extend([""] * max(0, 6 - len(card_room_ids)))

    return render(request, "Home.html", {
        "rooms": rooms,
        "card_room_ids": card_room_ids,
    })



# =========================
# AUTH SYSTEM
# =========================

@admin_required
def dashboard(request):
    today = timezone.localdate()
    rooms = Room.objects.all()
    users = Authorregis.objects.all()
    employees = Employee.objects.all()
    online_bookings = OnlineBooking.objects.select_related("user", "room")
    offline_bookings = OfflineBooking.objects.select_related("room")
    salaries = Salary.objects.select_related("employee")

    room_status_counts = {
        "Available": rooms.filter(status="available").count(),
        "Occupied": rooms.filter(status="occupied").count(),
        "Maintenance": rooms.filter(status="maintenance").count(),
    }

    occupied_room_ids = set(
        online_bookings.filter(check_in__lte=today, check_out__gt=today).values_list("room_id", flat=True)
    )
    occupied_room_ids.update(
        offline_bookings.filter(check_in__lte=today, check_out__gt=today).values_list("room_id", flat=True)
    )

    total_rooms = rooms.count()
    total_online_bookings = online_bookings.count()
    total_offline_bookings = offline_bookings.count()
    total_bookings = total_online_bookings + total_offline_bookings
    total_users = users.count()
    total_staff_users = users.filter(is_staff=True).count()
    total_guest_users = users.filter(is_staff=False).count()
    total_employees = employees.count()
    available_rooms = rooms.filter(status="available").count()
    occupancy_rate = round((len(occupied_room_ids) / total_rooms) * 100, 1) if total_rooms else 0
    check_ins_today = online_bookings.filter(check_in=today).count() + offline_bookings.filter(check_in=today).count()
    check_outs_today = online_bookings.filter(check_out=today).count() + offline_bookings.filter(check_out=today).count()

    booking_labels, online_booking_series = monthly_totals(online_bookings, "created_at")
    _, offline_booking_series = monthly_totals(offline_bookings, "created_at")
    booking_series = [online + offline for online, offline in zip(online_booking_series, offline_booking_series)]

    account_distribution_labels = ["Admins", "Guests", "Employees"]
    account_distribution_values = [total_staff_users, total_guest_users, total_employees]

    estimated_revenue = calculate_booking_revenue(online_bookings.select_related("room")) + calculate_booking_revenue(
        offline_bookings.select_related("room")
    )
    monthly_salary_budget = sum((salary.salary for salary in salaries), Decimal("0"))
    iot_summary = None
    recent_iot_alerts = []

    try:
        from alerts.services import build_monitoring_snapshot
        from alerts.runtime import run_monitoring_cycle

        run_monitoring_cycle(force_refresh=False)
        iot_snapshot = build_monitoring_snapshot(force_refresh=False)
        iot_summary = iot_snapshot["summary"]
        recent_iot_alerts = iot_snapshot["alerts"][:5]
    except (OperationalError, ProgrammingError):
        logger.warning("IoT monitoring tables are not available yet; skipping dashboard summary.", exc_info=True)

    context = build_admin_context(
        "dashboard",
        stats={
            "total_bookings": total_bookings,
            "online_bookings": total_online_bookings,
            "offline_bookings": total_offline_bookings,
            "rooms_available": available_rooms,
            "occupied_rooms": len(occupied_room_ids),
            "occupancy_rate": occupancy_rate,
            "check_ins_today": check_ins_today,
            "check_outs_today": check_outs_today,
            "users": total_users,
            "staff_users": total_staff_users,
            "employees": total_employees,
            "estimated_revenue": float(estimated_revenue),
            "monthly_salary_budget": float(monthly_salary_budget),
        },
        booking_chart_labels=json.dumps(booking_labels),
        booking_chart_values=json.dumps(booking_series),
        room_status_labels=json.dumps(list(room_status_counts.keys())),
        room_status_values=json.dumps(list(room_status_counts.values())),
        account_distribution_labels=json.dumps(account_distribution_labels),
        account_distribution_values=json.dumps(account_distribution_values),
        recent_online_bookings=online_bookings.order_by("-created_at")[:5],
        recent_offline_bookings=offline_bookings.order_by("-created_at")[:5],
        recent_users=users.order_by("-date_joined")[:5],
        recent_employees=employees.order_by("-created_at")[:5],
        recent_rooms=rooms.order_by("-created_at")[:5],
        iot_summary=iot_summary,
        recent_iot_alerts=recent_iot_alerts,
    )
    return render(request, "admin/Admin.html", context)
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
    if request.user.is_authenticated:
        return redirect(get_post_login_redirect(request, request.user))

    if request.method == "POST":
        email = request.POST.get("username")  # your form input is named "username"
        password = request.POST.get("password")
        try:
            user = authenticate(request, email=email, password=password)
        except ValueError:
            logger.exception("Malformed password hash for login attempt: %s", email)
            user = None

        if user:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect(get_post_login_redirect(request, user))
        else:
            messages.error(request, "Invalid credentials.")

    return render(request, "author_login.html", {"next": get_safe_next_url(request)})

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

            if booking_window_has_conflict(
                booking.room,
                check_in,
                check_out,
                online_instance=booking,
            ):
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

        if booking_window_has_conflict(room, check_in, check_out):
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
            if booking_window_has_conflict(selected_room, check_in, check_out):
                messages.error(request, "Room is not available for the selected dates.")
            else:
                # Store booking data in session for payment processing
                request.session['pending_booking'] = {
                    'room_id': selected_room.id,
                    'check_in': form_data["check_in"],
                    'check_out': form_data["check_out"],
                    'adults': adults,
                    'children': children,
                    'city': form_data["city"],
                    'country': form_data["country"],
                    'address': form_data["address"],
                }
                
                # Redirect to payment page instead of creating booking
                return redirect("booking_payment_page")

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


@admin_required
def online_booking_list(request, id=None):
    booking = get_object_or_404(OnlineBooking.objects.select_related("user", "room"), pk=id) if id else None

    if request.method == "POST":
        form = OnlineBookingForm(request.POST, instance=booking)
        if form.is_valid():
            saved_booking = form.save()
            messages.success(
                request,
                f"Online booking for {saved_booking.user.email} saved successfully.",
            )
            return redirect("online_booking_list")
    else:
        form = OnlineBookingForm(instance=booking)

    search_query = request.GET.get("q", "").strip()
    bookings = OnlineBooking.objects.select_related("user", "room").order_by("-created_at")
    bookings = apply_admin_search(
        bookings,
        search_query,
        ["user__email", "user__first_name", "user__last_name", "room__room_number", "city", "country", "address"],
    )

    context = build_admin_context(
        "online_bookings",
        form=form,
        data=bookings,
        editing_object=booking,
        search_query=search_query,
        form_action_url=reverse("edit_online_booking", args=[booking.pk]) if booking else reverse("online_booking_list"),
        submit_label="Update Booking" if booking else "Create Booking",
    )
    return render(request, "admin/Online_Booking.html", context)


@require_POST
@admin_required
def delete_online_booking(request, id):
    booking = get_object_or_404(OnlineBooking, pk=id)
    booking.delete()
    messages.success(request, "Online booking deleted successfully.")
    return redirect("online_booking_list")


# =========================
# OFFLINE BOOKING
# =========================

@admin_required
def add_customer(request, id=None):
    customer = get_object_or_404(OfflineBooking.objects.select_related("room"), pk=id) if id else None

    if request.method == "POST":
        form = OfflineBookingForm(request.POST, instance=customer)
        if form.is_valid():
            saved_customer = form.save()
            messages.success(
                request,
                f"Offline booking for {saved_customer.first_name} {saved_customer.last_name} saved successfully.",
            )
            return redirect("add_customer")
    else:
        form = OfflineBookingForm(instance=customer)

    search_query = request.GET.get("q", "").strip()
    customers = OfflineBooking.objects.select_related("room").order_by("-created_at")
    customers = apply_admin_search(
        customers,
        search_query,
        ["first_name", "last_name", "email", "mobile_number", "room__room_number", "country", "address"],
    )

    context = build_admin_context(
        "offline_bookings",
        form=form,
        data=customers,
        editing_object=customer,
        search_query=search_query,
        form_action_url=reverse("edit_customer", args=[customer.pk]) if customer else reverse("add_customer"),
        submit_label="Update Booking" if customer else "Create Booking",
    )
    return render(request, "admin/AddCustomer.html", context)


@require_POST
@admin_required
def delete_customer(request, id):
    customer = get_object_or_404(OfflineBooking, pk=id)
    customer.delete()
    messages.success(request, "Offline booking deleted successfully.")
    return redirect("add_customer")


# =========================
# EMPLOYEE
# =========================

@admin_required
def add_employee(request, id=None):
    employee = get_object_or_404(Employee, pk=id) if id else None

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            saved_employee = form.save()
            messages.success(
                request,
                f"Employee {saved_employee.first_name} {saved_employee.last_name} saved successfully.",
            )
            return redirect("add_employee")
    else:
        form = EmployeeForm(instance=employee)

    search_query = request.GET.get("q", "").strip()
    employees = Employee.objects.order_by("-created_at")
    employees = apply_admin_search(
        employees,
        search_query,
        ["employee_id", "first_name", "last_name", "email", "mobile_number", "department", "address"],
    )

    context = build_admin_context(
        "employees",
        form=form,
        data=employees,
        editing_object=employee,
        search_query=search_query,
        form_action_url=reverse("edit_employee", args=[employee.pk]) if employee else reverse("add_employee"),
        submit_label="Update Employee" if employee else "Add Employee",
    )
    return render(request, "admin/addemployee.html", context)


@require_POST
@admin_required
def delete_employee(request, id):
    employee = get_object_or_404(Employee, pk=id)
    employee.delete()
    messages.success(request, "Employee deleted successfully.")
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

@admin_required
def add_room(request, id=None):
    room = get_object_or_404(Room, pk=id) if id else None

    if request.method == "POST":
        form = RoomForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            saved_room = form.save()
            messages.success(request, f"Room {saved_room.room_number} saved successfully.")
            return redirect("add_room")
    else:
        form = RoomForm(instance=room)

    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    rooms = Room.objects.order_by("-created_at")
    if status_filter:
        rooms = rooms.filter(status=status_filter)
    rooms = apply_admin_search(rooms, search_query, ["room_number", "room_type", "facility", "status"])

    context = build_admin_context(
        "rooms",
        form=form,
        data=rooms,
        editing_object=room,
        search_query=search_query,
        status_filter=status_filter,
        status_choices=Room.ROOM_STATUS,
        form_action_url=reverse("edit_room", args=[room.pk]) if room else reverse("add_room"),
        submit_label="Update Room" if room else "Add Room",
    )
    return render(request, "admin/AddRoom.html", context)


@require_POST
@admin_required
def delete_room(request, id):
    room = get_object_or_404(Room, pk=id)
    room.delete()
    messages.success(request, "Room deleted successfully.")
    return redirect("add_room")


# =========================
# SALARY
# =========================

@admin_required
def add_salary(request, id=None):
    salary_record = get_object_or_404(Salary.objects.select_related("employee"), pk=id) if id else None

    if request.method == "POST":
        form = SalaryForm(request.POST, instance=salary_record)
        if form.is_valid():
            saved_salary = form.save()
            messages.success(
                request,
                f"Salary for {saved_salary.employee.first_name} {saved_salary.employee.last_name} saved successfully.",
            )
            return redirect("add_salary")
    else:
        form = SalaryForm(instance=salary_record)

    search_query = request.GET.get("q", "").strip()
    salaries = Salary.objects.select_related("employee").order_by("-created_at")
    salaries = apply_admin_search(
        salaries,
        search_query,
        ["employee__employee_id", "employee__first_name", "employee__last_name", "employee__email"],
    )

    context = build_admin_context(
        "salaries",
        form=form,
        data=salaries,
        editing_object=salary_record,
        search_query=search_query,
        form_action_url=reverse("edit_salary", args=[salary_record.pk]) if salary_record else reverse("add_salary"),
        submit_label="Update Salary" if salary_record else "Add Salary",
    )
    return render(request, "admin/AddEmployeeSalary.html", context)


@require_POST
@admin_required
def delete_salary(request, id):
    salary_record = get_object_or_404(Salary, pk=id)
    salary_record.delete()
    messages.success(request, "Salary record deleted successfully.")
    return redirect("add_salary")


# =========================
# USERS
# =========================

@admin_required
def manage_users(request, id=None):
    managed_user = get_object_or_404(Authorregis, pk=id) if id else None
    form_class = AdminUserUpdateForm if managed_user else AdminUserCreateForm

    if request.method == "POST":
        form = form_class(request.POST, instance=managed_user) if managed_user else form_class(request.POST)
        if form.is_valid():
            saved_user = form.save()
            if saved_user.pk == request.user.pk and form.cleaned_data.get("password1"):
                update_session_auth_hash(request, saved_user)
            messages.success(request, f"User {saved_user.email} saved successfully.")
            if saved_user.pk == request.user.pk and not saved_user.is_staff and not saved_user.is_receptionist:
                messages.warning(request, "Your dashboard privileges were removed. Redirected to your user home.")
                return redirect("user_home")
            return redirect("manage_users")
    else:
        form = form_class(instance=managed_user) if managed_user else form_class()

    search_query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    users = Authorregis.objects.annotate(booking_count=Count("onlinebooking", distinct=True)).order_by("-date_joined")
    users = apply_admin_search(users, search_query, ["email", "first_name", "last_name", "phone_number"])
    if role_filter == "staff":
        users = users.filter(is_staff=True, is_receptionist=False)
    elif role_filter == "receptionist":
        users = users.filter(is_receptionist=True)
    elif role_filter == "guest":
        users = users.filter(is_staff=False, is_receptionist=False)
    elif role_filter == "inactive":
        users = users.filter(is_active=False)

    context = build_admin_context(
        "users",
        form=form,
        data=users,
        editing_object=managed_user,
        search_query=search_query,
        role_filter=role_filter,
        form_action_url=reverse("edit_user", args=[managed_user.pk]) if managed_user else reverse("manage_users"),
        submit_label="Update User" if managed_user else "Add User",
    )
    return render(request, "admin/Users.html", context)


@require_POST
@admin_required
def delete_user(request, id):
    managed_user = get_object_or_404(Authorregis, pk=id)

    if managed_user.pk == request.user.pk:
        messages.error(request, "You cannot delete the account you are currently using.")
    elif managed_user.is_superuser and Authorregis.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, "You cannot delete the last superuser account.")
    else:
        managed_user.delete()
        messages.success(request, "User deleted successfully.")

    return redirect("manage_users")


# =========================
# RECEPTIONIST DECORATOR
# =========================

def receptionist_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("author_login")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")
        if not (request.user.is_staff or request.user.is_receptionist):
            messages.error(request, "You do not have permission to access the receptionist dashboard.")
            return redirect("user_home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# =========================
# RECEPTIONIST DASHBOARD
# =========================

@receptionist_required
def receptionist_dashboard(request):
    today = timezone.localdate()
    now = timezone.now()
    
    # Today's check-ins and check-outs
    todays_checkins_online = OnlineBooking.objects.filter(
        check_in=today,
        status__in=['confirmed', 'pending']
    ).select_related('user', 'room').order_by('created_at')
    
    todays_checkins_offline = OfflineBooking.objects.filter(
        check_in=today,
        status__in=['confirmed', 'pending']
    ).select_related('room').order_by('created_at')
    
    todays_checkouts_online = OnlineBooking.objects.filter(
        check_out=today,
        status='checked_in'
    ).select_related('user', 'room').order_by('created_at')
    
    todays_checkouts_offline = OfflineBooking.objects.filter(
        check_out=today,
        status='checked_in'
    ).select_related('room').order_by('created_at')
    
    # Room statistics
    total_rooms = Room.objects.count()
    available_rooms = Room.objects.filter(status='available').count()
    occupied_rooms = Room.objects.filter(status='occupied').count()
    reserved_rooms = Room.objects.filter(status='reserved').count()
    maintenance_rooms = Room.objects.filter(status='maintenance').count()
    
    # Housekeeping tasks
    pending_housekeeping = HousekeepingTask.objects.filter(
        status='pending'
    ).select_related('room').order_by('-priority', 'created_at')[:5]
    
    # Recent activity
    recent_activities = ActivityLog.objects.select_related('user', 'room').order_by('-created_at')[:10]
    
    # Revenue today
    today_payments = Payment.objects.filter(
        paid_at__date=today,
        payment_status='paid'
    ).aggregate(total=Sum('amount'))
    revenue_today = today_payments['total'] or Decimal('0.00')
    
    # Guests in house
    guests_in_house = OnlineBooking.objects.filter(status='checked_in').count() + \
                     OfflineBooking.objects.filter(status='checked_in').count()
    
    # Pending payments
    pending_payments_count = Payment.objects.filter(payment_status='pending').count()
    
    context = build_admin_context(
        "receptionist_dashboard",
        todays_checkins_online=todays_checkins_online,
        todays_checkins_offline=todays_checkins_offline,
        todays_checkouts_online=todays_checkouts_online,
        todays_checkouts_offline=todays_checkouts_offline,
        total_rooms=total_rooms,
        available_rooms=available_rooms,
        occupied_rooms=occupied_rooms,
        reserved_rooms=reserved_rooms,
        maintenance_rooms=maintenance_rooms,
        occupancy_rate=round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0,
        pending_housekeeping=pending_housekeeping,
        recent_activities=recent_activities,
        revenue_today=revenue_today,
        guests_in_house=guests_in_house,
        pending_payments_count=pending_payments_count,
        today=today,
    )
    
    return render(request, "admin/ReceptionistDashboard.html", context)


# =========================
# ROOM STATUS BOARD
# =========================

@receptionist_required
def room_status_board(request):
    rooms = Room.objects.all().order_by('floor', 'room_number')
    
    # Group rooms by floor
    rooms_by_floor = {}
    for room in rooms:
        if room.floor not in rooms_by_floor:
            rooms_by_floor[room.floor] = []
        rooms_by_floor[room.floor].append(room)
    
    context = build_admin_context(
        "room_status_board",
        rooms_by_floor=dict(sorted(rooms_by_floor.items())),
    )
    
    return render(request, "admin/RoomStatusBoard.html", context)


# =========================
# CHECK-IN VIEW
# =========================

@receptionist_required
def check_in_guest(request, booking_type, booking_id):
    if booking_type == 'online':
        booking = get_object_or_404(OnlineBooking, pk=booking_id)
        guest_name = f"{booking.user.first_name} {booking.user.last_name}"
    else:
        booking = get_object_or_404(OfflineBooking, pk=booking_id)
        guest_name = f"{booking.first_name} {booking.last_name}"
    
    if request.method == 'POST':
        # Update booking status
        booking.status = 'checked_in'
        booking.checked_in_at = timezone.now()
        booking.save()
        
        # Update room status
        room = booking.room
        room.status = 'occupied'
        room.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='check_in',
            description=f"Checked in {guest_name} to Room {room.room_number}",
            booking_type=booking_type,
            booking_id=booking_id,
            room=room
        )
        
        messages.success(request, f"{guest_name} checked in successfully to Room {room.room_number}!")
        return redirect('receptionist_dashboard')
    
    context = build_admin_context(
        "check_in",
        booking=booking,
        booking_type=booking_type,
        guest_name=guest_name,
    )
    
    return render(request, "admin/CheckIn.html", context)


# =========================
# CHECK-OUT VIEW
# =========================

@receptionist_required
def check_out_guest(request, booking_type, booking_id):
    if booking_type == 'online':
        booking = get_object_or_404(OnlineBooking, pk=booking_id, status='checked_in')
        guest_name = f"{booking.user.first_name} {booking.user.last_name}"
        guest_email = booking.user.email
    else:
        booking = get_object_or_404(OfflineBooking, pk=booking_id, status='checked_in')
        guest_name = f"{booking.first_name} {booking.last_name}"
        guest_email = booking.email
    
    # Calculate total amount
    total_amount = booking.get_total_amount()
    
    # Check for existing payment
    existing_payment = Payment.objects.filter(
        booking_type=booking_type,
        booking_id=booking_id
    ).first()
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        payment_amount = request.POST.get('payment_amount')
        
        # Update booking status
        booking.status = 'checked_out'
        booking.checked_out_at = timezone.now()
        booking.save()
        
        # Update room status
        room = booking.room
        room.status = 'available'
        room.housekeeping_status = 'dirty'
        room.save()
        
        # Create housekeeping task
        HousekeepingTask.objects.create(
            room=room,
            status='pending',
            priority='high',
            notes=f'Room vacated by {guest_name}',
            created_by=request.user
        )
        
        # Record payment if not already paid
        if not existing_payment or existing_payment.payment_status != 'paid':
            import random
            receipt_number = f"RCP{timezone.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
            
            Payment.objects.create(
                booking_type=booking_type,
                booking_id=booking_id,
                amount=payment_amount or total_amount,
                payment_method=payment_method,
                payment_status='paid',
                receipt_number=receipt_number,
                paid_at=timezone.now(),
                created_by=request.user
            )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='check_out',
            description=f"Checked out {guest_name} from Room {room.room_number}",
            booking_type=booking_type,
            booking_id=booking_id,
            room=room
        )
        
        messages.success(request, f"{guest_name} checked out successfully from Room {room.room_number}!")
        return redirect('receptionist_dashboard')
    
    context = build_admin_context(
        "check_out",
        booking=booking,
        booking_type=booking_type,
        guest_name=guest_name,
        guest_email=guest_email,
        total_amount=total_amount,
        existing_payment=existing_payment,
    )
    
    return render(request, "admin/CheckOut.html", context)


# =========================
# QUICK ROOM STATUS UPDATE (AJAX)
# =========================

@require_POST
@receptionist_required
def update_room_status(request, room_id):
    room = get_object_or_404(Room, pk=room_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Room.ROOM_STATUS):
        room.status = new_status
        room.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='room_status_changed',
            description=f"Changed Room {room.room_number} status to {new_status}",
            room=room
        )
        
        return JsonResponse({'success': True, 'message': f'Room {room.room_number} status updated to {new_status}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)


# =========================
# HOUSEKEEPING MANAGEMENT
# =========================

@receptionist_required
def housekeeping_board(request):
    tasks = HousekeepingTask.objects.select_related('room', 'assigned_to', 'created_by').order_by('-priority', 'created_at')
    
    # Filter options
    status_filter = request.GET.get('status', 'all')
    if status_filter and status_filter != 'all':
        tasks = tasks.filter(status=status_filter)
    
    context = build_admin_context(
        "housekeeping_board",
        tasks=tasks,
        status_filter=status_filter,
    )
    
    return render(request, "admin/HousekeepingBoard.html", context)


@require_POST
@receptionist_required
def update_housekeeping_task(request, task_id):
    task = get_object_or_404(HousekeepingTask, pk=task_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(HousekeepingTask.TASK_STATUS):
        task.status = new_status
        
        if new_status == 'in_progress' and not task.started_at:
            task.started_at = timezone.now()
        elif new_status == 'completed':
            task.completed_at = timezone.now()
            
            # Update room status
            room = task.room
            room.housekeeping_status = 'clean'
            room.last_cleaned = timezone.now()
            room.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='housekeeping_completed',
                description=f"Completed housekeeping for Room {room.room_number}",
                room=room
            )
        
        task.save()
        messages.success(request, f"Housekeeping task for Room {task.room.room_number} updated to {new_status}")
    
    return redirect('housekeeping_board')


# =========================
# GUEST SEARCH
# =========================

@receptionist_required
def guest_search(request):
    query = request.GET.get('q', '').strip()
    results = {
        'online_bookings': [],
        'offline_bookings': [],
        'rooms': []
    }
    
    if query:
        # Search online bookings
        results['online_bookings'] = OnlineBooking.objects.filter(
            Q(user__email__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(room__room_number__icontains=query)
        ).select_related('user', 'room')[:20]
        
        # Search offline bookings
        results['offline_bookings'] = OfflineBooking.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(mobile_number__icontains=query) |
            Q(room__room_number__icontains=query)
        ).select_related('room')[:20]
        
        # Search rooms
        results['rooms'] = Room.objects.filter(
            Q(room_number__icontains=query) |
            Q(room_type__icontains=query) |
            Q(floor__icontains=query)
        )[:20]
    
    context = build_admin_context(
        "guest_search",
        query=query,
        results=results,
    )
    
    return render(request, "admin/GuestSearch.html", context)


# =========================
# PAYMENT PROCESSING
# =========================

@receptionist_required
def process_payment(request, booking_type, booking_id):
    if booking_type == 'online':
        booking = get_object_or_404(OnlineBooking, pk=booking_id)
        guest_name = f"{booking.user.first_name} {booking.user.last_name}"
    else:
        booking = get_object_or_404(OfflineBooking, pk=booking_id)
        guest_name = f"{booking.first_name} {booking.last_name}"
    
    total_amount = booking.get_total_amount()
    
    # Get existing payments
    existing_payments = Payment.objects.filter(
        booking_type=booking_type,
        booking_id=booking_id
    ).order_by('-created_at')
    
    total_paid = sum(p.amount for p in existing_payments if p.payment_status == 'paid')
    balance = total_amount - total_paid
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        payment_amount = Decimal(request.POST.get('amount', '0'))
        
        import random
        receipt_number = f"RCP{timezone.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
        
        Payment.objects.create(
            booking_type=booking_type,
            booking_id=booking_id,
            amount=payment_amount,
            payment_method=payment_method,
            payment_status='paid',
            receipt_number=receipt_number,
            paid_at=timezone.now(),
            created_by=request.user
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='payment_received',
            description=f"Received payment of {format_naira(payment_amount)} from {guest_name} via {payment_method}",
            booking_type=booking_type,
            booking_id=booking_id,
            room=booking.room
        )
        
        messages.success(request, f"Payment of {format_naira(payment_amount)} received successfully!")
        return redirect('receptionist_dashboard')
    
    context = build_admin_context(
        "process_payment",
        booking=booking,
        booking_type=booking_type,
        guest_name=guest_name,
        total_amount=total_amount,
        total_paid=total_paid,
        balance=balance,
        existing_payments=existing_payments,
    )
    
    return render(request, "admin/PaymentProcessing.html", context)


# =========================
# PAYSTACK PAYMENT INTEGRATION
# =========================

def generate_payment_reference():
    """Generate unique payment reference"""
    return f"HMS-{uuid.uuid4().hex[:12].upper()}"


@login_required
def initiate_payment(request):
    """Initialize Paystack payment for a booking"""
    if request.method != 'POST':
        return redirect('online_booking')
    
    # Get booking details from session
    booking_data = request.session.get('pending_booking')
    if not booking_data:
        messages.error(request, "No pending booking found. Please start booking process again.")
        return redirect('online_booking')
    
    try:
        room = Room.objects.get(id=booking_data['room_id'])
        check_in = datetime.strptime(booking_data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(booking_data['check_out'], '%Y-%m-%d').date()
        
        # Calculate amount
        nights = (check_out - check_in).days
        amount = int(room.price * nights * 100)  # Convert to kobo (Paystack uses kobo)
        
        # Generate payment reference
        reference = generate_payment_reference()
        
        # Initialize Paystack transaction
        paystack = PaystackClient(secret_key=settings.PAYSTACK_SECRET_KEY)
        response = paystack.transactions.initialize(
            email=request.user.email,
            amount=amount,
            reference=reference,
            callback_url=request.build_absolute_uri(reverse('payment_callback'))
        )
        
        if response.status:
            # Store payment reference in session
            request.session['payment_reference'] = reference
            request.session['payment_amount'] = float(room.price * nights)
            
            # Create pending payment record
            Payment.objects.create(
                booking_type='online',
                booking_id=0,  # Will be updated after booking creation
                amount=room.price * nights,
                payment_method='paystack',
                payment_status='pending',
                receipt_number=reference,
                paystack_reference=reference,
                paystack_access_code=response.data.access_code,
                created_by=request.user
            )
            
            # Redirect to Paystack checkout
            return redirect(response.data.authorization_url)
        else:
            messages.error(request, "Failed to initialize payment. Please try again.")
            return redirect('online_booking')
            
    except Exception as e:
        logger.error(f"Payment initialization error: {str(e)}")
        messages.error(request, "An error occurred while processing your payment.")
        return redirect('online_booking')


@login_required
def payment_callback(request):
    """Handle Paystack payment callback"""
    reference = request.GET.get('reference')
    
    if not reference:
        messages.error(request, "Invalid payment reference.")
        return redirect('user_home')
    
    try:
        # Verify payment with Paystack
        paystack = PaystackClient(secret_key=settings.PAYSTACK_SECRET_KEY)
        response = paystack.transactions.verify(reference=reference)
        
        if response.status and response.data.status == 'success':
            # Get pending booking data
            booking_data = request.session.get('pending_booking')
            if not booking_data:
                messages.error(request, "Booking data not found.")
                return redirect('user_home')
            
            # Create the booking
            room = Room.objects.get(id=booking_data['room_id'])
            booking = OnlineBooking.objects.create(
                user=request.user,
                room=room,
                check_in=booking_data['check_in'],
                check_out=booking_data['check_out'],
                adults=booking_data.get('adults', 1),
                children=booking_data.get('children', 0),
                city=booking_data.get('city', ''),
                country=booking_data.get('country', ''),
                address=booking_data.get('address', ''),
                status='confirmed'
            )
            
            # Update payment record
            payment = Payment.objects.get(paystack_reference=reference)
            payment.booking_id = booking.id
            payment.payment_status = 'paid'
            payment.paid_at = timezone.now()
            payment.paystack_response = response.raw
            payment.save()
            
            # Update room status
            room.status = 'reserved'
            room.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='booking_created',
                description=f"Booking created with payment via Paystack for Room {room.room_number}",
                booking_type='online',
                booking_id=booking.id,
                room=room
            )
            
            ActivityLog.objects.create(
                user=request.user,
                action_type='payment_received',
                description=f"Payment of ${payment.amount} received via Paystack",
                booking_type='online',
                booking_id=booking.id,
                room=room
            )
            
            # Clear session data
            if 'pending_booking' in request.session:
                del request.session['pending_booking']
            if 'payment_reference' in request.session:
                del request.session['payment_reference']
            if 'payment_amount' in request.session:
                del request.session['payment_amount']
            
            messages.success(request, f"Payment successful! Your booking for Room {room.room_number} has been confirmed.")
            return redirect('payment_success', booking_id=booking.id)
        else:
            # Payment failed
            payment = Payment.objects.filter(paystack_reference=reference).first()
            if payment:
                payment.payment_status = 'failed'
                payment.paystack_response = response.raw
                payment.save()
            
            messages.error(request, "Payment verification failed. Please try again.")
            return redirect('payment_failed')
            
    except Exception as e:
        logger.error(f"Payment callback error: {str(e)}")
        messages.error(request, "An error occurred while verifying your payment.")
        return redirect('user_home')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhook notifications"""
    try:
        payload = json.loads(request.body)
        
        # Verify webhook signature (recommended for production)
        # signature = request.headers.get('x-paystack-signature')
        
        if payload['event'] == 'charge.success':
            reference = payload['data']['reference']
            
            # Update payment status
            payment = Payment.objects.filter(paystack_reference=reference).first()
            if payment and payment.payment_status == 'pending':
                payment.payment_status = 'paid'
                payment.paid_at = timezone.now()
                payment.paystack_response = payload['data']
                payment.save()
                
                # Update booking status if exists
                if payment.booking_id:
                    if payment.booking_type == 'online':
                        booking = OnlineBooking.objects.filter(id=payment.booking_id).first()
                    else:
                        booking = OfflineBooking.objects.filter(id=payment.booking_id).first()
                    
                    if booking:
                        booking.status = 'confirmed'
                        booking.save()
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def payment_success(request, booking_id):
    """Payment success page"""
    booking = get_object_or_404(OnlineBooking, id=booking_id, user=request.user)
    payment = Payment.objects.filter(booking_type='online', booking_id=booking_id, payment_status='paid').first()
    
    context = {
        'booking': booking,
        'payment': payment,
    }
    
    return render(request, 'payment_success.html', context)


@login_required
def payment_failed(request):
    """Payment failed page"""
    return render(request, 'payment_failed.html')


@login_required
def booking_payment_page(request):
    """Display booking summary and payment button"""
    booking_data = request.session.get('pending_booking')
    if not booking_data:
        messages.error(request, "No pending booking found.")
        return redirect('online_booking')
    
    try:
        room = Room.objects.get(id=booking_data['room_id'])
        check_in = datetime.strptime(booking_data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(booking_data['check_out'], '%Y-%m-%d').date()
        
        nights = (check_out - check_in).days
        total_amount = room.price * nights
        
        context = {
            'room': room,
            'check_in': check_in,
            'check_out': check_out,
            'adults': booking_data.get('adults', 1),
            'children': booking_data.get('children', 0),
            'nights': nights,
            'total_amount': total_amount,
            'booking_data': booking_data,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        }
        
        return render(request, 'booking_payment.html', context)
        
    except Room.DoesNotExist:
        messages.error(request, "Room not found.")
        return redirect('online_booking')
