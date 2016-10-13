"use strict";


$(document).ready(function () {

    function toggle_fields() {
        var selected_subtypes = $('#id_subtype option:selected');
        var needs_verification = $('#id_subtype option.verification:selected').length > 0;
        var no_verification = $('#id_subtype option.no-verification:selected').length > 0;
        var show_fields = no_verification && !needs_verification;
        $('#id_attendance').closest('div').toggle(show_fields);
        $('#id_conclusion').closest('div').toggle(show_fields);
    }

    toggle_fields();

    $('#id_subtype').on('click change', toggle_fields);

    $('#delete').click(function () {
        return confirm("Are you sure you want to delete this experience?");
    });

    $('#id_start_datetime').fdatepicker({
        format: 'mm/dd/yyyy hh:ii',
        pickTime: true
    });

    $('#id_end_datetime').fdatepicker({
        format: 'mm/dd/yyyy hh:ii',
        pickTime: true
    });
});
