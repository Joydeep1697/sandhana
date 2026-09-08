import unittest
import threading
import http.server
import socketserver
import uvicorn
import time
import os
from playwright.sync_api import sync_playwright

class TestE2EEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We need to run the frontend server and backend API server
        # We will use ports 8005 (frontend) and 8000 (backend) to avoid conflicts

        # Start Backend
        cls.api_thread = threading.Thread(target=uvicorn.run, kwargs={
            'app': 'core.fastapi_app:app', 'host': '127.0.0.1', 'port': 8000, 'log_level': 'error'
        }, daemon=True)
        cls.api_thread.start()

        # Start Frontend
        cls.httpd = socketserver.TCPServer(("127.0.0.1", 8005), http.server.SimpleHTTPRequestHandler)
        cls.http_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.http_thread.start()

        time.sleep(2) # Wait for servers to start

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_end_to_end_editor_flow(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Setup console and network logging
            console_errors = []
            failed_requests = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
            page.on("requestfailed", lambda req: failed_requests.append(req.url))

            # 1. Equation editor page loads
            # URL relative to where simpleHTTP server is running (usually project root)
            page.goto("http://localhost:8005/sandhana_mathematical_equation_editor_derivation_workbench_production/code.html")

            # 2. Canonical equation is fetched
            # Wait for KaTeX to render. It happens after fetch completes.
            page.wait_for_selector(".katex", timeout=5000)

            # 3. #visual-equation-display contains actual KaTeX-rendered output
            visual_html = page.locator("#visual-equation-display").inner_html()
            self.assertIn("katex", visual_html)
            self.assertIn("rho", visual_html)

            # 4. Click "Edit: Change Sign"
            # 5. Verify /api/equation/edit is called (we wait for network idle)
            with page.expect_response("**/api/equation/edit") as response_info:
                page.locator("#btn-edit-valid").click()
            response = response_info.value
            self.assertEqual(response.status, 200)

            # 6. Verify returned AST/LaTeX changes
            data = response.json()
            self.assertIn("+", data['latex'])

            # 7. Verify visible rendered equation changes
            # Let's wait a moment for UI to update
            time.sleep(0.5)
            new_latex_ui = page.locator("#equation-latex-display").text_content()
            self.assertIn("+", new_latex_ui)

            # 8. Verify validation state updates
            # It was valid before, should still be valid, but let's check it says "Passed"
            status = page.locator("xpath=//span[contains(text(), 'Formal Validation:')]/following-sibling::span").text_content()
            self.assertIn("Passed", status)

            # 9. Click "Edit: Break Dimension"
            with page.expect_response("**/api/equation/edit") as response_info:
                page.locator("#btn-edit-invalid").click()

            # Wait for UI to update
            time.sleep(0.5)

            # 10. Verify structured diagnostic
            diagnostics = page.locator(".diagnostic-msg").all_inner_texts()
            self.assertGreater(len(diagnostics), 0)
            self.assertTrue(any("unknown_sym" in d for d in diagnostics))

            # 11. Verify Provenance and Epistemic Invariant remain synchronized
            prov_parent = page.locator("#prov-parent").text_content()
            self.assertIn("#EQ-098-B1", prov_parent)

            invariant = page.locator("#epistemic-invariant").text_content()
            self.assertIn("Formal mathematical correctness", invariant)

            # 12. Verify no console errors (other than the 404s for favicon which we ignore)
            real_errors = [e for e in console_errors if "favicon" not in e.lower()]
            self.assertEqual(len(real_errors), 0, f"Found console errors: {real_errors}")

            real_failed_reqs = [r for r in failed_requests if "favicon" not in r.lower()]
            self.assertEqual(len(real_failed_reqs), 0, f"Found failed requests: {real_failed_reqs}")

            # 13. Verify navigation works
            # Click a nav link
            page.locator("a[data-path='investigation-command-center']").click()
            page.wait_for_load_state('networkidle')
            self.assertIn("sandhana_investigation_command_center", page.url)

            browser.close()

if __name__ == '__main__':
    unittest.main()
