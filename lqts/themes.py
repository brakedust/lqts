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

<div class="jumbotron text-center" style="margin-bottom:0">
  <h1>{title}</h1>
  <!-- <p>Agenda Status</p> -->
</div>

# <nav class="navbar navbar-expand-sm bg-dark navbar-dark">
#   <a class="navbar-brand" href="#">Navbar</a>
#   <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#collapsibleNavbar">
#     <span class="navbar-toggler-icon"></span>
#   </button>
#   <div class="collapse navbar-collapse" id="collapsibleNavbar">
#     <ul class="navbar-nav">
#       <li class="nav-item">
#         <a class="nav-link" href="qstat.html">QSTAT</a>
#       </li>
#       <li class="nav-item">
#         <a class="nav-link" href="agenda_status.html">Agenda Status</a>
#       </li>
#       <!-- <li class="nav-item">
#         <a class="nav-link" href="#">Link</a>
#       </li> -->
#     </ul>
#   </div>
# </nav>
"""


def make_html(title, content):

    html = header.format(title=title) + content.replace(
        '<table border="1" class="dataframe">', '<table class="table table-sm display">'
    ).replace("<thead>", '<thead class="thead-dark">').replace(
        '<tr style="text-align: right;">', '<tr style="text-align: center;">'
    ).replace(
        "<tr>", '<tr style="text-align: center;">'
    )

    html += """

</body>
</html>
"""
    return html
