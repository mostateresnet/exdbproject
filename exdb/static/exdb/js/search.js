"use strict";
$(document).ready(function () {
    $('#search-results').tablesorter({
        widgets: ["saveSort", "columns", "filter"],
        textExtraction: "basic",
        widgetOptions : {
            filter_cssFilter: 'fa round-search-box',
        },
    });

    $('tr.link').click(function () {
        window.location = $(this).attr('data-url');
    });

});
