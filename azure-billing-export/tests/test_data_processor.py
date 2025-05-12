import unittest
from src.core.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = DataProcessor()

    def test_aggregate_data(self):
        sample_data = [
            {'amount': 100, 'category': 'Compute'},
            {'amount': 200, 'category': 'Storage'},
            {'amount': 150, 'category': 'Compute'},
        ]
        expected_result = {
            'Compute': 250,
            'Storage': 200
        }
        result = self.processor.aggregate_data(sample_data)
        self.assertEqual(result, expected_result)

    def test_format_data_for_csv(self):
        aggregated_data = {
            'Compute': 250,
            'Storage': 200
        }
        expected_csv_format = [
            ['Category', 'Total Amount'],
            ['Compute', 250],
            ['Storage', 200]
        ]
        result = self.processor.format_data_for_csv(aggregated_data)
        self.assertEqual(result, expected_csv_format)

if __name__ == '__main__':
    unittest.main()