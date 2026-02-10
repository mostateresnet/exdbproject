"use strict";


$(document).ready(function () {
    $('#search-results').tablesorter({
        widgets: ["saveSort", "columns"],
        textExtraction: "basic",
    });

    $('.column-filter').on('change', function () {
        $('#search-filter-form').submit();
    });

    $('tr.link').click(
        /* istanbul ignore next because this is actually covered & tested but istanbul won't realize that */
        function () {
            window.location = $(this).attr('data-url');
        }
    );


});
