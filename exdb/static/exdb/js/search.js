"use strict";
$(document).ready(function () {
    $('#search-results').tablesorter({
        widgets: ["saveSort", "columns", "filter"],
        textExtraction: "basic",
        widgetOptions : {
            filter_cssFilter: 'fa round-search-box',
        },
    });

    $('tr.link').click(
        /* istanbul ignore next because this is actually covered & tested but istanbul won't realize that */
        function () {
            window.location = $(this).attr('data-url');
        }
    );

});
