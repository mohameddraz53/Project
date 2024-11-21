import boto3
import time
import datetime 
import os
# Access AWS credentials from environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_default_region = os.getenv('AWS_DEFAULT_REGION')



# Initialize a session using your default profile
session = boto3.Session()
ec2_client = session.client('ec2')


# Function to retrieve VPC IDs based on CIDR block
def get_vpc_id(cidr_block):
    vpcs = ec2_client.describe_vpcs()['Vpcs']
    for vpc in vpcs:
        if vpc['CidrBlock'] == cidr_block:
            return vpc['VpcId']
    return None


# Define CIDR blocks for Lab and Shared VPCs
lab_vpc_cidr = '10.0.0.0/16'
shared_vpc_cidr = '10.0.5.0/16'


# Retrieve VPC IDs
lab_vpc_id = get_vpc_id(lab_vpc_cidr)
shared_vpc_id = get_vpc_id(shared_vpc_cidr)


# Print VPC IDs
print(f"Lab VPC ID: {lab_vpc_id}")
print(f"Shared VPC ID: {shared_vpc_id}")



# Check if VPC IDs were found
if not lab_vpc_id or not shared_vpc_id:
    print("Lab VPC or Shared VPC not found. Please check the CIDR blocks.")
else:
    
  
  
    # Create VPC peering connection
    peering_connection = ec2_client.create_vpc_peering_connection(
        VpcId=lab_vpc_id,
        PeerVpcId=shared_vpc_id
    )
    print(f"VPC Peering Connection ID: {peering_connection['VpcPeeringConnection']['VpcPeeringConnectionId']}")
 
 
 
    # List all VPCs for debugging purposes
print("Listing all VPCs:")
vpcs = ec2_client.describe_vpcs()['Vpcs']
for vpc in vpcs:
    print(f"VPC ID: {vpc['VpcId']}, CIDR Block: {vpc['CidrBlock']}")
    # Assuming route tables need to be configured here...
    # Add your code for route table updates and flow logs here.




# Initialize the Boto3 client for EC2 and STS
ec2_client = boto3.client('ec2')
sts_client = boto3.client('sts')



# Step 1: Retrieve the AWS Account ID
account_id = sts_client.get_caller_identity()['Account']
print(f"AWS Account ID: {account_id}")



# Step 2: Retrieve all VPCs in the account
vpcs = ec2_client.describe_vpcs()['Vpcs']
vpc_ids = [vpc['VpcId'] for vpc in vpcs]
print("VPC IDs:")
for vpc_id in vpc_ids:
    print(f" - {vpc_id}")
    print()




# Step 3: Retrieve all route tables in the account
route_tables = ec2_client.describe_route_tables()['RouteTables']
print("Route Tables:")
for rt in route_tables:
    print(f" - Route Table ID: {rt['RouteTableId']}, VPC ID: {rt['VpcId']}")



# Step 4: Retrieve all VPC peering connections in the account
peering_connections = ec2_client.describe_vpc_peering_connections()['VpcPeeringConnections']
print("VPC Peering Connections:")
for pc in peering_connections:
    print(f" - Peering Connection ID: {pc['VpcPeeringConnectionId']}, Status: {pc['Status']['Code']}, VPCs: {pc['AccepterVpcInfo']['VpcId']} <-> {pc['RequesterVpcInfo']['VpcId']}")


# Initialize the Boto3 client for EC2
ec2_client = boto3.client('ec2')
logs_client = boto3.client('logs')


# Assign Lab VPC based on its CIDR block
lab_vpc = next((vpc for vpc in vpcs if vpc['CidrBlock'] == '10.0.0.0/16'), None)
if lab_vpc:
    lab_vpc_id = lab_vpc['VpcId']
    print(f"Lab VPC ID: {lab_vpc_id}")
else:
    lab_vpc_id = None
    print("Lab VPC not found.")
    
    
# Define VPC IDs (replace these with your actual VPC IDs)
lab_vpc_id = lab_vpc_id # Replace with your lab VPC ID



# Assign Shared VPC based on its CIDR block
shared_vpc = next((vpc for vpc in vpcs if vpc['CidrBlock'] == '10.0.5.0/16'), None)
if shared_vpc:
    shared_vpc_id = shared_vpc['VpcId']
    print(f"Shared VPC ID: {shared_vpc_id}")
else:
    shared_vpc_id = None
    print("Shared VPC not found.")
shared_vpc_id = shared_vpc_id  # Replace with your shared VPC ID



# Step 1: Create VPC Peering Connection
peering_connection = ec2_client.create_vpc_peering_connection(
    VpcId=lab_vpc_id,
    PeerVpcId=shared_vpc_id
)



# Step 2: Accept the VPC Peering Connection
peering_connection_id = peering_connection['VpcPeeringConnection']['VpcPeeringConnectionId']
ec2_client.accept_vpc_peering_connection(VpcPeeringConnectionId=peering_connection_id)

print(f'Created and accepted VPC peering connection: {peering_connection_id}')



# Step 3: Retrieve Route Tables for both VPCs
route_tables_lab = ec2_client.describe_route_tables(
    Filters=[{'Name': 'vpc-id', 'Values': [lab_vpc_id]}]
)['RouteTables']

route_tables_shared = ec2_client.describe_route_tables(
    Filters=[{'Name': 'vpc-id', 'Values': [shared_vpc_id]}]
)['RouteTables']



# Step 4: Add routes to the route tables
for rt in route_tables_lab:
    ec2_client.create_route(
        RouteTableId='${route_tables_lab}',
        DestinationCidrBlock='10.0.5.0/16',  # Shared VPC CIDR
        VpcPeeringConnectionId=peering_connection_id
    )
    print(f'Added route to {rt["RouteTableId"]} for shared VPC.')

for rt in route_tables_shared:
    ec2_client.create_route(
        RouteTableId='${route_tables_shared}',
        DestinationCidrBlock='10.0.0.0/16',  # Lab VPC CIDR
        VpcPeeringConnectionId=peering_connection_id
    )
    print(f'Added route to {rt["RouteTableId"]} for lab VPC.')



# Step 5: Create CloudWatch Log Group for Flow Logs
log_group_name = 'ShareVPCFlowLogs'
logs_client.create_log_group(LogGroupName=log_group_name)
print(f'Created CloudWatch Log Group: {log_group_name}')




# Step 6: Create Flow Logs
flow_logs_role = 'vpc-flow-logs-Role'  # Replace with your IAM role for VPC Flow Logs
flow_log_response = ec2_client.create_flow_logs(
    ResourceIds=[lab_vpc_id, shared_vpc_id],
    ResourceType='VPC',
    TrafficType='ALL',
    LogGroupName=log_group_name,
    DeliverLogsPermissionArn=f'arn:aws:iam::{boto3.client("sts").get_caller_identity()["Account"]}:role/{flow_logs_role}'
)
print('Flow logs created:', flow_log_response['FlowLogIds'])



# Function to retrieve flow logs from the specified log group
def get_flow_logs(log_group_name, start_time, end_time):
    query = f"""
    fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
    | sort @timestamp desc
    | limit 100
    """
    
    # Start query
    start_query_response = logs_client.start_query(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        queryString=query
    )
    
    query_id = start_query_response['queryId']
    
    # Wait for query to complete
    response = None
    while response == None or response['status'] == 'Running':
        print("Waiting for query to complete...")
        time.sleep(1)
        response = logs_client.get_query_results(
            queryId=query_id
        )
    
    return response['results']



# Set time range for the query
end_time = int(datetime.datetime.now().timestamp()) * 1000  # Current time in milliseconds
start_time = end_time - (60 * 60 * 1000)  # Last hour



# Fetch flow logs
flow_logs = get_flow_logs(log_group_name, start_time, end_time)



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

# Function to retrieve CloudWatch log streams
def get_log_streams(log_group_name):
    try:
        response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5  # Limit the number of log streams to retrieve
        )
        log_streams = response['logStreams']
        if log_streams:
            print(f"Log streams in log group {log_group_name}:")
            for stream in log_streams:
                print(f"Log Stream: {stream['logStreamName']}, Last Event: {stream['lastIngestionTime']}")
        else:
            print("No log streams found.")
    except Exception as e:
        print(f"Error retrieving log streams: {e}")

# Function to get log events from a specific log stream
def get_log_events(log_group_name, log_stream_name):
    try:
        response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            startFromHead=True
        )
        events = response['events']
        print(f"Log events from {log_stream_name}:")
        for event in events:
            print(f"Timestamp: {event['timestamp']}, Message: {event['message']}")
    except Exception as e:
        print(f"Error retrieving log events: {e}")
        
# Get Log Streams from the specified log group
log_streams = get_log_streams(log_group_name) 
log_stream_name = log_streams  # You can get the name from the log streams list
get_log_events(log_group_name, log_stream_name)