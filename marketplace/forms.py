from django import forms
from .models import BnsModel


class BnsModelForm(forms.ModelForm):
    # Add status field for handling sold status
    status = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = BnsModel
        fields = [
            "title",
            "slug",
            "desc",
            "image",
            "listing_type",
            "area",
            "contact",
            "min_price",
            "max_price",
            "price",
            "bidding_enabled",
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Required fields from spec.
        self.fields["title"].required = True
        self.fields["desc"].required = True
        self.fields["listing_type"].required = True
        self.fields["contact"].required = True

        # Optional fields from spec.
        self.fields["slug"].required = False
        self.fields["image"].required = False
        self.fields["area"].required = False
        self.fields["min_price"].required = False
        self.fields["max_price"].required = False
        self.fields["price"].required = False

    def clean(self):
        cleaned = super().clean()
        min_price = cleaned.get("min_price")
        max_price = cleaned.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            self.add_error("max_price", "Max price must be greater than or equal to min price.")
        return cleaned
