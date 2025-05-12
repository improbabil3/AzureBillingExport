import unittest
from src.core.export import export_to_csv
import os
import csv

class TestExportToCSV(unittest.TestCase):

    def setUp(self):
        self.test_data = [
            {"name": "Resource1", "cost": 100.0},
            {"name": "Resource2", "cost": 200.0},
        ]
        self.output_file = "test_output.csv"

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def test_export_to_csv_creates_file(self):
        export_to_csv(self.test_data, self.output_file)
        self.assertTrue(os.path.exists(self.output_file))

    def test_export_to_csv_correct_content(self):
        export_to_csv(self.test_data, self.output_file)
        with open(self.output_file, mode='r') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            self.assertEqual(len(rows), len(self.test_data))
            for i, row in enumerate(rows):
                self.assertEqual(row['name'], self.test_data[i]['name'])
                self.assertEqual(float(row['cost']), self.test_data[i]['cost'])

if __name__ == '__main__':
    unittest.main()