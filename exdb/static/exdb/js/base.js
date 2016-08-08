'use strict';

$(document).ready(function () {
    $('button#mobile-menu-toggle').click(function () {
        $('ul#mobile-menu').toggleClass('hide', !$('ul#mobile-menu').hasClass('hide'));
    });
});
