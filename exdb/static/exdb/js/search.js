"use strict";
$(document).ready(function () {
    $('#search-results').tablesorter({
        widgets: ["saveSort", "columns", "filter"],
        textExtraction: "basic",
        widgetOptions : {
            filter_cssFilter:'fa',
        },
    });

});
