// Data Table properties

$(document).ready(function() {
    $('#game-search-table').DataTable( {
        "order": [[ 0, "asc" ]],
        "pagingType": "first_last_numbers",
        "pageLength": 25,
    } );
} );