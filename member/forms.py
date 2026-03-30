from django import forms
from django.db.models import Q
from .models import City, Country, Member, MemberDetail, State
import re

class MemberForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].queryset = Country.objects.all().order_by("name")
        self.fields["state"].queryset = State.objects.none()
        self.fields["city"].queryset = City.objects.none()

        country_id = self.data.get("country")
        state_id = self.data.get("state")

        if not country_id and self.instance and self.instance.country_id:
            country_id = self.instance.country_id
        if not state_id and self.instance and self.instance.state_id:
            state_id = self.instance.state_id

        if country_id:
            self.fields["state"].queryset = State.objects.filter(country_id=country_id).order_by("name")
            self.fields["city"].queryset = City.objects.filter(country_id=country_id).order_by("name")

        if state_id:
            self.fields["city"].queryset = self.fields["city"].queryset.filter(
                Q(state_id=state_id) | Q(state__isnull=True)
            )

    class Meta:
        model = Member
        fields = [
            "first_name",
            "middle_name",
            "surname",
            "phone_no",
            "date_of_birth",
            # "age", # Removing manual age input
            "gender",
            "occupation",
            "email_id",
            "country",
            "state",
            "city",
            "residential_address",
            "profile_image",
            "marital_status",
            "education",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "middle_name": forms.TextInput(attrs={"class": "form-control"}),
            "surname": forms.TextInput(attrs={"class": "form-control"}),
            "phone_no": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "occupation": forms.TextInput(attrs={"class": "form-control"}),
            "email_id": forms.EmailInput(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-control"}),
            "state": forms.Select(attrs={"class": "form-control"}),
            "city": forms.Select(attrs={"class": "form-control"}),
            "residential_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "profile_image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "marital_status": forms.Select(attrs={"class": "form-control"}),
            "education": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get("country")
        state = cleaned_data.get("state")
        city = cleaned_data.get("city")

        if state and country and state.country_id != country.id:
            self.add_error("state", "Selected state does not belong to selected country.")

        if city and country and city.country_id != country.id:
            self.add_error("city", "Selected city does not belong to selected country.")

        if city and state and city.state_id and city.state_id != state.id:
            self.add_error("city", "Selected city does not belong to selected state.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        from datetime import date as _date
        if instance.date_of_birth:
            today = _date.today()
            dob = instance.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            instance.age = age
        else:
            instance.age = 0
            
        if commit:
            instance.save()
        return instance

class MemberCreateForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "first_name",
            "middle_name",
            "surname",
            "phone_no",
            "email_id",
            "gender",
            "date_of_birth",
            "occupation",
            "country",
            "state",
            "city",
            "residential_address",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["middle_name"].required = False
        self.fields["email_id"].required = True
        self.fields["date_of_birth"].required = False
        self.fields["occupation"].required = False
        self.fields["country"].required = True
        self.fields["state"].required = True
        self.fields["city"].required = False
        self.fields["residential_address"].required = True

        self.fields["country"].queryset = Country.objects.all().order_by("name")
        self.fields["state"].queryset = State.objects.none()
        self.fields["city"].queryset = City.objects.none()

        country_id = self.data.get("country") or self.initial.get("country")
        state_id = self.data.get("state") or self.initial.get("state")

        if country_id:
            self.fields["state"].queryset = State.objects.filter(country_id=country_id).order_by("name")
            self.fields["city"].queryset = City.objects.filter(country_id=country_id).order_by("name")

        if state_id:
            self.fields["city"].queryset = self.fields["city"].queryset.filter(
                Q(state_id=state_id) | Q(state__isnull=True)
            )

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get("country")
        state = cleaned_data.get("state")
        city = cleaned_data.get("city")

        if state and country and state.country_id != country.id:
            self.add_error("state", "Selected state does not belong to selected country.")

        if city and country and city.country_id != country.id:
            self.add_error("city", "Selected city does not belong to selected country.")

        if city and state and city.state_id and city.state_id != state.id:
            self.add_error("city", "Selected city does not belong to selected state.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        from datetime import date as _date
        if instance.date_of_birth:
            today = _date.today()
            dob = instance.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            instance.age = age
        else:
            instance.age = 0
            
        if commit:
            instance.save()
        return instance

class MemberDetailForm(forms.ModelForm):
    class Meta:
        model = MemberDetail
        fields = [
            "first_name",
            "middle_name",
            "surname",
            "date_of_birth",
            # "age", # Removing manual age input
            "gender",
            "occupation",
            "email_id",
            "profile_image",
            "marital_status",
            "education",
            # Matrimonial fields
            "show_on_matrimonial",
            "is_matrimonial_public",
            "matrimonial_visibility",
            "relation_with_member",
            "height",
            "blood_group",
            "gotra",
            "manglik",
            "annual_income",
            "about_matrimonial",
            "matrimonial_photo",
            # Extended matrimonial fields
            "diet",
            "addictions",
            "father_name",
            "mother_name",
            "family_type",
            "siblings",
            "contact_phone",
            "full_bio",
            "hobbies",
            "partner_preference",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "middle_name": forms.TextInput(attrs={"class": "form-control"}),
            "surname": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "occupation": forms.TextInput(attrs={"class": "form-control"}),
            "email_id": forms.EmailInput(attrs={"class": "form-control"}),
            "profile_image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "marital_status": forms.Select(attrs={"class": "form-control"}),
            "education": forms.TextInput(attrs={"class": "form-control"}),
            "show_on_matrimonial": forms.CheckboxInput(attrs={"id": "id_show_on_matrimonial", "class": "custom-control-input"}),
            "is_matrimonial_public": forms.CheckboxInput(attrs={"id": "id_is_matrimonial_public", "class": "custom-control-input"}),
            "matrimonial_visibility": forms.Select(attrs={"id": "id_matrimonial_visibility", "class": "form-control"}),
            "relation_with_member": forms.Select(attrs={"class": "form-control"}),
            "height": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 5'7\""}),
            "blood_group": forms.Select(attrs={"class": "form-control"}),
            "gotra": forms.TextInput(attrs={"class": "form-control"}),
            "manglik": forms.Select(attrs={"class": "form-control"}),
            "annual_income": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 5-7 LPA"}),
            "about_matrimonial": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "matrimonial_photo": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            # Extended
            "diet": forms.Select(attrs={"class": "form-control"}),
            "father_name": forms.TextInput(attrs={"class": "form-control"}),
            "mother_name": forms.TextInput(attrs={"class": "form-control"}),
            "family_type": forms.Select(attrs={"class": "form-control"}),
            "siblings": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 1 younger sister (married)"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Public contact number"}),
            "full_bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "hobbies": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Travel, cricket, fitness"}),
            "partner_preference": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    addictions = forms.MultipleChoiceField(
        choices=[
            ("Tobacco", "Tobacco"),
            ("Smoke", "Smoke"),
            ("Drink", "Drink"),
            ("None", "None"),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['about_matrimonial'].label = "About Me"
        self.fields['contact_phone'].label = "Parent Contact Number"
        
        # Load string into a list for the MultipleChoiceField
        if self.instance and self.instance.pk and self.instance.addictions:
            # If the database has "Smoke,Drink", we split into ["Smoke", "Drink"]
            self.initial['addictions'] = [x.strip() for x in self.instance.addictions.split(',') if x.strip()]

    def clean(self):
        from datetime import date as _date
        cleaned_data = super().clean()
        show = cleaned_data.get("show_on_matrimonial")
        dob = cleaned_data.get("date_of_birth")

        if show:
            # Age 18+ validation
            if not dob:
                self.add_error("date_of_birth", "Date of birth is required for matrimonial listing.")
            else:
                today = _date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                if age < 18:
                    self.add_error("date_of_birth", "Person must be 18 or older to be listed on matrimonial.")
            
            # Marital Status validation
            marital = cleaned_data.get("marital_status")
            if marital and marital.lower() == "married":
                self.add_error("marital_status", "Married persons cannot be listed on matrimonial.")

            # Required matrimonial fields
            required_matrimonial = {
                "relation_with_member": "Relation with primary member",
                "gender": "Gender",
                "marital_status": "Marital Status",
            }
            for field, label in required_matrimonial.items():
                if not cleaned_data.get(field):
                    self.add_error(field, f"{label} is required for matrimonial listing.")

            if not cleaned_data.get("contact_phone"):
                self.add_error("contact_phone", "Parent Contact Number is required for matrimonial listing.")
            if not cleaned_data.get("full_bio") and not cleaned_data.get("about_matrimonial"):
                self.add_error("full_bio", "A bio is required for matrimonial listing.")
                
        # Convert list of addictions to comma separated string
        addictions_list = cleaned_data.get('addictions')
        if addictions_list:
            cleaned_data['addictions'] = ', '.join(addictions_list)
        else:
            cleaned_data['addictions'] = ''

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        from datetime import date as _date
        if instance.date_of_birth:
            today = _date.today()
            dob = instance.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            instance.age = age
        else:
            instance.age = 0
            
        if commit:
            instance.save()
        return instance
