# Personal Expense Tracker

A simple Python command-line app for recording, reviewing, and exporting personal expenses.

## Features

- Add expenses with amount, category, description, and date (today by default)
- View expenses in a readable table
- Delete an expense by ID
- See total spending, category totals, and this month's total
- Filter by category or month
- Export expenses to CSV
- Store data locally in `expenses.json`, created automatically when needed
- Validate inputs and report corrupt or inaccessible data gracefully

## Installation

1. Install Python 3.8 or newer.
2. Clone this repository and enter the project directory:

   ```sh
   git clone https://github.com/YOUR-USERNAME/expense-tracker.git
   cd expense-tracker
   ```

3. No dependencies need to be installed; the app uses the Python standard library.

## Usage

Run commands from the project directory:

```sh
python expense_tracker.py add 12.50 Food --description "Lunch"
python expense_tracker.py add 35.00 Transport --description "Train ticket" --date 2025-03-12
python expense_tracker.py list
python expense_tracker.py delete 1
python expense_tracker.py summary
python expense_tracker.py filter --category Food
python expense_tracker.py filter --month 2025-03
python expense_tracker.py export expenses.csv
```

By default, the data file is `expenses.json` next to the script. To use a different
JSON file, pass `--data-file` before the command:

```sh
python expense_tracker.py --data-file my-expenses.json list
```

### Browser interface

Start the local web app from the project directory:

```sh
python expense_tracker_web.py
```

Then open `http://localhost:8080` in a browser. The browser interface supports
adding and deleting expenses, viewing summaries, filtering, and downloading a
CSV export. Press `Ctrl+C` in the terminal to stop the server. You can also use
the existing VS Code **Launch Chrome against localhost** configuration after
the server is running.

### Sample output

```text
$ python expense_tracker.py list
ID | DATE       | CATEGORY | DESCRIPTION | AMOUNT
---+------------+----------+-------------+-------
1  | 2025-03-12 | Food     | Lunch       | 12.50

$ python expense_tracker.py summary
Total spent: $12.50
Spending by category:
  Food: $12.50
This month's total: $12.50
```

## Tests

Run the unit tests with:

```sh
python -m unittest -v
```

## Future improvements

- Add recurring expenses and budgets
- Support date-range reports and charts
- Add an interactive menu and configurable currency

## How to contribute

Fork the repository, create a focused feature or fix branch, and add or update
unit tests for your changes. Run `python -m unittest -v`, then open a pull
request describing the change.

## GitHub repository setup

Create an empty repository on GitHub named `expense-tracker`, then run these
commands from this project directory (replace `YOUR-USERNAME`):

```sh
git init
git add .
git commit -m "Initial commit: personal expense tracker"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/expense-tracker.git
git push -u origin main
```

Suggested repository description: **A simple Python CLI to record, review, summarize, and export personal expenses.**

Suggested topics: `python`, `command-line`, `expense-tracker`, `personal-finance`, `csv`, `json`
