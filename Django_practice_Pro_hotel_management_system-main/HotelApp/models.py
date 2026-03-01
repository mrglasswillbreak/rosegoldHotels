from django.contrib.auth.models import AbstractUser
from django.db import models


# =========================
# CUSTOM USER MODEL
# =========================
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()   # 👈 VERY IMPORTANT

    def __str__(self):
        return self.email


# =========================
# ROOM MODEL
# =========================

from django.db import models

class Room(models.Model):
    ROOM_STATUS = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
    ]

    ROOM_TYPES = [
        ('single', 'Single'),
        ('double', 'Double'),
        ('suite', 'Suite'),
    ]

    room_number = models.CharField(max_length=50, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    floor = models.IntegerField()
    facility = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='rooms/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=ROOM_STATUS, default='available')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type})"

# =========================
# ONLINE BOOKING
# =========================

class OnlineBooking(models.Model):
    user = models.ForeignKey(Authorregis, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    check_in = models.DateField()
    check_out = models.DateField()

    adults = models.IntegerField()
    children = models.IntegerField()

    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    address = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.room.room_number}"


# =========================
# OFFLINE BOOKING
# =========================

class OfflineBooking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    mobile_number = models.CharField(max_length=15)

    check_in = models.DateField()
    check_out = models.DateField()

    adults = models.IntegerField()
    children = models.IntegerField()

    country = models.CharField(max_length=100)
    address = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


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
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    salary = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.first_name} Salary"