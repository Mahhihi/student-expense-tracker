"""A simple command-line personal expense tracker."""

import argparse
import csv
from datetime import date
import json
import math
from pathlib import Path


DATA_FILE = Path(__file__).with_name("expenses.json")
CSV_FIELDS = ("id", "amount", "category", "description", "date")


class ExpenseError(Exception):
    """Raised when expense data or user input is invalid."""


class StorageError(ExpenseError):
    """Raised when the expense file cannot be read or written."""


def validate_amount(amount):
    """Return a valid non-negative expense amount."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ExpenseError("Amount must be a number.")

    if not math.isfinite(amount) or amount < 0:
        raise ExpenseError("Amount must be a finite, non-negative number.")
    return amount


def validate_date(value):
    """Return an ISO-formatted date, defaulting to today when omitted."""
    if value is None:
        return date.today().isoformat()

    try:
        parsed_date = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ExpenseError("Date must be a valid date in YYYY-MM-DD format.")
    return parsed_date.isoformat()


def _validate_expense(expense):
    """Validate and normalize an expense loaded from storage."""
    if not isinstance(expense, dict):
        raise ExpenseError("Each expense must be a JSON object.")

    try:
        expense_id = int(expense["id"])
        amount = validate_amount(expense["amount"])
        category = str(expense["category"]).strip()
        description = str(expense["description"]).strip()
        expense_date = validate_date(expense["date"])
    except (KeyError, TypeError, ValueError) as error:
        message = "An expense is missing valid required fields."
        raise ExpenseError(message) from error

    if expense_id < 1:
        raise ExpenseError("Expense IDs must be positive integers.")
    if not category:
        raise ExpenseError("Expense category cannot be empty.")

    return {
        "id": expense_id,
        "amount": amount,
        "category": category,
        "description": description,
        "date": expense_date,
    }


def load_expenses(file_path=DATA_FILE):
    """Load expenses from JSON, creating the file when it does not exist."""
    path = Path(file_path)
    if not path.exists():
        save_expenses([], path)
        return []

    try:
        with path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
    except (OSError, json.JSONDecodeError) as error:
        message = "Could not read expenses.json: {}".format(error)
        raise StorageError(message) from error

    if not isinstance(data, list):
        raise StorageError("Expense data must be a JSON list.")

    try:
        expenses = [_validate_expense(item) for item in data]
    except ExpenseError as error:
        message = "Expense data is invalid: {}".format(error)
        raise StorageError(message) from error
    return expenses


def save_expenses(expenses, file_path=DATA_FILE):
    """Write expenses to a JSON file."""
    path = Path(file_path)
    try:
        with path.open("w", encoding="utf-8") as data_file:
            json.dump(expenses, data_file, indent=2)
            data_file.write("\n")
    except OSError as error:
        message = "Could not save expenses: {}".format(error)
        raise StorageError(message) from error


def add_expense(amount, category, description="", expense_date=None,
                file_path=DATA_FILE):
    """Validate, save, and return a new expense."""
    amount = validate_amount(amount)
    category = str(category).strip()
    if not category:
        raise ExpenseError("Expense category cannot be empty.")
    expense_date = validate_date(expense_date)

    expenses = load_expenses(file_path)
    expense = {
        "id": max((item["id"] for item in expenses), default=0) + 1,
        "amount": amount,
        "category": category,
        "description": str(description).strip(),
        "date": expense_date,
    }
    expenses.append(expense)
    save_expenses(expenses, file_path)
    return expense


def delete_expense(expense_id, file_path=DATA_FILE):
    """Delete an expense by ID and return whether it was found."""
    try:
        expense_id = int(expense_id)
    except (TypeError, ValueError):
        raise ExpenseError("Expense ID must be an integer.")

    expenses = load_expenses(file_path)
    remaining = [item for item in expenses if item["id"] != expense_id]
    if len(remaining) == len(expenses):
        return False
    save_expenses(remaining, file_path)
    return True


def filter_expenses(expenses, category=None, month=None):
    """Filter expenses by category and/or YYYY-MM month."""
    if month is not None:
        try:
            parsed_month = date.fromisoformat(month + "-01")
        except (TypeError, ValueError):
            raise ExpenseError("Month must be in YYYY-MM format.")
        month = parsed_month.strftime("%Y-%m")

    return [
        item for item in expenses
        if (category is None
            or item["category"].casefold() == category.strip().casefold())
        and (month is None or item["date"][:7] == month)
    ]


def summarize_expenses(expenses, today=None):
    """Return total spending, category totals, and this month's total."""
    today = today or date.today()
    category_totals = {}
    total = 0.0
    month_total = 0.0

    for expense in expenses:
        amount = expense["amount"]
        total += amount
        category_totals[expense["category"]] = (
            category_totals.get(expense["category"], 0.0) + amount
        )
        if expense["date"][:7] == today.strftime("%Y-%m"):
            month_total += amount

    return {
        "total": total,
        "by_category": category_totals,
        "this_month": month_total,
    }


def export_expenses(expenses, file_path):
    """Export expenses to a CSV file."""
    try:
        with Path(file_path).open(
                "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(expenses)
    except OSError as error:
        raise StorageError("Could not export CSV: {}".format(error)) from error


def _format_table(expenses):
    """Format expenses as a readable, fixed-width table."""
    headers = ("ID", "DATE", "CATEGORY", "DESCRIPTION", "AMOUNT")
    rows = [
        (
            str(item["id"]),
            item["date"],
            item["category"],
            item["description"],
            "{:.2f}".format(item["amount"]),
        )
        for item in expenses
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        if rows else len(headers[index])
        for index in range(len(headers))
    ]
    line = "-+-".join("-" * width for width in widths)
    output = [" | ".join(headers[index].ljust(widths[index])
                         for index in range(len(headers))), line]
    output.extend(
        " | ".join(row[index].ljust(widths[index])
                   for index in range(len(headers)))
        for row in rows
    )
    return "\n".join(output)


def _build_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Track personal expenses in a local JSON file."
    )
    parser.add_argument(
        "--data-file", default=str(DATA_FILE),
        help="path to the expense JSON file (default: expenses.json)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser("add", help="add an expense")
    add_parser.add_argument("amount", type=float)
    add_parser.add_argument("category")
    add_parser.add_argument("--description", default="")
    add_parser.add_argument("--date", dest="expense_date")

    commands.add_parser("list", help="view all expenses")

    delete_parser = commands.add_parser(
        "delete", help="delete an expense by ID"
    )
    delete_parser.add_argument("id", type=int)

    commands.add_parser("summary", help="show spending totals")

    filter_parser = commands.add_parser("filter", help="filter expenses")
    filter_parser.add_argument("--category")
    filter_parser.add_argument("--month", help="month in YYYY-MM format")

    export_parser = commands.add_parser(
        "export", help="export expenses to CSV"
    )
    export_parser.add_argument("csv_file")
    return parser


def main(argv=None):
    """Run the command-line interface and report user-friendly errors."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "add":
            expense = add_expense(
                args.amount, args.category, args.description,
                args.expense_date, args.data_file,
            )
            print("Added expense #{}.".format(expense["id"]))
        elif args.command == "list":
            expenses = load_expenses(args.data_file)
            message = (
                _format_table(expenses)
                if expenses else "No expenses found."
            )
            print(message)
        elif args.command == "delete":
            if delete_expense(args.id, args.data_file):
                print("Deleted expense #{}.".format(args.id))
            else:
                print("Expense #{} not found.".format(args.id))
        elif args.command == "summary":
            summary = summarize_expenses(load_expenses(args.data_file))
            print("Total spent: ${:.2f}".format(summary["total"]))
            print("Spending by category:")
            if summary["by_category"]:
                for category, amount in sorted(summary["by_category"].items()):
                    print("  {}: ${:.2f}".format(category, amount))
            else:
                print("  No expenses found.")
            print("This month's total: ${:.2f}".format(summary["this_month"]))
        elif args.command == "filter":
            expenses = filter_expenses(
                load_expenses(args.data_file), args.category, args.month
            )
            message = (
                _format_table(expenses)
                if expenses else "No matching expenses."
            )
            print(message)
        elif args.command == "export":
            expenses = load_expenses(args.data_file)
            export_expenses(expenses, args.csv_file)
            print("Exported {} expense(s) to {}.".format(
                len(expenses), args.csv_file
            ))
    except (ExpenseError, StorageError) as error:
        print("Error: {}".format(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
