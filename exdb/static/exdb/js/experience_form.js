"use strict";


$(document).ready(function () {

    function toggle_fields() {
        var i,
            show_fields,
            valid_subtypes = $('#id_type option:selected').data('valid-subtypes');
        if (valid_subtypes) {
            valid_subtypes = String(valid_subtypes).split(',');
            $('#id_subtypes li').hide();
            for (i = 0; i < valid_subtypes.length; i += 1) {
                $('#id_subtypes input[value=' + valid_subtypes[i] + ']').closest('li').show();
            }
            $('#id_subtypes input').not(':visible').prop('checked', false);
        } else {
            $('#id_subtypes li').show();
        }
        show_fields = $('#id_subtypes .no-verification:checked').length > 0 && $('#id_subtypes .verification:checked').length === 0;
        $('#id_attendance').closest('div').toggle(show_fields);
        $('#id_conclusion').closest('div').toggle(show_fields);
    }

    toggle_fields();

    $('#id_type, #id_subtypes').on('click change', toggle_fields);

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
