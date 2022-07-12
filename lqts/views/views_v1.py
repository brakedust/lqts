from lqts.core import server
from lqts.html.render_qstat import render_qstat_page, render_qstat_table, render_qtop_table
from starlette.responses import HTMLResponse


app = server.get_app()


@app.get("/")
async def root():

    return HTMLResponse(render_qstat_page(False))


@app.get("/qstatus")
async def qstat_html(complete: str = "no"):

    complete = complete == "yes"
    return HTMLResponse(render_qstat_page(complete))


@app.get("/page_fragments/qstat_table")
async def qstat_table_html(complete: str = "no"):

    complete = complete == "yes"
    html_text = render_qstat_table(app.queue.all_jobs, complete)
    # print(html_text)
    return HTMLResponse(html_text)


@app.get("/page_fragments/qtop_table")
async def qstat_table_html():

    html_text = render_qtop_table(app.queue.all_jobs)
    # print(html_text)
    return HTMLResponse(html_text)
