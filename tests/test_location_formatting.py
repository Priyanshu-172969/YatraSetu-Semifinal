"""
test_location_formatting.py - Unit Tests for Location Formatting Helper
Tests deduplication of localities, districts, states, and conditional 'District' suffixing.
"""

import unittest
from app import format_location

class TestLocationFormatting(unittest.TestCase):

    def test_district_already_in_locality(self):
        """Verifies no duplicate district when district is part of locality (e.g., Amer, Jaipur)."""
        dest = {
            'locality_city': 'Amer, Jaipur',
            'district': 'Jaipur',
            'state_ut': 'Rajasthan'
        }
        result = format_location(dest)
        self.assertEqual(result, 'Amer, Jaipur, Rajasthan')
        # Even with append_district=True, Jaipur should not be appended
        result_detailed = format_location(dest, append_district=True)
        self.assertEqual(result_detailed, 'Amer, Jaipur, Rajasthan')

    def test_locality_equals_district(self):
        """Verifies no duplicate when locality is identical to district (e.g., Agra)."""
        dest = {
            'locality_city': 'Agra',
            'district': 'Agra',
            'state_ut': 'Uttar Pradesh'
        }
        self.assertEqual(format_location(dest), 'Agra, Uttar Pradesh')
        self.assertEqual(format_location(dest, append_district=True), 'Agra, Uttar Pradesh')

    def test_district_already_contains_word_district(self):
        """Verifies 'District' is not repeated when district text already includes it (e.g., Golaghat and adjoining districts)."""
        dest = {
            'locality_city': 'Kohora/Bokakhat',
            'district': 'Golaghat and adjoining districts',
            'state_ut': 'Assam'
        }
        result = format_location(dest, append_district=True)
        self.assertEqual(result, 'Kohora/Bokakhat, Golaghat and adjoining districts, Assam')
        self.assertNotIn('districts District', result)

    def test_distinct_district_without_suffix(self):
        """Verifies distinct district is included cleanly without suffix when append_district=False."""
        dest = {
            'locality_city': 'Hampi',
            'district': 'Vijayanagara',
            'state_ut': 'Karnataka'
        }
        self.assertEqual(format_location(dest, append_district=False), 'Hampi, Vijayanagara, Karnataka')

    def test_distinct_district_with_suffix(self):
        """Verifies distinct district gets 'District' suffix when append_district=True."""
        dest = {
            'locality_city': 'Hampi',
            'district': 'Vijayanagara',
            'state_ut': 'Karnataka'
        }
        self.assertEqual(format_location(dest, append_district=True), 'Hampi, Vijayanagara District, Karnataka')

    def test_state_already_represented_in_location(self):
        """Verifies state is not repeated if already present in locality or district (e.g., Delhi)."""
        dest = {
            'locality_city': 'Mehrauli, New Delhi',
            'district': 'South Delhi',
            'state_ut': 'Delhi'
        }
        result = format_location(dest, append_district=False)
        self.assertEqual(result, 'Mehrauli, New Delhi, South Delhi')

    def test_raw_arguments_invocation(self):
        """Verifies format_location can be called with positional string arguments."""
        result = format_location('Amer, Jaipur', 'Jaipur', 'Rajasthan')
        self.assertEqual(result, 'Amer, Jaipur, Rajasthan')

        result2 = format_location('Konark', 'Puri', 'Odisha', append_district=True)
        self.assertEqual(result2, 'Konark, Puri District, Odisha')

if __name__ == '__main__':
    unittest.main()
