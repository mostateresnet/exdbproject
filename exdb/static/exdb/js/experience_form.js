"use strict";

$(document).ready(function () {

    if (!$('#id_type option:selected').hasClass('no-verification')) {
        $('#id_attendance').closest('div').addClass('hide');
        $('#id_conclusion').closest('div').addClass('hide');
    }

    $('#id_type').change(function () {
        var att_field, con_field;
        att_field = $('#id_attendance').closest('div');
        con_field = $('#id_conclusion').closest('div');
        if ($('#id_type option:selected').hasClass('no-verification') && att_field.hasClass('hide') && con_field.hasClass('hide')) {
            att_field.removeClass('hide');
            con_field.removeClass('hide');
        }
        if (!$('#id_type option:selected').hasClass('no-verification') && !att_field.hasClass('hide') && !con_field.hasClass('hide')) {
            att_field.addClass('hide');
            con_field.addClass('hide');
        }
    });
});
