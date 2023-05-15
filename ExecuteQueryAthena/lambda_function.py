import os
import time
import execute_athena_query

params = {
    "sql_files_path": "./sql_files/",
    "bucket": "mediascale-datalake-",
    'athena_output_location': 's3://mediascale-datalake-dev/temp/'
}


def lambda_handler(event, context):
    # Get SQl files
    file_path = "./sql_files/"
    list_folders = [f.path for f in os.scandir(file_path) if f.is_dir()]

    list_files = []
    for path in list_folders:
        for filename in os.scandir(path):
            file_path_complete = f"{path}/{filename.name}"
            list_files.append(file_path_complete)

    # sort list in-place in alphabetical order
    list_files.sort()

    for file in list_files:

        try:
            # Read SQL file
            with open(file, 'r') as sql_query:
                query_string = sql_query.read()
                print(f"Executing file: {file}")

                # Create object
                obj_athena = execute_athena_query.AthenaProcess(bucket="mediascale-datalake-dev")
                # Start Query on Athena
                query_details = obj_athena.start_query(query=query_string)

                # Check query status
                query_status = obj_athena.check_query_execution(query_execution_id=query_details['QueryExecutionId'])

                waiting_status = ["QUEUED", "RUNNING"]
                while query_status in waiting_status:
                    print(f"Query status: {query_status}")
                    # Wait 30 secs
                    time.sleep(30)
                    # Check query status again
                    query_status = obj_athena.check_query_execution(
                        query_execution_id=query_details['QueryExecutionId'])

                    if query_status == "SUCCEEDED":
                        print({"Message": "Query finished", "Sql": file})

                        continue
        except Exception as error:
            raise error
        else:
            print("Application finished")

    return event
