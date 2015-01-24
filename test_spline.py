from __future__ import print_function, unicode_literals

import unittest
import imp
import subprocess

spline = imp.load_source('spline', './spline')
Code, Context = spline.Code, spline.Context

class TestCode(unittest.TestCase):

    def test_code_imports(self):
        code = spline.Code(spline.Context()).imports('re')
        self.assertEqual(1, len(code._imports))

    def test_code_imports_missing_module(self):
        with self.assertRaises(spline.Unsupported):
            code = spline.Code(spline.Context()).imports('missing')
            self.assertEqual(0, len(code._imports))


class TestEndToEnd(unittest.TestCase):

    def _run(self, cmdline):
        return subprocess.check_output(cmdline.format(spline='./spline'),
                                       shell=True)

    def test_simple(self):
        self.assertEqual(b'55\n', self._run('seq 10 | {spline} to_int sum'))
