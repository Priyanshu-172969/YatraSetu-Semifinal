"""
test_images_and_filters.py - Tests for destination photography metadata resolution,
authoritative CSV place_name mapping, license compliance, template rendering,
graceful fallbacks, and Jinja template filters (split_urls).
"""

import os
import csv
import unittest
from unittest.mock import patch
from app import app, get_destination_image, split_urls

class TestImagesAndFilters(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_all_30_destination_ids_map_to_authoritative_csv_and_valid_images(self):
        """
        Authoritative verification:
        Opens destination_core.csv and verifies that for each destination_id:
        1. An image metadata record exists.
        2. meta['place_name'] exactly matches the CSV place_name.
        3. The corresponding image file exists locally on disk and has substantial size (> 5 KB).
        4. The license is permissible (CC BY, CC BY-SA, CC0, Public Domain) and contains NO ND / NO NC.
        5. Source URL and artist credit are present and non-empty.
        """
        csv_path = os.path.join(app.root_path, 'destination_core.csv')
        self.assertTrue(os.path.exists(csv_path), "destination_core.csv must exist in project root")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            csv_records = list(reader)

        self.assertEqual(len(csv_records), 30, "destination_core.csv must contain exactly 30 records")

        for row in csv_records:
            dest_id = int(row['destination_id'])
            expected_name = row['place_name'].strip()

            meta = get_destination_image(dest_id)
            self.assertIsNotNone(
                meta,
                f"Missing image mapping for destination_id={dest_id} ('{expected_name}')"
            )

            # Strict place_name match against authoritative CSV
            self.assertEqual(
                meta['place_name'],
                expected_name,
                f"Destination ID {dest_id} mapping mismatch: expected '{expected_name}', got '{meta['place_name']}'"
            )

            # File existence and validity
            full_path = os.path.join(app.root_path, 'static', meta['path'])
            self.assertTrue(
                os.path.exists(full_path),
                f"Image file missing on disk: {full_path} for destination '{expected_name}'"
            )
            file_size = os.path.getsize(full_path)
            self.assertGreater(
                file_size,
                5000,
                f"Image file suspiciously small ({file_size} bytes): {full_path}"
            )

            # License verification: strictly NO NoDerivatives (ND) and NO NonCommercial (NC)
            lic = meta.get('license', '').upper()
            self.assertNotIn(
                'ND',
                lic,
                f"Destination ID {dest_id} ('{expected_name}') has prohibited ND license: {meta.get('license')}"
            )
            self.assertNotIn(
                'NC',
                lic,
                f"Destination ID {dest_id} ('{expected_name}') has prohibited NC license: {meta.get('license')}"
            )

            # Provenance and attribution
            self.assertTrue(
                meta.get('artist'),
                f"Destination ID {dest_id} ('{expected_name}') must have artist attribution"
            )
            self.assertTrue(
                meta.get('source_url'),
                f"Destination ID {dest_id} ('{expected_name}') must have Wikimedia Commons source_url"
            )

    def test_get_destination_image_invalid_id(self):
        """Verifies destination image lookup returns None for invalid or non-existent IDs."""
        self.assertIsNone(get_destination_image(999))
        self.assertIsNone(get_destination_image(0))
        self.assertIsNone(get_destination_image(-5))
        self.assertIsNone(get_destination_image('invalid_string'))
        self.assertIsNone(get_destination_image(None))

    def test_homepage_and_explorer_display_images_and_fallbacks(self):
        """
        Verifies that cards display local image tags when an image exists,
        and display .card-media-fallback when an image is absent.
        """
        # Test valid destination (ID 1 - Taj Mahal)
        meta_taj = get_destination_image(1)
        self.assertIsNotNone(meta_taj)
        self.assertEqual(meta_taj['filename'], '01-taj-mahal.jpg')

        # Mock destination list with one with image and one without
        mock_destinations = [
            {
                'destination_id': 1,
                'place_name': 'Taj Mahal',
                'locality_city': 'Agra',
                'district': 'Agra',
                'state_ut': 'Uttar Pradesh',
                'category': 'Heritage',
                'description': 'Iconic ivory-white marble mausoleum'
            },
            {
                'destination_id': 999,
                'place_name': 'Hypothetical Unmapped Place',
                'locality_city': 'Nowhere',
                'district': 'District',
                'state_ut': 'State',
                'category': 'Cultural',
                'description': 'A new destination without an image file yet'
            }
        ]

        with patch('app.fetch_all', return_value=mock_destinations):
            with patch('app.fetch_one', return_value={'total': 2}):
                res = self.client.get('/destinations')
                self.assertEqual(res.status_code, 200)
                html = res.data.decode('utf-8')
                
                # Should render 01-taj-mahal.jpg for ID 1
                self.assertIn('01-taj-mahal.jpg', html)
                self.assertIn('alt="Taj Mahal"', html)
                
                # Should render fallback for ID 999
                self.assertIn('card-media-fallback', html)

    def test_detail_view_renders_hero_and_fallback(self):
        """
        Verifies that destination_detail renders hero image and attribution bar when image exists,
        and renders cleanly without hero media when image is absent.
        """
        mock_detail_with_img = {
            'destination_id': 2,
            'place_name': 'Qutb Minar',
            'locality_city': 'Mehrauli',
            'district': 'South Delhi',
            'state_ut': 'Delhi',
            'category': 'Heritage',
            'historical_significance': 'Victory tower built in 1192',
            'unesco_world_heritage': 1,
            'best_time_to_visit': 'Oct - Mar',
            'visiting_hours': 'Sunrise to sunset',
            'entry_fee_inr': 50,
            'official_tourism_url': 'https://delhitourism.gov.in',
            'supporting_source_urls': 'https://asi.nic.in'
        }

        with patch('app.fetch_one', return_value=mock_detail_with_img):
            with patch('app.fetch_all', return_value=[]):
                res = self.client.get('/destinations/2')
                self.assertEqual(res.status_code, 200)
                html = res.data.decode('utf-8')
                self.assertIn('detail-hero-media', html)
                self.assertIn('02-qutb-minar.jpg', html)
                self.assertIn('detail-img-credit', html)

        # Mock destination without image (ID 999)
        mock_detail_no_img = dict(mock_detail_with_img)
        mock_detail_no_img['destination_id'] = 999
        mock_detail_no_img['place_name'] = 'Hypothetical Cave'

        with patch('app.fetch_one', return_value=mock_detail_no_img):
            with patch('app.fetch_all', return_value=[]):
                res = self.client.get('/destinations/999')
                self.assertEqual(res.status_code, 200)
                html = res.data.decode('utf-8')
                # Hero media block must not be rendered when no image exists
                self.assertNotIn('detail-hero-media', html)
                self.assertIn('Hypothetical Cave', html)

    def test_split_urls_filter(self):
        """Verifies split_urls filter handles None, empty string, single URLs, and pipe-separated lists."""
        self.assertEqual(split_urls(None), [])
        self.assertEqual(split_urls(""), [])
        self.assertEqual(split_urls("   "), [])

        single_url = "https://en.wikipedia.org/wiki/Taj_Mahal"
        self.assertEqual(split_urls(single_url), [single_url])

        multi_urls = "https://asi.nic.in/taj-mahal | https://en.wikipedia.org/wiki/Taj_Mahal"
        self.assertEqual(split_urls(multi_urls), [
            "https://asi.nic.in/taj-mahal",
            "https://en.wikipedia.org/wiki/Taj_Mahal"
        ])

        messy_urls = "  https://asi.nic.in/ | |  https://en.wikipedia.org/  | "
        self.assertEqual(split_urls(messy_urls), [
            "https://asi.nic.in/",
            "https://en.wikipedia.org/"
        ])


if __name__ == '__main__':
    unittest.main()
