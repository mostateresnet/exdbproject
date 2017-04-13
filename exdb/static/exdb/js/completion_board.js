"use strict";


$(document).ready(function () {

    $( "#switch-section" ).click(function( event ) {
        event.preventDefault();
        $("#switch-section").attr("href", $("#sel option:selected").val());
        $("#switch-section").attr("href", $("#sel option:selected").val());
        window.location.href = $("#switch-section").attr("href");
    });

    $(".cell").click(function(event) {
        $(this).children().toggleClass('hidden');
    })
});
