bb.pages.builders = function(next, route_matches) {
    var div = $('<div>');
    div.append('<h1>Builders</h1>');

    bb.display_page_content(next, div);
    return true;
}
