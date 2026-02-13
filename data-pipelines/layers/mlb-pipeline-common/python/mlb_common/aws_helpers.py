"""
Shared AWS helpers for S3 and DynamoDB operations.
"""
import io
import json
import logging
import boto3
import pandas as pd

logger = logging.getLogger(__name__)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')


# --- S3 ---

def read_csv_from_s3(bucket, key):
    """Read a CSV file from S3 into a pandas DataFrame."""
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(io.BytesIO(obj['Body'].read()))


def write_csv_to_s3(df, bucket, key):
    """Write a pandas DataFrame to S3 as CSV."""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())
    logger.info(f"Wrote CSV to s3://{bucket}/{key}")


def append_csv_to_s3(df, bucket, key):
    """Append rows to an existing CSV in S3 (or create if it doesn't exist)."""
    try:
        existing_df = read_csv_from_s3(bucket, key)
        df = pd.concat([existing_df, df], ignore_index=True)
    except s3.exceptions.NoSuchKey:
        pass
    write_csv_to_s3(df, bucket, key)


def write_json_to_s3(data, bucket, key):
    """Write a Python dict/list to S3 as JSON."""
    body = json.dumps(data, default=str)
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType='application/json')
    logger.info(f"Wrote JSON to s3://{bucket}/{key}")


def read_json_from_s3(bucket, key):
    """Read a JSON file from S3 into a Python dict/list."""
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj['Body'].read().decode('utf-8'))


def write_parquet_to_s3(df, bucket, key):
    """Write a pandas DataFrame to S3 as Parquet."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pandas(df)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    logger.info(f"Wrote Parquet to s3://{bucket}/{key}")


# --- DynamoDB ---

def dynamo_put_item(table_name, item):
    """Put a single item into a DynamoDB table."""
    table = dynamodb.Table(table_name)
    table.put_item(Item=item)


def dynamo_scan(table_name):
    """Scan an entire DynamoDB table and return all items."""
    table = dynamodb.Table(table_name)
    response = table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    return items


def dynamo_get_item(table_name, key):
    """Get a single item from a DynamoDB table."""
    table = dynamodb.Table(table_name)
    response = table.get_item(Key=key)
    return response.get('Item')
