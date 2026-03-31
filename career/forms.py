from django import forms

from .models import CareerPost


class CareerPostForm(forms.ModelForm):
    class Meta:
        model = CareerPost
        fields = [
            "post_type",
            "full_name",
            "title",
            "description",
            "contact_person_name",
            "contact_person_number",
            "email",
            "phone",
            "location",
            "company_name",
            "current_company_name",
            "responsibilities",
            "skills",
            "current_ctc_lpa",
            "expected_lpa",
            "package_lpa",
            "experience_years",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            css_class = "form-control"
            if field_name == "description":
                field.widget.attrs.update({"rows": 5})
            if field_name in {"responsibilities"}:
                field.widget = forms.Textarea(attrs={"rows": 3})
            field.widget.attrs["class"] = css_class

        self.fields["company_name"].required = False
        self.fields["current_company_name"].required = False
        self.fields["skills"].required = False
        self.fields["responsibilities"].required = False
        self.fields["current_ctc_lpa"].required = False
        self.fields["expected_lpa"].required = False
        self.fields["package_lpa"].required = False
        self.fields["experience_years"].required = False
