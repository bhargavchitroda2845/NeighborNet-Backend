(function($) {
    "use strict";

    // Override Django admin autocomplete initialization to always include
    // required query keys for /admin/autocomplete/.
    function initAutocomplete($element, options) {
        var settings = $.extend(true, {
            ajax: {
                data: function(params) {
                    return {
                        term: params.term || "",
                        page: params.page || 1,
                        app_label: $element.attr("data-app-label"),
                        model_name: $element.attr("data-model-name"),
                        field_name: $element.attr("data-field-name")
                    };
                },
                delay: 250
            },
            minimumInputLength: 1,
            width: "resolve",
            allowClear: true
        }, options);

        // If required metadata is missing, do not initialize AJAX autocomplete.
        if (
            !$element.attr("data-app-label") ||
            !$element.attr("data-model-name") ||
            !$element.attr("data-field-name")
        ) {
            return;
        }

        $element.select2(settings);
    }

    $.fn.djangoAdminSelect2 = function(options) {
        this.each(function() {
            initAutocomplete($(this), options);
        });
        return this;
    };

    $(function() {
        $(".admin-autocomplete").not("[name*=__prefix__]").djangoAdminSelect2();
    });

    $(document).on("formset:added", function(event, $newFormset) {
        $newFormset.find(".admin-autocomplete").djangoAdminSelect2();
    });
})(django.jQuery);
