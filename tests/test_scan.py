import subprocess
import unittest
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from pyatv_cli.cli import _discover_avahi_hosts, cli


class AvahiScanTests(unittest.TestCase):
    @patch("pyatv_cli.cli.subprocess.run")
    def test_discovers_unique_ipv4_hosts_from_apple_tv_services(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                "=;eth0;IPv4;Apple TV;_airplay._tcp;local;appletv.local;"
                "192.168.1.191;7000;\"model=AppleTV5,3\"\n"
                "=;eth0;IPv6;Apple TV;_airplay._tcp;local;appletv.local;"
                "192.168.1.191;7000;\"model=AppleTV5,3\"\n"
                "=;eth0;IPv4;Roku;_airplay._tcp;local;roku.local;"
                "192.168.1.219;7000;\"model=3941X2\"\n"
                "=;eth0;IPv4;Roku;_unrelated._tcp;local;roku.local;"
                "192.168.1.219;7000;\n"
            ),
        )

        self.assertEqual(_discover_avahi_hosts(5), ["192.168.1.191"])
        self.assertEqual(run.call_count, 3)

    @patch("pyatv_cli.cli.pyatv.scan", new_callable=AsyncMock)
    @patch("pyatv_cli.cli._discover_avahi_hosts", return_value=["192.168.1.191"])
    def test_avahi_option_probes_discovered_hosts_with_pyatv(self, _discover, scan):
        scan.return_value = []

        result = CliRunner().invoke(cli, ["scan", "--avahi"])

        self.assertEqual(result.exit_code, 0, result.output)
        scan.assert_awaited_once()
        self.assertEqual(scan.await_args.kwargs["hosts"], ["192.168.1.191"])


if __name__ == "__main__":
    unittest.main()
