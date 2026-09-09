import unittest
from unittest.mock import patch

from Ammeters.client import AmmeterClientError, request_current_from_ammeter


class AmmeterClientTests(unittest.TestCase):
    @patch("Ammeters.client.socket")
    def test_returns_finite_measurement(self, socket_factory):
        connection = socket_factory.return_value.__enter__.return_value
        connection.recv.return_value = b" 2.5\n"

        self.assertEqual(request_current_from_ammeter(5000, b"MEASURE"), 2.5)

    @patch("Ammeters.client.socket")
    def test_wraps_connection_failure(self, socket_factory):
        connection = socket_factory.return_value.__enter__.return_value
        connection.connect.side_effect = OSError("connection refused")

        with self.assertRaisesRegex(AmmeterClientError, "Could not communicate"):
            request_current_from_ammeter(5000, b"MEASURE")

    @patch("Ammeters.client.socket")
    def test_rejects_non_finite_measurement(self, socket_factory):
        connection = socket_factory.return_value.__enter__.return_value
        connection.recv.return_value = b"nan"

        with self.assertRaisesRegex(AmmeterClientError, "Non-finite"):
            request_current_from_ammeter(5000, b"MEASURE")

    def test_validates_client_arguments(self):
        with self.assertRaises(ValueError):
            request_current_from_ammeter(0, b"MEASURE")
        with self.assertRaises(ValueError):
            request_current_from_ammeter(5000, b"", timeout=0)


if __name__ == "__main__":
    unittest.main()