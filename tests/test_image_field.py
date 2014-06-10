import json
import os

from six.moves.urllib.parse import urljoin

from django.core.files import File
from django.core.exceptions import ValidationError
from django.test import TestCase

from djbetty.conf import settings
from testproject.testapp.models import TestModel

from httmock import urlmatch, HTTMock
import requests  # noqa


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'images')

TEST_IMAGE_DATA = json.dumps({
    "id": 12345,
    "name": "Lenna.png",
    "width": 512,
    "height": 512,
    "credit": "Lena Soderberg",
    "selections": {}
}).encode("UTF-8")


@urlmatch(path=r'.*api/new$')
def betty_new_mock(url, request):
    return {
        "status_code": 200,
        "content": TEST_IMAGE_DATA
    }


@urlmatch(path=r'.*api/12345.*$')
def betty_detail_mock(url, request):
    return {
        "status_code": 200,
        "content": TEST_IMAGE_DATA
    }


class ImageFieldTestCase(TestCase):

    def setUp(self):
        settings.BETTY_PUBLIC_TOKEN = "noop"
        self.base_url = urljoin("http://localhost:8081", settings.BETTY_IMAGE_URL)
        if self.base_url[-1] == "/":
            self.base_url = self.base_url[:-1]
        self._old_betty_image_url = settings.BETTY_IMAGE_URL
        settings.BETTY_IMAGE_URL = self.base_url

    def test_fileless_save(self):
        test_object = TestModel()
        test_object.listing_image = 12345
        test_object.save()

        self.assertEqual(test_object.listing_image.id, 12345)

    def test_validate(self):
        test_object = TestModel()
        test_object.image = 12345
        test_object.full_clean()

        test_object.image = None
        test_object.full_clean()

        test_object.image = "12345"
        test_object.full_clean()

        with self.assertRaises(ValidationError):
            test_object.image = "abcdef"
            test_object.full_clean()

    def test_charfield_save(self):
        """DRF seems to want to save fields it doesn't know about as CharFields,
        so if a string is passed in, let's handle it right."""
        test = TestModel()
        test.image = ""
        test.save()
        test = TestModel.objects.get(id=test.id)
        self.assertEqual(test.image, None)

    def test_save(self):
        lenna_path = os.path.join(TEST_DATA_PATH, 'Lenna.png')
        with open(lenna_path, "rb") as lenna:
            test = TestModel()
            with HTTMock(betty_new_mock):
                test.image.save("Lenna.png", File(lenna))

        with HTTMock(betty_detail_mock):
            self.assertEqual(test.image.name, "Lenna.png")

        test = TestModel.objects.get(id=test.id)
        with HTTMock(betty_detail_mock):
            self.assertEqual(test.image.name, "Lenna.png")

    def test_listing_image(self):
        lenna_path = os.path.join(TEST_DATA_PATH, 'Lenna.png')
        with open(lenna_path, "rb") as lenna:
            test = TestModel()
            with HTTMock(betty_new_mock):
                test.listing_image.save("Lenna.png", File(lenna))
        test.save()

        self.assertEqual(test.listing_image.alt, None)
        self.assertEqual(test.listing_image.caption, None)

    def test_alt_and_caption(self):
        lenna_path = os.path.join(TEST_DATA_PATH, 'Lenna.png')
        with open(lenna_path, "rb") as lenna:
            test = TestModel()
            with HTTMock(betty_new_mock):
                test.image.save("Lenna.png", File(lenna))

        test.image.alt = "Just a cool chick"
        test.image.caption = "Kind of sexist?"
        test.save()

        test = TestModel.objects.get(id=test.id)

        self.assertEqual(test.image.alt, "Just a cool chick")
        self.assertEqual(test.image.caption, "Kind of sexist?")
