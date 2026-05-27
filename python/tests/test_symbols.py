import platform
import shutil
import subprocess
import unittest

import eddsa._eddsa as _eddsa


class SymbolExportTests(unittest.TestCase):
    @unittest.skipUnless(platform.system() == "Linux", "ELF symbol check")
    def test_extension_exports_only_module_init(self):
        nm = shutil.which("nm")
        if nm is None:
            self.skipTest("nm is not installed")

        output = subprocess.check_output(
            [nm, "-D", "--defined-only", _eddsa.__file__],
            text=True,
        )
        exported = {
            line.split()[-1].split("@@", 1)[0].split("@", 1)[0]
            for line in output.splitlines()
            if line.strip()
        }
        allowed = {"PyInit__eddsa", "PYEDDSA_0.8"}

        self.assertLessEqual(exported, allowed)
        self.assertIn("PyInit__eddsa", exported)


if __name__ == "__main__":
    unittest.main()
