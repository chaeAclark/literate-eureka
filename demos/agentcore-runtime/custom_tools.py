import re
import time
import json
import copy
import uuid
import boto3

from strands import tool
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple


@tool
def check_provider_availability(provider_id: str, date_str: str) -> Dict[str, Union[str, List[str]]]:
    """
    Check a provider's availability for a specific date.

    Args:
        provider_id (str): The provider's system ID (e.g., 'PROV-48271')
        date_str (str): Date in 'YYYY-MM-DD' format

    Returns:
        Dict containing provider ID, date, and available time slots
    """
    def generate_time_slots(start_time: str, end_time: str, interval_mins: int = 30) -> List[str]:
        time_format = '%H:%M'
        current = datetime.strptime(start_time, time_format)
        end = datetime.strptime(end_time, time_format)
        slots = []

        while current < end:
            slots.append(current.strftime(time_format))
            current += timedelta(minutes=interval_mins)

        return slots

    dynamodb = boto3.resource('dynamodb')
    providers_table = dynamodb.Table('practice_info_table')
    appointments_table = dynamodb.Table('practice_appointments_table')

    # Convert date string to datetime object to get day of week
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    day_of_week = date_obj.strftime('%A').lower()
    day_key = f"{day_of_week}_hours"

    # Get provider details
    provider = providers_table.get_item(Key={'system_id': provider_id}).get('Item', {})
    if not provider or 'operation_hours' not in provider:
        return {
            'provider_id': provider_id,
            'date': date_str,
            'day_of_week': day_of_week.capitalize(),
            'available_slots': [],
            'error': 'Provider not found or no operating hours defined'
        }

    # Check if provider works on this day
    hours_key = f"{day_of_week}_hours"
    if hours_key not in provider['operation_hours']:
        return {
            'provider_id': provider_id,
            'date': date_str,
            'day_of_week': day_of_week.capitalize(),
            'available_slots': [],
            'message': f'Provider does not work on {day_of_week.capitalize()}'
        }

    # Get working hours for this day
    hours_str = provider['operation_hours'][hours_key]['S']
    start_time, end_time = hours_str.split(' - ')

    # Get all booked appointments for this provider on this date using scan instead of query
    response = appointments_table.scan(
        FilterExpression='provider_id = :pid AND appointment_date = :date',
        ExpressionAttributeValues={':pid': provider_id, ':date': date_str}
    )

    # Calculate all possible slots
    all_slots = generate_time_slots(start_time, end_time)

    # Remove booked slots
    booked_slots = [item['appointment_time'] for item in response.get('Items', [])]
    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    return {
        'provider_id': provider_id,
        'date': date_str,
        'day_of_week': day_of_week.capitalize(),
        'available_slots': available_slots
    }


@tool
def schedule_appointment(
    provider_id: str,
    patient_id: str,
    date_str: str,
    time_slot: str,
    duration_mins: int = 30,
    appointment_type: str = "Regular Checkup"
) -> Dict[str, str]:
    """
    Schedule a new appointment with a provider.
    """
    # No changes needed here as it doesn't use GSIs
    dynamodb = boto3.resource('dynamodb')
    appointments_table = dynamodb.Table('practice_appointments_table')

    # Check if the provider is available at this time
    availability = check_provider_availability(provider_id, date_str)
    if time_slot not in availability['available_slots']:
        return {
            'status': 'error',
            'message': f'Provider is not available at {time_slot} on {date_str}'
        }

    # Generate a unique appointment ID
    appointment_id = f"APPT-{str(uuid.uuid4())[:8]}"

    # Schedule the appointment
    appointments_table.put_item(
        Item={
            'appointment_id': appointment_id,
            'provider_id': provider_id,
            'patient_id': patient_id,
            'appointment_date': date_str,
            'appointment_time': time_slot,
            'duration_mins': duration_mins,
            'appointment_type': appointment_type,
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }
    )

    return {
        'status': 'success',
        'message': 'Appointment scheduled successfully',
        'appointment_id': appointment_id
    }


@tool
def cancel_appointment(appointment_id: str) -> Dict[str, str]:
    """
    Cancel an existing appointment.
    """
    # No changes needed here as it uses the primary key
    dynamodb = boto3.resource('dynamodb')
    appointments_table = dynamodb.Table('practice_appointments_table')

    try:
        # Check if appointment exists
        response = appointments_table.get_item(Key={'appointment_id': appointment_id})
        if 'Item' not in response:
            return {
                'status': 'error',
                'message': f'Appointment {appointment_id} not found'
            }

        # Update appointment status to cancelled
        appointments_table.update_item(
            Key={'appointment_id': appointment_id},
            UpdateExpression='SET #status = :status, cancelled_at = :cancelled_at',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'cancelled',
                ':cancelled_at': datetime.now().isoformat()
            }
        )

        return {
            'status': 'success',
            'message': 'Appointment cancelled successfully'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error cancelling appointment: {str(e)}'
        }


@tool
def get_patient_appointments(patient_id: str, status: Optional[str] = None) -> Dict:
    """
    Get all appointments for a specific patient, optionally filtered by status.
    """
    dynamodb = boto3.resource('dynamodb')
    appointments_table = dynamodb.Table('practice_appointments_table')

    # Get patient appointments using scan with filter instead of query
    if status:
        response = appointments_table.scan(
            FilterExpression='patient_id = :pid AND #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':pid': patient_id, ':status': status}
        )
    else:
        response = appointments_table.scan(
            FilterExpression='patient_id = :pid',
            ExpressionAttributeValues={':pid': patient_id}
        )

    return {
        'patient_id': patient_id,
        'appointments': response.get('Items', [])
    }


@tool
def get_provider_schedule(provider_id: str, date_str: Optional[str] = None) -> Dict:
    """
    Get a provider's schedule for a specific date or upcoming appointments.
    """
    dynamodb = boto3.resource('dynamodb')
    appointments_table = dynamodb.Table('practice_appointments_table')

    # Get provider schedule using scan with filter instead of query
    if date_str:
        response = appointments_table.scan(
            FilterExpression='provider_id = :pid AND appointment_date = :date AND #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':pid': provider_id, 
                ':date': date_str,
                ':status': 'scheduled'
            }
        )
        result = {
            'provider_id': provider_id,
            'date': date_str,
            'appointments': sorted(response.get('Items', []), key=lambda x: x['appointment_time'])
        }
    else:
        today = datetime.now().strftime('%Y-%m-%d')
        response = appointments_table.scan(
            FilterExpression='provider_id = :pid AND #status = :status AND appointment_date >= :today',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':pid': provider_id,
                ':status': 'scheduled',
                ':today': today
            }
        )
        result = {
            'provider_id': provider_id,
            'upcoming_appointments': sorted(
                response.get('Items', []), 
                key=lambda x: (x['appointment_date'], x['appointment_time'])
            )
        }

    return result


@tool
def get_athena_columns_info(
    db_name: str,
    table_name: str,
) -> List[Dict[str, str]]:
    """
    Retrieves a simplified list of columns and their data types.

    Args:
        db_name: Database name
        table_name: Table name

    Returns:
        List of dictionaries with column name and data type
    """
    region_name = 'us-east-1'

    def get_table_schema(
        db_name: str,
        table_name: str,
    ) -> Dict[str, Any]:
        """
        Retrieves detailed table schema information from AWS Glue Data Catalog.

        Args:
            db_name: Database name
            table_name: Table name

        Returns:
            Dict containing complete table schema information
        """
        region_name = 'us-east-1'

        try:
            # Initialize Glue client
            glue_client = boto3.client('glue', region_name=region_name)

            # Get table metadata from Glue catalog
            response = glue_client.get_table(
                DatabaseName=db_name,
                Name=table_name
            )

            return response['Table']
        except Exception as e:
            print(f"Error retrieving table schema: {str(e)}")
            raise
    try:
        # Get full schema
        schema = get_table_schema(db_name, table_name, region_name)

        # Extract just the column information
        columns = []
        for col in schema['StorageDescriptor']['Columns']:
            columns.append({
                'name': col['Name'],
                'type': col['Type'],
                'comment': col.get('Comment', '')
            })

        # Include partition keys if any
        if 'PartitionKeys' in schema and schema['PartitionKeys']:
            for partition in schema['PartitionKeys']:
                columns.append({
                    'name': partition['Name'],
                    'type': partition['Type'],
                    'comment': partition.get('Comment', ''),
                    'is_partition': True
                })

        return columns
    except Exception as e:
        print(f"Error retrieving columns info: {str(e)}")
        raise


@tool
def query_athena(
    db_name: str,
    table_name: str,
    columns: List[str] = None,
    filters: List[Dict[str, Any]] = None,
    group_by: List[str] = None,
    order_by: List[Tuple[str, str]] = None,
    limit: Optional[int] = 5,
    max_execution_time_seconds: int = 300
) -> List[Dict[str, Any]]:
    """
    Query AWS Athena with a controlled SELECT statement.

    Args:
        db_name: Database name
        table_name: Table name
        columns: List of columns to select (default: ['*'] for all columns)
        filters: List of filter dictionaries with format:
                [{'column': 'col_name', 'operator': '>', 'value': 10}]
                Supported operators: =, !=, >, <, >=, <=, LIKE, IN, NOT IN, IS NULL, IS NOT NULL
        group_by: List of columns to group by
        order_by: List of (column, direction) tuples for sorting
                Example: [("timestamp", "DESC"), ("user_id", "ASC")]
        limit: Maximum number of rows to return
        max_execution_time_seconds: Maximum execution time before timeout

    Returns:
        List of dictionaries containing query results
    """
    s3_output = 's3://chaeclrk-ags-tech-aiml-hcls-datasets/provider_search/athena_results/'
    region_name = 'us-east-1'
    # Default to all columns
    if not columns:
        columns = ['*']

    # Initialize boto3 client
    athena_client = boto3.client('athena', region_name=region_name)

    # Construct the SELECT query
    columns_str = ', '.join(columns) if columns != ['*'] else '*'
    query = f"SELECT {columns_str} FROM {db_name}.{table_name}"

    # Process WHERE conditions
    if filters and len(filters) > 0:
        where_clauses = []
        for filter_item in filters:
            column = filter_item.get('column')
            operator = filter_item.get('operator', '=')
            value = filter_item.get('value')

            # Handle different operator types
            if operator.upper() in ('IS NULL', 'IS NOT NULL'):
                where_clauses.append(f"{column} {operator}")
            elif operator.upper() in ('IN', 'NOT IN'):
                if not isinstance(value, (list, tuple)):
                    raise ValueError("Value for IN operator must be a list or tuple")
                formatted_values = []
                for v in value:
                    if isinstance(v, str):
                        formatted_values.append(f"'{v}'")
                    else:
                        formatted_values.append(str(v))
                values_str = ', '.join(formatted_values)
                where_clauses.append(f"{column} {operator} ({values_str})")
            elif operator.upper() in ('LIKE'):
                where_clauses.append(f"LOWER({column}) LIKE LOWER('{value}')")
            else:
                # Standard operators
                if operator not in ('=', '!=', '>', '<', '>=', '<='):
                    raise ValueError(f"Unsupported operator: {operator}")

                if isinstance(value, str):
                    where_clauses.append(f"{column} {operator} '{value}'")
                elif value is None:
                    where_clauses.append(f"{column} IS NULL")
                else:
                    where_clauses.append(f"{column} {operator} {value}")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

    # Add GROUP BY
    if group_by and len(group_by) > 0:
        query += " GROUP BY " + ", ".join(group_by)

    # Add ORDER BY
    if order_by and len(order_by) > 0:
        order_clauses = []
        for field, direction in order_by:
            if not re.match(r'^[a-zA-Z0-9_]+\$', field):
                raise ValueError(f"Invalid field name in ORDER BY: {field}")
            if direction.upper() not in ('ASC', 'DESC'):
                raise ValueError(f"Direction must be ASC or DESC, got: {direction}")
            order_clauses.append(f"{field} {direction.upper()}")
        query += " ORDER BY " + ", ".join(order_clauses)

    # Add LIMIT
    limit = min([10, limit])
    if limit:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Limit must be a positive integer")
        query += f" LIMIT {limit}"

    print(f"Executing Athena query: {query}")

    try:
        # Execute query
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': db_name},
            ResultConfiguration={'OutputLocation': s3_output}
        )

        query_execution_id = response['QueryExecutionId']

        # Wait for completion
        start_time = time.time()
        while True:
            query_status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            state = query_status['QueryExecution']['Status']['State']

            if state == 'SUCCEEDED':
                break
            elif state in ['FAILED', 'CANCELLED']:
                error_message = query_status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                raise Exception(f"Query {state}: {error_message}")

            if time.time() - start_time > max_execution_time_seconds:
                athena_client.stop_query_execution(QueryExecutionId=query_execution_id)
                raise TimeoutError(f"Query execution timed out after {max_execution_time_seconds} seconds")

            time.sleep(2)

        # Get results
        results = []
        column_names = []

        paginator = athena_client.get_paginator('get_query_results')
        for page in paginator.paginate(QueryExecutionId=query_execution_id):
            rows = page['ResultSet']['Rows']

            # Extract column names from first row of first page
            if not column_names and rows:
                column_names = [col['VarCharValue'] for col in rows[0]['Data']]
                rows = rows[1:]  # Skip header

            # Process data rows
            for row in rows:
                data = {}
                for i, value in enumerate(row['Data']):
                    data[column_names[i]] = value.get('VarCharValue')
                results.append(data)

        return results

    except Exception as e:
        print(f"Error executing Athena query: {str(e)}")
        raise


@tool
def get_dynamodb_schemas(table_name: str):
    """
    Get schema information for a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table

    Returns:
        Dictionary containing table schema information
    """
    sample_items = True
    sample_size = 3

    def infer_attribute_schema(
        table_name: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Infer attribute schema by sampling items from the table.

        Args:
            table_name: Name of the DynamoDB table

        Returns:
            Dictionary with attribute names and their inferred types
        """
        region_name = 'us-east-1'
        sample_size = 3

        # Initialize DynamoDB resource (for easier item access)
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
        table = dynamodb.Table(table_name)

        # Scan a sample of items
        response = table.scan(Limit=sample_size)
        items = response.get('Items', [])

        if not items:
            return {}

        # Analyze attributes
        attributes = {}
        for item in items:
            for attr_name, attr_value in item.items():
                # Determine the type of the attribute
                if isinstance(attr_value, str):
                    attr_type = 'String'
                elif isinstance(attr_value, (int, float)):
                    attr_type = 'Number'
                elif isinstance(attr_value, bool):
                    attr_type = 'Boolean'
                elif isinstance(attr_value, list):
                    attr_type = 'List'
                elif isinstance(attr_value, dict):
                    attr_type = 'Map'
                elif attr_value is None:
                    attr_type = 'Null'
                else:
                    attr_type = 'Unknown'

                # Update attribute information
                if attr_name not in attributes:
                    attributes[attr_name] = {
                        'type': attr_type,
                        'count': 1,
                    }
                else:
                    # If we see a different type, mark as mixed
                    if attributes[attr_name]['type'] != attr_type:
                        attributes[attr_name]['type'] = 'Mixed'
                    attributes[attr_name]['count'] += 1

        # Calculate frequency for each attribute
        total_items = len(items)
        for attr in attributes.values():
            attr['frequency'] = (attr['count'] / total_items) * 100

        return attributes

    region_name = 'us-east-1'
    try:
        # Initialize DynamoDB client and resource
        dynamodb_client = boto3.client('dynamodb', region_name=region_name)

        # Get table metadata
        response = dynamodb_client.describe_table(TableName=table_name)
        table_info = response['Table']

        # Extract key schema
        key_schema = {}
        for key in table_info['KeySchema']:
            key_type = key['KeyType']
            if key_type == 'HASH':
                key_schema['partition_key'] = {
                    'name': key['AttributeName'],
                    'type': next((attr['AttributeType'] for attr in table_info['AttributeDefinitions'] 
                                 if attr['AttributeName'] == key['AttributeName']), None)
                }
            elif key_type == 'RANGE':
                key_schema['sort_key'] = {
                    'name': key['AttributeName'],
                    'type': next((attr['AttributeType'] for attr in table_info['AttributeDefinitions'] 
                                 if attr['AttributeName'] == key['AttributeName']), None)
                }

        # Extract secondary indexes
        gsi = []
        if 'GlobalSecondaryIndexes' in table_info:
            for index in table_info['GlobalSecondaryIndexes']:
                gsi_keys = {}
                for key in index['KeySchema']:
                    key_type = 'partition_key' if key['KeyType'] == 'HASH' else 'sort_key'
                    gsi_keys[key_type] = {
                        'name': key['AttributeName'],
                        'type': next((attr['AttributeType'] for attr in table_info['AttributeDefinitions'] 
                                     if attr['AttributeName'] == key['AttributeName']), None)
                    }

                gsi.append({
                    'name': index['IndexName'],
                    'keys': gsi_keys,
                    'projection_type': index['Projection']['ProjectionType'],
                    'non_key_attributes': index['Projection'].get('NonKeyAttributes', [])
                })

        lsi = []
        if 'LocalSecondaryIndexes' in table_info:
            for index in table_info['LocalSecondaryIndexes']:
                lsi_keys = {}
                for key in index['KeySchema']:
                    key_type = 'partition_key' if key['KeyType'] == 'HASH' else 'sort_key'
                    lsi_keys[key_type] = {
                        'name': key['AttributeName'],
                        'type': next((attr['AttributeType'] for attr in table_info['AttributeDefinitions'] 
                                     if attr['AttributeName'] == key['AttributeName']), None)
                    }

                lsi.append({
                    'name': index['IndexName'],
                    'keys': lsi_keys,
                    'projection_type': index['Projection']['ProjectionType'],
                    'non_key_attributes': index['Projection'].get('NonKeyAttributes', [])
                })

        # Prepare table schema result
        schema_info = {
            'table_name': table_info['TableName'],
            'key_schema': key_schema,
            'global_secondary_indexes': gsi,
            'local_secondary_indexes': lsi,
            'billing_mode': table_info.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED'),
            'creation_time': table_info.get('CreationDateTime', ''),
            'item_count': table_info.get('ItemCount', 0),
            'size_bytes': table_info.get('TableSizeBytes', 0)
        }

        # Infer non-key attribute schema by sampling items (optional)
        if sample_items:
            schema_info['attribute_schema'] = infer_attribute_schema(table_name)

        return schema_info

    except Exception as e:
        print(f"Error getting DynamoDB schema: {str(e)}")
        raise


@tool
def dynamo_table_filter(table_name, filters=None, sort_by=None, limit=5):
    """
    Flexible filter for DynamoDB table records.

    Args:
        table_name (str): DynamoDB table name
        filters (list/dict): Filter conditions - either:
            - dict with fields: 'field', 'condition', 'value'
            - list of multiple filter dicts (combined with AND logic)
        sort_by (dict): Optional sorting info with 'field' and 'direction' ('asc'/'desc')
        limit (int): Maximum number of records to return

    Filter condition options:
        'eq' - equals
        'ne' - not equals
        'gt' - greater than
        'lt' - less than
        'ge' - greater than or equal
        'le' - less than or equal
        'contains' - string contains or list contains
        'begins_with' - string starts with
        'exists' - field exists
        'not_exists' - field does not exist
        'in' - value in list
        'between' - value in range [min, max]

    Example usage:
        # Find diabetic patients
        diabetic_patients = flexible_patient_filter('patient_info',
            {'field': 'medicalSummary.diagnoses', 'condition': 'contains', 'value': 'diabetes'})

        # Find female patients over 65 with heart conditions
        elderly_heart_patients = flexible_patient_filter('patient_info', [
            {'field': 'demographics.gender', 'condition': 'eq', 'value': 'Female'},
            {'field': 'demographics.age', 'condition': 'gt', 'value': 65},
            {'field': 'medicalSummary.diagnoses', 'condition': 'contains', 'value': 'heart'}
        ])
    """
    region = 'us-east-1'

    def matches_all_filters(patient, filters):
        """Check if a patient matches all the specified filters"""
        if isinstance(filters, str):
            filters = json.loads(filters)
        if isinstance(filters, dict):
            filters = [filters]
        for filter_item in filters:
            if not matches_filter(patient, filter_item):
                return False
        return True

    def matches_filter(patient, filter_item):
        """Check if a patient matches a single filter"""
        if isinstance(filter_item, str):
            filter_item = json.loads(filter_item)

        field = filter_item.get('field', '')
        condition = filter_item.get('condition', 'eq')
        value = filter_item.get('value')
        case_sensitive = filter_item.get('case_sensitive', False)
        #print('completed\n\n')
        # Get the actual value from the patient data
        actual = get_value_at_path(patient, field)

        # Handle existence checks
        if condition == 'exists':
            return actual is not None
        if condition == 'not_exists':
            return actual is None

        # If the field doesn't exist but we're checking other conditions, it's a non-match
        if actual is None:
            return False

        # Convert Decimal to float for easier comparison (DynamoDB returns Decimal)
        if isinstance(actual, Decimal):
            actual = float(actual)
        if isinstance(value, Decimal):
            value = float(value)

        # Case insensitivity for strings
        if isinstance(actual, str) and isinstance(value, str) and not case_sensitive:
            actual = actual.lower()
            value = value.lower()

        # Handle list contained values (for diagnoses, medications, etc.)
        if isinstance(actual, list) and condition == 'contains':
            if isinstance(value, str) and not case_sensitive:
                return any(value in str(item).lower() for item in actual)
            return any(value in str(item) for item in actual)

        # Normal comparison operations
        if condition == 'eq':
            return actual == value
        elif condition == 'ne':
            return actual != value
        elif condition == 'gt':
            return actual > value
        elif condition == 'lt':
            return actual < value
        elif condition == 'ge':
            return actual >= value
        elif condition == 'le':
            return actual <= value
        elif condition == 'contains':
            if isinstance(actual, str):
                return value in actual
            return False
        elif condition == 'begins_with':
            if isinstance(actual, str):
                return actual.startswith(value)
            return False
        elif condition == 'in':
            return actual in value if isinstance(value, list) else False
        elif condition == 'between':
            return value[0] <= actual <= value[1] if isinstance(value, list) and len(value) >= 2 else False

        # Unknown condition
        return False

    def get_value_at_path(data, path):
        """Get a value from a nested dictionary using dot notation path"""
        if not path:
            return None

        # Handle JSON path notation (e.g., "demographics.age")
        parts = path.split('.')
        current = copy.deepcopy(data)  # Avoid modifying the original data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    # Initialize DynamoDB connection
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    # Retrieve all patient records
    all_patients = []
    last_evaluated_key = None

    # Get all records with pagination
    while True:
        scan_kwargs = {}
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

        response = table.scan(**scan_kwargs)
        all_patients.extend(response.get('Items', []))

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    # If no filters, return all patients (potentially sorted and limited)
    if not filters:
        result = all_patients
    else:
        # Normalize filters to a list format
        if isinstance(filters, dict):
            filters = [filters]

        # Apply filters
        try:
            result = [patient for patient in all_patients if matches_all_filters(patient, filters)]
        except Exception as e:
            print(e)
            raise e

    # Apply sorting if requested
    if sort_by and 'field' in sort_by:
        field = sort_by['field']
        reverse = sort_by.get('direction', 'asc').lower() == 'desc'

        # Sort based on the specified field
        result.sort(
            key=lambda x: get_value_at_path(x, field) or "", 
            reverse=reverse
        )

    # Apply limit if specified
    if limit and isinstance(limit, int) and limit > 0:
        result = result[:limit]

    return result

