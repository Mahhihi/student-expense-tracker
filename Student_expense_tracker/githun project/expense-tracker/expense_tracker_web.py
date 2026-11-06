"""Local browser interface for the personal expense tracker."""

import argparse
import csv
from datetime import date
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
from urllib.parse import parse_qs, urlencode, urlparse

import expense_tracker


def _render_page(expenses, category_filter="", month_filter="", message="",
                 all_expenses=None):
    """Render the tracker dashboard as a self-contained HTML page."""
    summary = expense_tracker.summarize_expenses(all_expenses or expenses)
    count = len(all_expenses) if all_expenses is not None else len(expenses)
    rows = []
    for item in expenses:
        rows.append(
            "<tr>"
            "<td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
            "<td class=\"amount\">${:.2f}</td>"
            "<td><form method=\"post\" class=\"inline\">"
            "<input type=\"hidden\" name=\"action\" value=\"delete\">"
            "<input type=\"hidden\" name=\"id\" value=\"{}\">"
            "<button class=\"delete\" type=\"submit\">Delete</button>"
            "</form></td></tr>".format(
                item["date"],
                html.escape(item["category"]),
                html.escape(item["description"]),
                item["id"],
                item["amount"],
                item["id"],
            )
        )

    category_totals = "".join(
        "<li><span>{}</span><strong>${:.2f}</strong></li>".format(
            html.escape(category), amount
        )
        for category, amount in sorted(summary["by_category"].items())
    ) or "<li class=\"muted\">No expenses yet</li>"
    expense_rows = "".join(rows) or (
        '<tr><td class="empty" colspan="6">No matching expenses.</td></tr>'
    )
    notice = (
        '<p class="notice">{}</p>'.format(html.escape(message))
        if message else ""
    )

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Personal Expense Tracker</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f6f8; color: #17212b; }}
    main {{ max-width: 1050px; margin: 40px auto; padding: 0 20px; }}
    h1 {{ margin-bottom: 4px; }}
    .subtitle, .muted {{ color: #687582; }}
    .cards {{ display: grid; grid-template-columns: repeat(3, 1fr);
      gap: 14px; }}
    .card, section {{ background: white; border: 1px solid #e1e6eb;
      border-radius: 10px; padding: 18px; }}
    .card span {{ display: block; color: #687582; font-size: .9rem; }}
    .card strong {{ display: block; font-size: 1.5rem;
      margin-top: 6px; }}
    .columns {{ display: grid; grid-template-columns: 1fr 1.35fr; gap: 16px;
      margin: 18px 0; }}
    label {{ display: block; font-size: .9rem; margin: 12px 0 5px; }}
    input {{ box-sizing: border-box; width: 100%; padding: 9px;
      border: 1px solid #cbd3da; border-radius: 6px; }}
    button, .button {{ display: inline-block; border: 0; border-radius: 6px;
      background: #1769aa; color: white; padding: 9px 13px;
      text-decoration: none; cursor: pointer; font: inherit; }}
    .delete {{ background: #a52e38; padding: 6px 9px; }}
    .inline {{ display: inline; }}
    .filter-row {{ display: grid; grid-template-columns: 1fr 1fr auto;
      gap: 10px; align-items: end; }}
    .filter-row label {{ margin-top: 0; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ text-align: left; padding: 10px 8px;
      border-bottom: 1px solid #e8ecef; }}
    th {{ color: #687582; font-size: .82rem; text-transform: uppercase; }}
    .amount {{ white-space: nowrap; }}
    .empty {{ text-align: center; color: #687582; padding: 24px; }}
    .notice {{ background: #e8f4ec; border-radius: 6px;
      padding: 10px 12px; }}
    ul {{ list-style: none; padding: 0; margin-bottom: 0; }}
    li {{ display: flex; justify-content: space-between; padding: 7px 0; }}
    .section-heading {{ display: flex; align-items: center;
      justify-content: space-between; gap: 12px; }}
    @media (max-width: 720px) {{
      .cards, .columns {{ grid-template-columns: 1fr; }}
      .filter-row {{ grid-template-columns: 1fr; }}
      main {{ margin-top: 24px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>Personal Expense Tracker</h1>
  <p class="subtitle">Your expenses, organized in one place.</p>
  {notice}
  <div class="cards">
    <div class="card"><span>Total spent</span>
      <strong>${total:.2f}</strong></div>
    <div class="card"><span>This month</span>
      <strong>${this_month:.2f}</strong></div>
    <div class="card"><span>Expenses recorded</span>
      <strong>{count}</strong></div>
  </div>
  <div class="columns">
    <section>
      <h2>Add an expense</h2>
      <form method="post">
        <input type="hidden" name="action" value="add">
        <label for="amount">Amount</label>
        <input id="amount" name="amount" type="number" min="0" step="0.01"
          required placeholder="0.00">
        <label for="category">Category</label>
        <input id="category" name="category" required
          placeholder="e.g. Food">
        <label for="description">Description</label>
        <input id="description" name="description"
          placeholder="Optional details">
        <label for="expense-date">Date</label>
        <input id="expense-date" name="expense_date" type="date"
          value="{today}" required>
        <p><button type="submit">Add expense</button></p>
      </form>
    </section>
    <section>
      <h2>Spending by category</h2>
      <ul>{categories}</ul>
    </section>
  </div>
  <section>
    <div class="section-heading">
      <h2>Expenses</h2>
      <a class="button" href="/export.csv">Export CSV</a>
    </div>
    <form method="get" class="filter-row">
      <div><label for="filter-category">Category</label>
        <input id="filter-category" name="category" value="{filter_category}"
          placeholder="Any category"></div>
      <div><label for="filter-month">Month</label>
        <input id="filter-month" name="month" type="month"
          value="{filter_month}"></div>
      <div><button type="submit">Filter</button>
        <a class="button" href="/">Clear</a></div>
    </form>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Date</th><th>Category</th><th>Description</th>
          <th>ID</th><th>Amount</th><th></th></tr></thead>
        <tbody>{expense_rows}</tbody>
      </table>
    </div>
  </section>
</main>
</body>
</html>""".format(
        notice=notice,
        total=summary["total"],
        this_month=summary["this_month"],
        count=count,
        categories=category_totals,
        today=date.today().isoformat(),
        filter_category=html.escape(category_filter, quote=True),
        filter_month=html.escape(month_filter, quote=True),
        expense_rows=expense_rows,
    )


class ExpenseTrackerHandler(BaseHTTPRequestHandler):
    """Handle dashboard, form, and CSV requests."""

    def _send(self, body, content_type="text/html; charset=utf-8", status=200,
              headers=None):
        body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, message):
        location = "/?{}".format(urlencode({"message": message}))
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self):
        """Display the dashboard or download a CSV export."""
        request = urlparse(self.path)
        if request.path == "/export.csv":
            try:
                expenses = expense_tracker.load_expenses(
                    self.server.data_file
                )
            except expense_tracker.ExpenseError as error:
                self._send(html.escape(str(error)), status=500)
                return

            output = io.StringIO(newline="")
            writer = csv.DictWriter(
                output, fieldnames=expense_tracker.CSV_FIELDS
            )
            writer.writeheader()
            writer.writerows(expenses)
            self._send(
                output.getvalue(),
                content_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition":
                        'attachment; filename="expenses.csv"'
                },
            )
            return

        if request.path != "/":
            self._send("Not found", status=404)
            return

        query = parse_qs(request.query)
        category = query.get("category", [""])[0]
        month = query.get("month", [""])[0]
        message = query.get("message", [""])[0]
        try:
            all_expenses = expense_tracker.load_expenses(self.server.data_file)
            expenses = expense_tracker.filter_expenses(
                all_expenses,
                category=category or None,
                month=month or None,
            )
            page = _render_page(
                expenses, category, month, message, all_expenses=all_expenses
            )
            self._send(page)
        except expense_tracker.ExpenseError as error:
            self._send(
                "<h1>Unable to show expenses</h1><p>{}</p>".format(
                    html.escape(str(error))
                ),
                status=400,
            )

    def do_POST(self):
        """Validate and process add/delete form submissions."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 1024 * 1024:
                message = "Form submission is too large."
                raise expense_tracker.ExpenseError(message)
            form_data = self.rfile.read(length).decode("utf-8")
            form = parse_qs(form_data)
            action = form.get("action", [""])[0]

            if action == "add":
                expense_tracker.add_expense(
                    form.get("amount", [""])[0],
                    form.get("category", [""])[0],
                    form.get("description", [""])[0],
                    form.get("expense_date", [""])[0],
                    self.server.data_file,
                )
                self._redirect("Expense added.")
            elif action == "delete":
                expense_id = form.get("id", [""])[0]
                if expense_tracker.delete_expense(
                        expense_id, self.server.data_file):
                    self._redirect("Expense deleted.")
                else:
                    self._redirect("Expense ID was not found.")
            else:
                raise expense_tracker.ExpenseError("Unknown form action.")
        except (UnicodeDecodeError, ValueError,
                expense_tracker.ExpenseError) as error:
            self._send(
                "<h1>Unable to save expense</h1><p>{}</p>"
                '<p><a href="/">Return to tracker</a></p>'.format(
                    html.escape(str(error))
                ),
                status=400,
            )

    def log_message(self, format_string, *args):
        """Keep request logging short and consistent."""
        print("{} - {}".format(self.address_string(), format_string % args))


def main(argv=None):
    """Start the local web server."""
    parser = argparse.ArgumentParser(
        description="Run the expense tracker in a local browser."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--data-file", default=str(expense_tracker.DATA_FILE),
        help="path to the expense JSON file",
    )
    args = parser.parse_args(argv)

    server = HTTPServer((args.host, args.port), ExpenseTrackerHandler)
    server.data_file = args.data_file
    print("Expense tracker running at http://{}:{}/".format(
        args.host, args.port
    ))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping expense tracker.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
