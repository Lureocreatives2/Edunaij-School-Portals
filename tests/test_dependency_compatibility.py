"""Exercise report and token behavior affected by security updates."""
import copy
import time
from io import BytesIO

import jwt
from django.test import SimpleTestCase
from PIL import Image
from pypdf import PdfReader
from xhtml2pdf import pisa


class DependencyCompatibilityTests(SimpleTestCase):
    def test_image_decoding_and_report_generation(self):
        image_buffer = BytesIO()
        Image.new('RGB', (32, 32), color='green').save(image_buffer, format='PNG')
        image_buffer.seek(0)
        with Image.open(image_buffer) as uploaded_image:
            uploaded_image.verify()
        output = BytesIO()
        result = pisa.CreatePDF('<html><body><h1>School report</h1><p>SSS 1</p></body></html>', dest=output)
        self.assertFalse(result.err)
        output.seek(0)
        report = PdfReader(output)
        self.assertIn('School report', report.pages[0].extract_text())

    def test_jwt_decode_preserves_options_and_expiry_checks(self):
        key = 'dependency-regression-only-' + '8f3d6a2c' * 8
        options = {'require': ['exp']}
        original = copy.deepcopy(options)
        valid = jwt.encode({'exp': int(time.time()) + 300, 'sub': 'example'}, key, algorithm='HS256')
        self.assertEqual(jwt.decode(valid, key, algorithms=['HS256'], options=options)['sub'], 'example')
        self.assertEqual(options, original)
        expired = jwt.encode({'exp': int(time.time()) - 60, 'sub': 'example'}, key, algorithm='HS256')
        with self.assertRaises(jwt.ExpiredSignatureError):
            jwt.decode(expired, key, algorithms=['HS256'], options=options)
