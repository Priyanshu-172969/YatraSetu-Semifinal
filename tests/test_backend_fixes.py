"""
test_backend_fixes.py - Tests for safe pagination, server-side validation, error handling, and CSRF protection.
"""

import unittest
from unittest.mock import patch, MagicMock
from app import app, generate_csrf_token

class TestBackendFixes(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-321'
        self.client = app.test_client()

    def test_safe_pagination_malformed_and_bounds(self):
        """Verifies safe pagination on malformed, zero, negative, and out-of-range page params."""
        app.config['WTF_CSRF_ENABLED'] = False
        mock_dest = [{'destination_id': 1, 'place_name': 'Taj Mahal', 'locality_city': 'Agra', 'district': 'Agra', 'state_ut': 'Uttar Pradesh', 'category': 'Heritage', 'description': 'Iconic'}]
        with patch('app.fetch_all', return_value=mock_dest):
            with patch('app.fetch_one', return_value={'total': 25}):
                # Malformed non-integer: ?page=abc
                res_abc = self.client.get('/destinations?page=abc')
                self.assertEqual(res_abc.status_code, 200)

                # Zero: ?page=0
                res_zero = self.client.get('/destinations?page=0')
                self.assertEqual(res_zero.status_code, 200)

                # Negative: ?page=-5
                res_neg = self.client.get('/destinations?page=-5')
                self.assertEqual(res_neg.status_code, 200)

                # Clamped above total: ?page=999
                res_large = self.client.get('/destinations?page=999')
                self.assertEqual(res_large.status_code, 200)

    def test_csrf_protection_rejects_missing_token(self):
        """Verifies that state-changing POST requests without CSRF token receive HTTP 400."""
        app.config['WTF_CSRF_ENABLED'] = True
        response = self.client.post('/trips/create', data={
            'trip_name': 'Himalayan Trek',
            'starting_city': 'New Delhi',
            'planned_duration_days': '7'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"CSRF", response.data)

    def test_csrf_protection_accepts_valid_token(self):
        """Verifies that POST with a valid session CSRF token is accepted."""
        app.config['WTF_CSRF_ENABLED'] = True
        with self.client.session_transaction() as sess:
            sess['_csrf_token'] = 'valid-csrf-token-1234567890abcdef'

        with patch('app.execute_query', return_value=10):
            response = self.client.post('/trips/create', data={
                'csrf_token': 'valid-csrf-token-1234567890abcdef',
                'trip_name': 'Goa Monsoon Tour',
                'starting_city': 'Bengaluru',
                'planned_duration_days': '5'
            }, follow_redirects=False)
            self.assertEqual(response.status_code, 302)

    def test_trip_duration_range_validation(self):
        """Verifies server-side validation for trip duration (1-90 days)."""
        app.config['WTF_CSRF_ENABLED'] = False
        # Too long: 100 days
        res_high = self.client.post('/trips/create', data={
            'trip_name': 'World Tour',
            'starting_city': 'New Delhi',
            'planned_duration_days': '100'
        }, follow_redirects=True)
        self.assertIn(b"Planned trip duration must be between 1 and 90 days", res_high.data)

        # Invalid non-numeric
        res_alpha = self.client.post('/trips/create', data={
            'trip_name': 'World Tour',
            'starting_city': 'New Delhi',
            'planned_duration_days': 'invalid'
        }, follow_redirects=True)
        self.assertIn(b"Planned duration must be a valid number of days", res_alpha.data)

    def test_trip_move_direction_validation(self):
        """Verifies invalid direction value in trip_move_stop is rejected."""
        app.config['WTF_CSRF_ENABLED'] = False
        response = self.client.post('/trips/1/stops/1/move/sideways', follow_redirects=True)
        self.assertIn(b"Invalid stop movement direction", response.data)

    def test_stop_duration_range_validation(self):
        """Verifies stop duration (1-30 days) is validated on server."""
        app.config['WTF_CSRF_ENABLED'] = False
        with patch('app.fetch_one', side_effect=lambda q, p=None: {'trip_id': 1} if 'trip_plans' in q else {'destination_id': 1}):
            response = self.client.post('/trips/1/stops/add', data={
                'destination_id': '1',
                'planned_days': '45'
            }, follow_redirects=True)
            self.assertIn(b"Stop duration must be between 1 and 30 days", response.data)

    def test_destination_create_required_fields_validation(self):
        """Verifies missing required fields in destination_create returns error with entered fields."""
        app.config['WTF_CSRF_ENABLED'] = False
        response = self.client.post('/destinations/new', data={
            'place_name': 'Incomplete Destination',
            'locality_city': 'City Only'
            # other required fields missing
        }, follow_redirects=True)
        self.assertIn(b"All required fields marked with an asterisk (*) must be filled", response.data)
        self.assertIn(b"Incomplete Destination", response.data)

if __name__ == '__main__':
    unittest.main()
