from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# =========================
# CUSTOM USER MODEL
# =========================


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be provided")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, password, **extra_fields)

class Authorregis(AbstractUser):
    username = None  # remove username
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    theme = models.CharField(max_length=10, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')
    is_receptionist = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()   # 👈 VERY IMPORTANT

    def __str__(self):
        return self.email
    
    def get_role(self):
        if self.is_superuser:
            return 'Super Admin'
        elif self.is_staff and not self.is_receptionist:
            return 'Admin'
        elif self.is_receptionist:
            return 'Receptionist'
        return 'Guest'


# =========================
# ROOM MODEL
# =========================

class Room(models.Model):
    ROOM_STATUS = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
        ('reserved', 'Reserved'),
    ]

    ROOM_TYPES = [
        ('single', 'Single'),
        ('double', 'Double'),
        ('suite', 'Suite'),
    ]

    HOUSEKEEPING_STATUS = [
        ('clean', 'Clean'),
        ('dirty', 'Dirty'),
        ('in_progress', 'In Progress'),
    ]

    room_number = models.CharField(max_length=50, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, db_index=True)
    floor = models.IntegerField()
    facility = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='rooms/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=ROOM_STATUS, default='available', db_index=True)
    housekeeping_status = models.CharField(max_length=20, choices=HOUSEKEEPING_STATUS, default='clean')
    last_cleaned = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type})"

# =========================
# ONLINE BOOKING
# =========================

class OnlineBooking(models.Model):
    BOOKING_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(Authorregis, on_delete=models.CASCADE, db_index=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, db_index=True)

    check_in = models.DateField(db_index=True)
    check_out = models.DateField(db_index=True)

    adults = models.IntegerField()
    children = models.IntegerField()

    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='confirmed', db_index=True)
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checked_out_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_vip = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.room.room_number}"
    
    def get_total_nights(self):
        return (self.check_out - self.check_in).days
    
    def get_total_amount(self):
        return self.get_total_nights() * self.room.price


# =========================
# OFFLINE BOOKING
# =========================

class OfflineBooking(models.Model):
    BOOKING_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, db_index=True)

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    mobile_number = models.CharField(max_length=15)

    check_in = models.DateField(db_index=True)
    check_out = models.DateField(db_index=True)

    adults = models.IntegerField()
    children = models.IntegerField()

    country = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='confirmed', db_index=True)
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checked_out_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_vip = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_total_nights(self):
        return (self.check_out - self.check_in).days
    
    def get_total_amount(self):
        return self.get_total_nights() * self.room.price


# =========================
# EMPLOYEE
# =========================

class Employee(models.Model):
    employee_id = models.CharField(max_length=50, primary_key=True)

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15, unique=True)

    joining_date = models.DateField()
    date_of_birth = models.DateField()

    department = models.CharField(max_length=100)
    gender = models.CharField(max_length=20)
    blood_group = models.CharField(max_length=10)
    education = models.CharField(max_length=100)

    guardian = models.CharField(max_length=150)
    guardian_number = models.CharField(max_length=15)

    image = models.ImageField(upload_to='employees/')
    address = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# =========================
# SALARY
# =========================

class Salary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_index=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.first_name} Salary"


# =========================
# PAYMENT MODEL
# =========================

class Payment(models.Model):
    PAYMENT_METHOD = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('paystack', 'Paystack'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]

    booking_type = models.CharField(max_length=20, choices=[('online', 'Online'), ('offline', 'Offline')])
    booking_id = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending', db_index=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(Authorregis, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments_created', db_index=True)
    notes = models.TextField(blank=True, null=True)
    
    # Paystack specific fields
    paystack_reference = models.CharField(max_length=100, blank=True, null=True, unique=True, db_index=True)
    paystack_access_code = models.CharField(max_length=100, blank=True, null=True)
    paystack_response = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.receipt_number} - {self.amount}"

    class Meta:
        ordering = ['-created_at']


# =========================
# HOUSEKEEPING TASK MODEL
# =========================

class HousekeepingTask(models.Model):
    TASK_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    TASK_PRIORITY = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='housekeeping_tasks', db_index=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='pending', db_index=True)
    priority = models.CharField(max_length=20, choices=TASK_PRIORITY, default='medium', db_index=True)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks', db_index=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(Authorregis, on_delete=models.SET_NULL, null=True, related_name='tasks_created', db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Housekeeping {self.room.room_number} - {self.status}"

    class Meta:
        ordering = ['-priority', '-created_at']


# =========================
# ACTIVITY LOG MODEL
# =========================

class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
        ('booking_created', 'Booking Created'),
        ('booking_modified', 'Booking Modified'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_received', 'Payment Received'),
        ('room_status_changed', 'Room Status Changed'),
        ('housekeeping_assigned', 'Housekeeping Assigned'),
        ('housekeeping_completed', 'Housekeeping Completed'),
    ]

    user = models.ForeignKey(Authorregis, on_delete=models.SET_NULL, null=True, related_name='activities', db_index=True)
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES, db_index=True)
    description = models.TextField()
    
    booking_type = models.CharField(max_length=20, blank=True, null=True)
    booking_id = models.IntegerField(blank=True, null=True, db_index=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs', db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.action_type} by {self.user.email if self.user else 'System'} at {self.created_at}"

    class Meta:
        ordering = ['-created_at']
