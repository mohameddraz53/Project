
                      ##-------------------------------------VPC_Peering_Connection_Creation_Project------------------------------------------##
import boto3
import time
import json
import datetime 
import os
# Access AWS credentials from environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_default_region = os.getenv('AWS_DEFAULT_REGION')


# Initialize boto3 clients
ec2_client = boto3.client('ec2')
logs_client = boto3.client('logs')

# Describe VPCs
print("Describing VPCs...")
vpcs = ec2_client.describe_vpcs()
lab_vpc_id = next((vpc['VpcId'] for vpc in vpcs['Vpcs'] if 'Tags' in vpc and any(tag['Key'] == 'Name' and tag['Value'] == 'Lab VPC' for tag in vpc['Tags'])), None)
shared_vpc_id = next((vpc['VpcId'] for vpc in vpcs['Vpcs'] if 'Tags' in vpc and any(tag['Key'] == 'Name' and tag['Value'] == 'Shared VPC' for tag in vpc['Tags'])), None)

print(f"Lab VPC ID: {lab_vpc_id}")
print(f"Shared VPC ID: {shared_vpc_id}")

# Describe Route Tables
print("Describing Route Tables...")
route_tables = ec2_client.describe_route_tables()
lab_route_table_id = next((rt['RouteTableId'] for rt in route_tables['RouteTables'] if 'Tags' in rt and any(tag['Key'] == 'Name' and tag['Value'] == 'Lab Private Route Table' for tag in rt['Tags'])), None)
shared_route_table_id = next((rt['RouteTableId'] for rt in route_tables['RouteTables'] if 'Tags' in rt and any(tag['Key'] == 'Name' and tag['Value'] == 'Shared-VPC Route Table' for tag in rt['Tags'])), None)

print(f"Lab Route Table ID: {lab_route_table_id}")
print(f"Shared Route Table ID: {shared_route_table_id}")

# Create VPC Peering Connection
print("Creating VPC Peering Connection...")
peering_response = ec2_client.create_vpc_peering_connection(
    VpcId=lab_vpc_id,
    PeerVpcId=shared_vpc_id,
    TagSpecifications=[{'ResourceType': 'vpc-peering-connection', 'Tags': [{'Key': 'Name', 'Value': 'Lab-Peer'}]}]
)
peering_id = peering_response['VpcPeeringConnection']['VpcPeeringConnectionId']
print(f"Peering Connection ID: {peering_id}")

# Accept VPC Peering Connection
print("Accepting VPC Peering Connection...")
ec2_client.accept_vpc_peering_connection(VpcPeeringConnectionId=peering_id)

# Create Routes
print("Creating routes in route tables...")
ec2_client.create_route(RouteTableId=lab_route_table_id, DestinationCidrBlock='10.5.0.0/16', VpcPeeringConnectionId=peering_id)
ec2_client.create_route(RouteTableId=shared_route_table_id, DestinationCidrBlock='10.0.0.0/16', VpcPeeringConnectionId=peering_id)

# Create CloudWatch Log Group
log_group_name = 'ShareVPCFlowLogs'
print(f"Creating CloudWatch Log Group: {log_group_name}...")
logs_client.create_log_group(logGroupName=log_group_name)

# Create Flow Logs
print("Creating Flow Logs...")
ec2_client.create_flow_logs(
    ResourceIds=[shared_vpc_id],
    ResourceType='VPC',
    TrafficType='ALL',
    LogDestinationType='cloud-watch-logs',
    LogGroupName=log_group_name,
    DeliverLogsPermissionArn='arn:aws:iam::146904539270:role/vpc-flow-logs-Role',
    MaxAggregationInterval=60
)

# Fetch Flow Logs
def get_flow_logs(log_group_name, start_time, end_time):
    query = "fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action | sort @timestamp desc | limit 100"
    print("Starting flow log query...")
    query_id = logs_client.start_query(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        queryString=query
    )['queryId']

    print("Waiting for query results...")
    while True:
        result = logs_client.get_query_results(queryId=query_id)
        if result['status'] == 'Complete':
            return result['results']
        time.sleep(1)

# Get Log Streams
def get_log_streams(log_group_name):
    print("Fetching log streams...")
    return logs_client.describe_log_streams(
        logGroupName=log_group_name,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )['logStreams']

# Get Log Events
def get_log_events(log_group_name, log_stream_name):
    print(f"Fetching log events from {log_stream_name}...")
    return logs_client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        startFromHead=True
    )['events']

# Query Flow Logs
end_time = int(datetime.datetime.now().timestamp() * 1000)
start_time = end_time - 3600000  # Last hour in milliseconds

flow_logs = get_flow_logs(log_group_name, start_time, end_time)
print("VPC Flow Logs Analysis:")
for log in flow_logs:
    print(json.dumps(log, indent=4))

# Get and analyze log streams
log_streams = get_log_streams(log_group_name)
if not log_streams:
    print(f"No log streams found in {log_group_name}")
else:
    for stream in log_streams:
        log_stream_name = stream['logStreamName']
        log_events = get_log_events(log_group_name, log_stream_name)
        for event in log_events:
            print(f"Timestamp: {event['timestamp']}, Message: {event['message']}")

# Print retrieved flow logs
print("VPC Flow Logs Analysis:")
for log in flow_logs:
    timestamp = log[0]['value']
    src_addr = log[1]['value']
    dst_addr = log[2]['value']
    src_port = log[3]['value']
    dst_port = log[4]['value']
    protocol = log[5]['value']
    action = log[6]['value']
    
    print(f"Timestamp: {timestamp}, Source IP: {src_addr}, Destination IP: {dst_addr}, "
          f"Source Port: {src_port}, Destination Port: {dst_port}, Protocol: {protocol}, "
          f"Action: {action}")
