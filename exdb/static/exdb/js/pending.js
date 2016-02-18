'use strict';

$(document).ready(function () {
    $('#pending-queue').tablesorter({
        widgets: ["filter"],
    });
    $('#evaluation-queue').tablesorter({
        widgets: ["filter"],
    });
});
