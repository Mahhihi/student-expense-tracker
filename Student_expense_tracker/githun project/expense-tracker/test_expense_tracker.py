"""Basic unit tests for the expense tracker."""

import csv
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

import expense_tracker
import expense_tracker_web


class ExpenseTrackerTests(unittest.TestCase):
    """Test storage, validation, summaries, filtering, and CSV export."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temp_dir.name) / "expenses.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_data_file_is_created(self):
        self.assertEqual(expense_tracker.load_expenses(self.data_file), [])
        self.assertTrue(self.data_file.exists())

    def test_add_and_delete_expense(self):
        expense = expense_tracker.add_expense(
            12.5, "Food", "Lunch", "2024-01-03", self.data_file
        )
        self.assertEqual(expense["id"], 1)
        loaded = expense_tracker.load_expenses(self.data_file)
        self.assertEqual(loaded, [expense])
        self.assertTrue(expense_tracker.delete_expense(1, self.data_file))
        self.assertFalse(expense_tracker.delete_expense(1, self.data_file))

    def test_invalid_amount_category_and_date_are_rejected(self):
        for amount, category, expense_date in (
                (-1, "Food", "2024-01-01"),
                (1, "  ", "2024-01-01"),
                (1, "Food", "not-a-date")):
            with self.subTest(amount=amount, category=category,
                              expense_date=expense_date):
                with self.assertRaises(expense_tracker.ExpenseError):
                    expense_tracker.add_expense(
                        amount, category, "", expense_date, self.data_file
                    )

    def test_summary_and_filters(self):
        expenses = [
            {"id": 1, "amount": 10.0, "category": "Food",
             "description": "Lunch", "date": "2024-05-01"},
            {"id": 2, "amount": 20.0, "category": "Travel",
             "description": "Bus", "date": "2024-04-30"},
        ]
        summary = expense_tracker.summarize_expenses(
            expenses, today=date(2024, 5, 15)
        )
        self.assertEqual(summary["total"], 30.0)
        self.assertEqual(summary["by_category"]["Food"], 10.0)
        self.assertEqual(summary["this_month"], 10.0)
        self.assertEqual(
            [item["id"] for item in expense_tracker.filter_expenses(
                expenses, category="food"
            )],
            [1],
        )
        self.assertEqual(
            [item["id"] for item in expense_tracker.filter_expenses(
                expenses, month="2024-04"
            )],
            [2],
        )

    def test_corrupt_json_is_reported(self):
        self.data_file.write_text("{bad json", encoding="utf-8")
        with self.assertRaises(expense_tracker.StorageError):
            expense_tracker.load_expenses(self.data_file)

    def test_csv_export(self):
        expenses = [expense_tracker.add_expense(
            4, "Books", "Notebook", "2024-02-02", self.data_file
        )]
        csv_file = Path(self.temp_dir.name) / "expenses.csv"
        expense_tracker.export_expenses(expenses, csv_file)
        with csv_file.open(newline="", encoding="utf-8") as exported:
            rows = list(csv.DictReader(exported))
        self.assertEqual(rows[0]["category"], "Books")
        self.assertEqual(rows[0]["amount"], "4.0")

    def test_invalid_json_shape_is_reported(self):
        invalid_data = json.dumps({"expense": []})
        self.data_file.write_text(invalid_data, encoding="utf-8")
        with self.assertRaises(expense_tracker.StorageError):
            expense_tracker.load_expenses(self.data_file)

    def test_web_page_escapes_user_supplied_text(self):
        page = expense_tracker_web._render_page(
            [{
                "id": 1,
                "amount": 5.0,
                "category": "<script>alert(1)</script>",
                "description": "Test & verify",
                "date": "2024-01-01",
            }]
        )
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("Test &amp; verify", page)


if __name__ == "__main__":
    unittest.main()
