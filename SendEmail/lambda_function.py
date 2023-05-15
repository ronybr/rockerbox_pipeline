"""
This lambda function is used to send the email with the attachments to Rockerbox
"""
import boto3
import os
import ast
import logging
import pandas as pd
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Define the aws services to use
REGION = 'eu-central-1'
s3 = boto3.resource(service_name='s3', region_name=REGION)
ses = boto3.client(service_name='ses', region_name=REGION)
ssm = boto3.client('ssm', REGION)

param_store_name = os.environ.get("param_store_name")
ssm_params = ast.literal_eval(ssm.get_parameter(Name=f'{param_store_name}')['Parameter']['Value'])

body_text = ssm_params["body_text"]
bucket_name = ssm_params["bucket_name"]
key = ssm_params["key"]

# Define and create the temporary folder on AWS Lambda function
TEMP_FOLDER = "/tmp/rockerbox/in"
TEMP_FOLDER_OUT = "/tmp/rockerbox/out"


def create_multipart_message(sender: str, recipients: list, title: str, file_extension: str, partition_date: str,
                             data_source: str, text: str = None, attachments: list = None) \
        -> MIMEMultipart:
    """
    Creates a MIME multipart message object.
    Uses only the Python `email` standard library.
    Emails, both sender and recipients, can be just the email string or have the format 'The Name <the_email@host.com>'.

    :param sender: The sender.
    :param recipients: List of recipients. Needs to be a list, even if only one recipient.
    :param title: The title of the email.
    :param file_extension: csv, txt...
    :param partition_date: 20211209
    :param data_source: The platform or the system that provide the data. Ex.: Rivery, Google ADS, etc...
    :param text: The text version of the email body (optional).
    :param attachments: List of files to attach in the email.
    :return: A `MIMEMultipart` to be used to send the email.
    """
    try:
        multipart_content_subtype = 'alternative'
        msg = MIMEMultipart(multipart_content_subtype)
        msg['Subject'] = title
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Bcc'] = 'dev@mediascale.eu'

        # Record the MIME types of both parts - text/plain
        part = MIMEText(text, 'plain')
        msg.attach(part)

        # Add attachments
        for attachment in attachments or []:
            with open(attachment, 'rb') as f:
                part = MIMEApplication(f.read())
                part.add_header('Content-Disposition', 'attachment',
                                filename=f"{data_source}_{partition_date}.{file_extension}")
                msg.attach(part)
    except Exception as error:
        raise error

    return msg


def send_mail(sender: str, recipients: list, title: str, file_extension: str, partition_date: str, data_source: str,
              text: str = None, attachments: list = None) -> dict:
    """
    Send email to recipients.
    The sender needs to be a verified email in SES.
    :param sender: The sender.
    :param recipients: List of recipients. Needs to be a list, even if only one recipient.
    :param title: The title of the email.
    :param file_extension: csv, txt...
    :param partition_date: 20211209
    :param data_source: The platform or the system that provide the data. Ex.: Rivery, Google ADS, etc...
    :param text: The text version of the email body (optional).
    :param attachments: List of files to attach in the email.
    :return: The execution of the function to send the email
    """

    try:
        msg = create_multipart_message(sender, recipients, title, file_extension, partition_date, data_source,
                                       text, attachments)
        # Execute the function to send the email

        recipients.append("dev@mediascale.eu")
        return ses.send_raw_email(Source=sender, Destinations=recipients, RawMessage={'Data': msg.as_string()})
    except ClientError as error:
        raise error


def lambda_handler(event, context):
    """
    Send the email with the attachments to Rockerbox
    :param event:
    :param context:
    :return:
    """

    global receiver

    for objs in s3.Bucket(bucket_name).objects.filter(Prefix=key):

        # print(objs, objs.get()['ContentType'])

        # Check if the object is a file
        if objs.get()['ContentType'].__contains__("octet-stream"):

            # Collect the keys
            obj_key = objs.key
            # Get the data source
            data_source = obj_key.split('/')[-2]

            # Get the email receiver
            if data_source.__contains__("belgium"):
                receiver = [ssm_params["receiver"][0]]
            elif data_source.__contains__("netherlands"):
                receiver = [ssm_params["receiver"][1]]

            # Get the file name
            file_name = obj_key.split('/')[-1]

            try:
                # Get the partition date
                partition_date = obj_key.split('/')[-3]

                os.makedirs(TEMP_FOLDER, exist_ok=True)
                os.makedirs(TEMP_FOLDER_OUT, exist_ok=True)

                logger.info(f"Downloading from s3: {obj_key}")
                s3.Bucket(bucket_name).download_file(obj_key, f'{TEMP_FOLDER}/{file_name}')
            except Exception as error:
                logger.error(f"Error to download file {file_name}, please check the log!")
                raise error
            else:
                try:
                    logger.info("Starting the email process...")

                    # Convert csv to xlsx
                    # read_file = pd.read_csv(f'{TEMP_FOLDER}/{file_name}', delimiter=',')
                    read_file = pd.read_parquet(f'{TEMP_FOLDER}/{file_name}')
                    read_file.to_excel(f'{TEMP_FOLDER_OUT}/{file_name}.xlsx', index=None, header=True)

                    # Send the params to send the email
                    send_mail(sender=ssm_params["sender"], recipients=receiver,
                              title=ssm_params["subject"],
                              file_extension='xlsx', partition_date=partition_date, data_source=data_source,
                              text=body_text, attachments=[f'{TEMP_FOLDER_OUT}/{file_name}.xlsx'])
                except Exception as error:
                    raise error
                else:
                    # Delete file from temporary folder on Lambda /tmp
                    os.remove(f'{TEMP_FOLDER}/{file_name}')
                    os.remove(f'{TEMP_FOLDER_OUT}/{file_name}.xlsx')
                    # Delete file from temporary folder on s3 /tmp
                    s3.Object(bucket_name, obj_key).delete()
                    logger.info(f"Email sent. Date: {partition_date}, file: {obj_key}")

    return event
