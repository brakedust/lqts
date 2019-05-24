header = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>LoQuTuS</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.0/css/bootstrap.min.css">
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.0/umd/popper.min.js"></script>
  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.0/js/bootstrap.min.js"></script>
  <script src="https://cdn.datatables.net/1.10.16/js/jquery.dataTables.min.js"></script>
  <script src="https://cdn.datatables.net/1.10.16/js/dataTables.bootstrap4.min.js"></script>
  <style>
  .fakeimg {{
      height: 100px;
      background: #aaa;
  }}
  </style>
</head>
<body>

<div style="background:steelblue">
        <h1 style="text-align:center;color: white">LoQuTuS</h1>
        <h2 style="text-align:center;color: white">QSTAT</h1>
    </div>
<!--
<nav class="navbar navbar-expand-sm bg-dark navbar-dark">
  <a class="navbar-brand" href="#">Navbar</a>
  <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#collapsibleNavbar">
    <span class="navbar-toggler-icon"></span>
  </button>
  <div class="collapse navbar-collapse" id="collapsibleNavbar">
    <ul class="navbar-nav">
      <li class="nav-item">
        <a class="nav-link" href="qstat.html">QSTAT</a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="agenda_status.html">Agenda Status</a>
      </li>
      <!-- <li class="nav-item">
        <a class="nav-link" href="#">Link</a>
      </li> -->
    </ul>
  </div>
</nav>
-->
"""


def qstat_coloring_script():
    return """<script>
        var i;
        var row;
        var t = document.getElementsByClassName("table");

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

    </script>"""


def make_html(title, content):

    html = f"""{header.format(title=title)}
{content}
{qstat_coloring_script()}
</body>
</html>
"""
    return html
