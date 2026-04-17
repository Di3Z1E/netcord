import unittest
from unittest.mock import patch, MagicMock
from src.netcord.core import get_adapters, get_public_ip, ping_host

class TestCore(unittest.TestCase):
    @patch("src.netcord.core.run_cmd")
    def test_get_adapters(self, mock_run):
        mock_run.return_value = ("Ethernet\nWi-Fi\n", "", 0)
        adapters = get_adapters()
        self.assertEqual(adapters, ["Ethernet", "Wi-Fi"])

    @patch("urllib.request.urlopen")
    def test_get_public_ip(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"1.2.3.4"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        self.assertEqual(get_public_ip(), "1.2.3.4")

    @patch("src.netcord.core.run_cmd")
    def test_ping_host(self, mock_run):
        mock_run.return_value = ("Reply from 8.8.8.8...", "", 0)
        result = ping_host("8.8.8.8")
        self.assertIn("Reply from 8.8.8.8", result)

if __name__ == "__main__":
    unittest.main()
