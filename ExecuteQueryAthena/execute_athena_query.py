import boto3
import botocore

athena_client = boto3.client('athena')


class AthenaProcess:

    def __init__(self, bucket):
        self._bucket = boto3.resource('s3').Bucket(bucket)
        self._s3 = boto3.session.Session().client('s3')

    @staticmethod
    def start_query(query, workgroup='primary'):

        try:
            athena_response = athena_client.start_query_execution(
                QueryString=query,
                ResultConfiguration={
                    'OutputLocation': 's3://mediascale-datalake-dev/temp/',
                    'EncryptionConfiguration': {
                        'EncryptionOption': 'SSE_S3'
                    }
                },
                WorkGroup=workgroup
            )
        except botocore.exceptions.ClientError as error:
            raise error
        else:
            return athena_response

    @staticmethod
    def check_query_execution(query_execution_id):

        try:
            execution_response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            query_status = execution_response['QueryExecution']['Status']['State']
            print(f"FUNC: {query_status}")

        except botocore.exceptions.ClientError as error:
            raise error
        else:
            return query_status

    def delete_partition(self, s3_key):
        self._s3.delete_object(Bucket=self._bucket.name, Key=s3_key)
