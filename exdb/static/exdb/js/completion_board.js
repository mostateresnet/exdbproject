"use strict";


$(document).ready(function () {
    $("#switch-affiliation").click(function (event) {
        event.preventDefault();
        window.location.href = $("#affiliation-selector option:selected").val();
    });
    $("table.fixed-headers").floatThead();
});
