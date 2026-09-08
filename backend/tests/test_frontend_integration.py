import unittest
import os
import re

class TestFrontendIntegration(unittest.TestCase):
    def test_frontend_has_katex_and_id(self):
        html_file = 'sandhana_mathematical_equation_editor_derivation_workbench_production/code.html'
        if not os.path.exists(html_file):
            html_file = '../' + html_file

        with open(html_file, 'r') as f:
            content = f.read()

        self.assertIn('katex.min.css', content, "KaTeX CSS not found")
        self.assertIn('katex.min.js', content, "KaTeX JS not found")

        # Verify DOM element IDs exist in HTML tags, not just JS strings
        self.assertRegex(content, r'<[^>]+id="visual-equation-display"[^>]*>', "Visual equation display ID not found in HTML tag")
        self.assertRegex(content, r'<[^>]+id="equation-latex-display"[^>]*>', "LaTeX equation display ID not found in HTML tag")

    def test_frontend_has_dynamic_provenance(self):
        html_file = 'sandhana_mathematical_equation_editor_derivation_workbench_production/code.html'
        if not os.path.exists(html_file):
            html_file = '../' + html_file

        with open(html_file, 'r') as f:
            content = f.read()

        self.assertRegex(content, r'<[^>]+id="prov-parent"[^>]*>')
        self.assertRegex(content, r'<[^>]+id="symbol-dictionary"[^>]*>')

if __name__ == '__main__':
    unittest.main()
