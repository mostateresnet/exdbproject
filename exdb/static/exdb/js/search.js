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


    $('button#export').click(function (){
        var experiences = [];
        $('table#search-results tbody tr:not(.filtered)').each(function (){
            experiences.push($(this).data('pk'));
        });
        //var data = new FormData();
        //data.append('experiences', JSON.stringify(experiences));
        window.location = $(this).data('url')+"?experiences="+JSON.stringify(experiences);
    });
});
