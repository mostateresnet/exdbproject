"use strict";
$(document).ready(function () {
    $('#id_start_datetime, #id_end_datetime').fdatepicker({
        format: 'mm/dd/yyyy hh:ii',
        disableDblClickSelection: true,
        pickTime: true
    });
});
