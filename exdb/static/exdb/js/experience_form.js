"use strict";


$(document).ready(function () {

    function toggle_fields() {
        //This next line is redundant solely for coverage.
        //It can be simplified when another branch is added to the project's js.
        var no_verification = $('#id_subtype option.no-verification:selected').length ? true : false;
        $('#id_attendance').closest('div').toggle(no_verification);
        $('#id_conclusion').closest('div').toggle(no_verification);
    }

    toggle_fields();

    $('#id_subtype').change(toggle_fields);

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
