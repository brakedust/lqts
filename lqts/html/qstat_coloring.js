var i;
var row;
// var t = document.getElementsByClassName("table");
var t = decument.getElementsById("QstatTable")

for (i = 0; i < t[0].rows.length; i++) {
    row = t[0].rows[i]
    if (row.cells[1].innerHTML == "R") {
        // running
        row.style.backgroundColor = "#007bff";
        row.style.color = "white";
    }
    else if (row.cells[1].innerHTML == "Q") {
        // queued

        if (row.cells[5].innerHTML.startsWith("-")) {
            row.style.color = "white";
            row.style.backgroundColor = "green";
        }
        else {
            // queued, has incomplete dependenceis
            row.style.backgroundColor = "lightgreen";
        }
    }
    else if (row.cells[1].innerHTML == "C") {
        row.style.color = "#999 ";
    }
    else if (row.cells[1].innerHTML == "D") {
        row.style.backgroundColor = "#ffcccc";
        row.style.color = "slategrey";
    }

}
$(document).ready(function () {
    $('table').DataTable(
        { paging: false }
    );

});