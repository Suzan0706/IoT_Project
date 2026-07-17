from django.test import SimpleTestCase
from django.urls import reverse


class AutoReloadTests(SimpleTestCase):
    def test_auto_reload_status_endpoint_returns_json(self):
        with self.settings(DEBUG=True):
            response = self.client.get(reverse('auto_reload_status'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('reload', data)
        self.assertIn('timestamp', data)
        self.assertIn('files', data)
        self.assertIsInstance(data['reload'], bool)
