"use strict";

$(document).ready(function () {

    $('#id_attendance').closest('div').addClass('hide');

    $('#id_type').change(function () {
        var att_field = $('#id_attendance').closest('div');
        if ($('#id_type option:selected').hasClass('no-verification') && att_field.hasClass('hide')) {
            att_field.removeClass('hide');
        }
        if (!$('#id_type option:selected').hasClass('no-verification') && !att_field.hasClass('hide')) {
            att_field.addClass('hide');
        }
    });
});
