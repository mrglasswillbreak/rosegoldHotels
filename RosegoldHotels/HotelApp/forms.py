from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import validate_email as django_validate_email, FileExtensionValidator

from . import models
from .models import Authorregis


# =========================
# FILE UPLOAD VALIDATORS
# =========================

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
MAX_IMAGE_SIZE_MB = 5


def validate_image_file(image):
    """Validate image file extension and size."""
    if image:
        # Check file extension
        ext_validator = FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
        ext_validator(image)
        
        # Check file size (5MB max)
        if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(f"Image file too large. Maximum size is {MAX_IMAGE_SIZE_MB}MB.")
    return image


def booking_window_has_conflict(room, check_in, check_out, online_instance=None, offline_instance=None):
    if not room or not check_in or not check_out:
        return False

    online_conflicts = models.OnlineBooking.objects.filter(
        room=room,
        check_in__lt=check_out,
        check_out__gt=check_in,
    )
    offline_conflicts = models.OfflineBooking.objects.filter(
        room=room,
        check_in__lt=check_out,
        check_out__gt=check_in,
    )

    if online_instance and online_instance.pk:
        online_conflicts = online_conflicts.exclude(pk=online_instance.pk)
    if offline_instance and offline_instance.pk:
        offline_conflicts = offline_conflicts.exclude(pk=offline_instance.pk)

    return online_conflicts.exists() or offline_conflicts.exists()


class StyledFormMixin:
    textarea_rows = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "admin-checkbox"
                continue

            css_classes = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{css_classes} form-control".strip()

            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", self.textarea_rows)

            if isinstance(widget, forms.DateInput):
                widget.input_type = "date"

            if isinstance(widget, forms.NumberInput):
                widget.attrs.setdefault("step", "1")

            widget.attrs.setdefault("placeholder", field.label)


class BookingValidationMixin:
    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get("room")
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")
        adults = cleaned_data.get("adults")
        children = cleaned_data.get("children")

        if check_in and check_out and check_in >= check_out:
            self.add_error("check_out", "Check-out must be after check-in.")

        if adults is not None and adults <= 0:
            self.add_error("adults", "At least one adult is required.")

        if children is not None and children < 0:
            self.add_error("children", "Children cannot be negative.")

        if room and check_in and check_out and not self.errors:
            online_instance = self.instance if isinstance(self.instance, models.OnlineBooking) else None
            offline_instance = self.instance if isinstance(self.instance, models.OfflineBooking) else None
            if booking_window_has_conflict(
                room,
                check_in,
                check_out,
                online_instance=online_instance,
                offline_instance=offline_instance,
            ):
                raise forms.ValidationError("This room is already booked for the selected dates.")

        return cleaned_data


class OnlineBookingForm(BookingValidationMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = models.OnlineBooking
        fields = "__all__"
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "date"}),
            "check_out": forms.DateInput(attrs={"type": "date"}),
            "adults": forms.NumberInput(attrs={"min": 1}),
            "children": forms.NumberInput(attrs={"min": 0}),
            "address": forms.Textarea(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = Authorregis.objects.order_by("email")
        self.fields["room"].queryset = models.Room.objects.order_by("room_number")


class OfflineBookingForm(BookingValidationMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = models.OfflineBooking
        fields = "__all__"
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "date"}),
            "check_out": forms.DateInput(attrs={"type": "date"}),
            "adults": forms.NumberInput(attrs={"min": 1}),
            "children": forms.NumberInput(attrs={"min": 0}),
            "address": forms.Textarea(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = models.Room.objects.order_by("room_number")


class EmployeeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = models.Employee
        fields = "__all__"
        widgets = {
            "joining_date": forms.DateInput(attrs={"type": "date"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }
    
    def clean_image(self):
        return validate_image_file(self.cleaned_data.get('image'))


class RoomForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = models.Room
        fields = "__all__"
        widgets = {
            "facility": forms.Textarea(),
            "price": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "floor": forms.NumberInput(attrs={"min": 0}),
        }
    
    def clean_image(self):
        return validate_image_file(self.cleaned_data.get('image'))


class SalaryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = models.Salary
        fields = "__all__"
        widgets = {
            "salary": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = models.Employee.objects.order_by("first_name", "last_name")


class AdminUserCreateForm(StyledFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )

    class Meta:
        model = Authorregis
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "theme",
            "is_active",
            "is_staff",
            "is_receptionist",
            "is_superuser",
        ]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if password1 and len(password1) < 8:
            self.add_error("password1", "Password must be at least 8 characters.")
        if cleaned_data.get("is_superuser") and not cleaned_data.get("is_staff"):
            self.add_error("is_staff", "Superusers must also be staff users.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminUserUpdateForm(StyledFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="New password",
        strip=False,
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to keep the current password.",
    )
    password2 = forms.CharField(
        label="Confirm new password",
        strip=False,
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )

    class Meta:
        model = Authorregis
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "theme",
            "is_active",
            "is_staff",
            "is_receptionist",
            "is_superuser",
        ]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "Passwords do not match.")
            elif len(password1) < 8:
                self.add_error("password1", "Password must be at least 8 characters.")
        if cleaned_data.get("is_superuser") and not cleaned_data.get("is_staff"):
            self.add_error("is_staff", "Superusers must also be staff users.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get("password1")
        if password1:
            user.set_password(password1)
        if commit:
            user.save()
        return user


class AuthorRegisterForm(StyledFormMixin, UserCreationForm):
    accept_terms = forms.BooleanField(
        label="I agree to the Terms & Conditions",
        required=True,
        error_messages={
            "required": "You must accept the Terms & Conditions to register.",
        },
    )

    class Meta:
        model = Authorregis
        fields = ["first_name", "last_name", "email", "phone_number"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"].label = "First Name"
        self.fields["last_name"].label = "Last Name"
        self.fields["phone_number"].label = "Phone Number"
        self.fields["email"].label = "Email"

        for field_name in ["first_name", "last_name", "phone_number", "email"]:
            self.fields[field_name].required = True

        self.fields["first_name"].widget.attrs["placeholder"] = "First Name *"
        self.fields["last_name"].widget.attrs["placeholder"] = "Last Name *"
        self.fields["email"].widget.attrs["placeholder"] = "Email *"
        self.fields["phone_number"].widget.attrs["placeholder"] = "Phone Number *"
        self.fields["password1"].widget.attrs["placeholder"] = "Password *"
        self.fields["password2"].widget.attrs["placeholder"] = "Confirm Password *"

        self.fields["accept_terms"].widget.attrs["class"] = "form-check-input"
        self.fields["accept_terms"].widget.attrs["id"] = "terms"

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        django_validate_email(email)

        if Authorregis.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already registered.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_active = False
        if commit:
            user.save()
        return user
