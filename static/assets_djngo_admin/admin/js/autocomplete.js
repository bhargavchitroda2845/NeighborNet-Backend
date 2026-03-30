(function($) {
    'use strict';

    /**
     * Initialize a single Select2 autocomplete widget
     * @param {jQuery} $element - The <select> element
     * @param {Object} options - Optional settings
     */
    var initAutocomplete = function($element, options) {
        // Merge default settings with user-provided options
        var settings = $.extend(true, {
            ajax: {
                data: function(params) {
                    return {
                        term: params.term,      // what the user types
                        page: params.page || 1, // pagination
                        app_label: $element.attr('data-app-label'),
                        model_name: $element.attr('data-model-name'),
                        field_name: $element.attr('data-field-name')
                    };
                },
                delay: 250 // small delay to reduce requests
            },
            minimumInputLength: 1,  // require at least 1 character before searching
            width: 'resolve',       // make the dropdown fit the container
            allowClear: true        // show clear (x) button if field is optional
        }, options);

        $element.select2(settings);
    };

    /**
     * jQuery plugin to initialize all admin autocomplete widgets
     */
    $.fn.djangoAdminSelect2 = function(options) {
        this.each(function() {
            var $element = $(this);
            initAutocomplete($element, options);
        });
        return this;
    };

    // Initialize all autocomplete widgets on page load
    $(function() {
        $('.admin-autocomplete').not('[name*=__prefix__]').djangoAdminSelect2();
    });

    // Re-initialize widgets for dynamically added formsets
    $(document).on('formset:added', function(event, $newFormset) {
        $newFormset.find('.admin-autocomplete').djangoAdminSelect2();
    });

})(django.jQuery);
