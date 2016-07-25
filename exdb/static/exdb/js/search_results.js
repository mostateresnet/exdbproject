"use strict";
$(document).ready(function () {
    $('#search-results').tablesorter({
        theme: "bootstrap",
        widgets: ["saveSort", "columns", "filter"],
        textExtraction: "basic",
    });
});
