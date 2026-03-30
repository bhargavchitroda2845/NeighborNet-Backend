from django import forms

from member.models import Member

from .models import Donation, DonationSubject


class DonationForm(forms.ModelForm):
    member_no = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter member number"}),
    )

    class Meta:
        model = Donation
        fields = [
            "member_no",
            "name",
            "address",
            "city",
            "state",
            "country",
            "subject",
            "amount",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "subject": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = False
        self.fields["address"].required = False
        self.fields["city"].required = False
        self.fields["state"].required = False
        self.fields["country"].required = False
        self.fields["subject"].queryset = DonationSubject.objects.filter(is_active=True).order_by("-is_default", "name")
        if not self.is_bound and not self.initial.get("subject"):
            default_subject = self.fields["subject"].queryset.filter(is_default=True).first()
            if default_subject:
                self.initial["subject"] = default_subject.pk

    def clean_member_no(self):
        value = self.cleaned_data.get("member_no")
        if value and not Member.objects.filter(
            member_no=value,
            approval_status="Approved",
            status="Active",
        ).exists():
            raise forms.ValidationError("Only approved active member number is allowed.")
        return value
