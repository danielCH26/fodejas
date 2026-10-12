"""MinIO bucket initialization (INF-008 / Gap #6).

Replaces the mc-based init (docker/minio-init/lifecycle.sh) for
environments where the minio/mc image cannot be pulled. Uses boto3
(available via django-storages) against the S3-compatible endpoint:

1. Ensure the bucket exists (create if missing).
2. Enable bucket versioning (roadmap.md acceptance: versionado).
3. Lifecycle rules: noncurrent versions expire after 90 days and
   incomplete multipart uploads are aborted after 7 days.

Idempotent: safe to run on every deploy.

Run inside the app container (has boto3 + env vars):
    python scripts/minio_init.py
"""

from __future__ import annotations

import os
import sys

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

BUCKET = os.environ.get("AWS_STORAGE_BUCKET_NAME", "fodejas-media")
ENDPOINT = os.environ.get("AWS_S3_ENDPOINT_URL", "http://minio:9000")
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
SECRET_KEY = os.environ.get(
    "AWS_SECRET_ACCESS_KEY", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
)

NONCURRENT_EXPIRY_DAYS = 90
INCOMPLETE_UPLOAD_ABORT_DAYS = 7


def main() -> int:
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=os.environ.get("AWS_S3_REGION_NAME", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )

    # 1. Bucket
    try:
        s3.head_bucket(Bucket=BUCKET)
        print(f"[minio-init] bucket '{BUCKET}' exists")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=BUCKET)
            print(f"[minio-init] bucket '{BUCKET}' created")
        else:
            raise

    # 2. Versioning
    s3.put_bucket_versioning(
        Bucket=BUCKET, VersioningConfiguration={"Status": "Enabled"}
    )
    status = s3.get_bucket_versioning(Bucket=BUCKET).get("Status")
    print(f"[minio-init] versioning: {status}")

    # 3. Lifecycle: noncurrent expiry + incomplete multipart abort
    s3.put_bucket_lifecycle_configuration(
        Bucket=BUCKET,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "expire-noncurrent-versions",
                    "Status": "Enabled",
                    "Filter": {},
                    "NoncurrentVersionExpiration": {
                        "NoncurrentDays": NONCURRENT_EXPIRY_DAYS,
                    },
                },
                {
                    "ID": "abort-incomplete-multipart",
                    "Status": "Enabled",
                    "Filter": {},
                    "AbortIncompleteMultipartUpload": {
                        "DaysAfterInitiation": INCOMPLETE_UPLOAD_ABORT_DAYS,
                    },
                },
            ]
        },
    )
    rules = s3.get_bucket_lifecycle_configuration(Bucket=BUCKET)["Rules"]
    print(f"[minio-init] lifecycle rules active: {[r['ID'] for r in rules]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
