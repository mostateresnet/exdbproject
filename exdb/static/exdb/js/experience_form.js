"use strict";


$(document).ready(function () {

    function toggle_fields() {
        var show_fields = $('#id_subtypes option.no-verification:selected').length > 0 && $('#id_subtypes option.verification:selected').length === 0;
        $('#id_attendance').closest('div').toggle(show_fields);
        $('#id_conclusion').closest('div').toggle(show_fields);
    }

    toggle_fields();

    $('#id_subtypes').on('click change', toggle_fields);

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
