import json

import pytest
import responses

from pdc_api.client import upload_file_to_s3_presigned_url
from pdc_api.errors import PDCServiceError
from pdc_api.models import File, PresignedPost

PRESIGNED_URL = "https://s3.example.com/upload"

PRESIGNED_FIELDS = {
    "bucket": "test-bucket",
    "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
    "key": "test-key",
    "Policy": "test-policy",
    "X-Amz-Signature": "test-sig",
}


@pytest.fixture()
def presigned_post():
    return PresignedPost(url=PRESIGNED_URL, fields=PRESIGNED_FIELDS)


@pytest.fixture()
def stub_s3_upload():

    def _stub(*, status=204):
        responses.add(method=responses.POST, url=PRESIGNED_URL, status=status)

    return _stub


class TestUploadFileToS3PresignedUrl:
    def test_uploads_successfully(self, presigned_post, stub_s3_upload):
        stub_s3_upload()

        upload_file_to_s3_presigned_url(
            presigned_post=presigned_post,
            file_data=b"data",
            file_name="test.pdf",
            content_type="application/pdf",
        )

    def test_raises_on_failure(self, presigned_post, stub_s3_upload):
        stub_s3_upload(status=403)

        with pytest.raises(PDCServiceError):
            upload_file_to_s3_presigned_url(
                presigned_post=presigned_post,
                file_data=b"file content",
                file_name="test.pdf",
                content_type="application/pdf",
            )


class TestFile:
    def test_keeps_presigned_download_url_as_plain_string(self):
        url = (
            "https://my-bucket.s3.us-east-1.amazonaws.com/files/report%20%28final%29.pdf"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600&X-Amz-Signature=abc123"
        )

        file = File.model_validate({"id": 1, "name": "report (final).pdf", "downloadUrl": url})

        assert isinstance(file.download_url, str)
        assert file.download_url == url
        assert json.loads(json.dumps(file.model_dump()))["download_url"] == url
