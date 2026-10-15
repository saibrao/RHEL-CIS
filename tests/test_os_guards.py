"""Run the real first task of each role against synthetic facts, without hardening.

Requires ansible-playbook and PyYAML (included with ansible-core).
Run: python -m unittest discover -s tests -v
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class OSGuardTests(unittest.TestCase):
    def test_guards_stop_before_configuration(self):
        executable = shutil.which("ansible-playbook")
        self.assertIsNotNone(executable, "ansible-playbook must be on PATH")
        for major in (6, 7):
            role = ROOT / f"rhel{major}-cis/roles/cis"
            tasks = yaml.safe_load((role / "tasks/main.yml").read_text())
            guard = tasks[0]
            self.assertIn("fail", guard, "OS guard must precede every other task")
            self.assertIn("always", guard["tags"])
            metadata = yaml.safe_load((role / "meta/main.yml").read_text())
            self.assertEqual(metadata.get("dependencies", []), [])
            cases = {
                "supported_rhel": ("RedHat", str(major), "RedHat", True),
                "supported_centos": ("RedHat", major, "CentOS", True),
                "wrong_family_same_version": ("Debian", str(major), "Debian", False),
                "wrong_family_wrong_version": ("Debian", "22", "Ubuntu", False),
                "wrong_major": ("RedHat", str(13 - major), "RedHat", False),
                "newer_major": ("RedHat", "9", "RedHat", False),
                "missing_family": (None, str(major), "RedHat", False),
                "missing_version": ("RedHat", None, "RedHat", False),
                "missing_facts": (None, None, None, False),
            }
            hosts = {}
            for name, (family, version, distribution, _) in cases.items():
                hosts[name] = {
                    key: value for key, value in {
                        "ansible_os_family": family,
                        "ansible_distribution_major_version": version,
                        "ansible_distribution": distribution,
                    }.items() if value is not None
                }
            for mode in ([], ["--tags", "section1"], ["--check", "--diff"]):
                with self.subTest(major=major, mode=mode), tempfile.TemporaryDirectory() as tmp:
                    directory = Path(tmp)
                    inventory = directory / "inventory.yml"
                    inventory.write_text(yaml.safe_dump({"all": {"hosts": hosts}}))
                    playbook = directory / "guard.yml"
                    # Only the production guard is executed. The sentinel represents
                    # the first configuration change; no hardening task is loaded.
                    playbook.write_text(yaml.safe_dump([{
                        "hosts": "all", "gather_facts": False,
                        "tasks": [guard, {
                            "name": "Configuration sentinel",
                            "debug": {"msg": "Reached configuration"},
                            "changed_when": True, "tags": ["section1"],
                        }],
                    }]))
                    config = directory / "ansible.cfg"
                    config.write_text("[defaults]\nretry_files_enabled = False\n")
                    env = dict(os.environ, ANSIBLE_CONFIG=str(config),
                               ANSIBLE_NOCOLOR="1", ANSIBLE_LOCAL_TEMP=str(directory / "local"))
                    result = subprocess.run(
                        [executable, "-i", str(inventory), str(playbook), *mode],
                        cwd=tmp, env=env, text=True, capture_output=True, timeout=60,
                    )
                    output = result.stdout + result.stderr
                    self.assertEqual(result.returncode, 2, output)
                    for host, (*_, supported) in cases.items():
                        recap = re.search(
                            rf"^{host}\s+: ok=(\d+)\s+changed=(\d+)\s+unreachable=(\d+)\s+failed=(\d+)",
                            output, re.MULTILINE,
                        )
                        self.assertIsNotNone(recap, output)
                        expected = (1, 1, 0, 0) if supported else (0, 0, 0, 1)
                        self.assertEqual(tuple(map(int, recap.groups())), expected, output)
                    self.assertNotIn("undefined", output.lower(), output)


if __name__ == "__main__":
    unittest.main()
