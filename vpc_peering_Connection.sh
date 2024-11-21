#!/bin/bash
                  ###----------------------------------------VPC_Peering_Connection_Project------------------------------------###
                  
# Check if AWS credentials file exists
credentials_file="$HOME/.aws/credentials"

if [ -f "$credentials_file" ]; then
    echo "Retrieving AWS credentials from $credentials_file..."
    # Parse and display the credentials from the file
    while read -r line; do
        # Exclude empty lines and comments
        if [[ ! -z "$line" && "$line" != \[*\] ]]; then
            echo "$line"
        fi
    done < "$credentials_file"
else
    echo "AWS credentials file not found. Checking environment variables..."
    # Retrieve environment variable credentials
    if [[ -n "$AWS_ACCESS_KEY_ID" && -n "$AWS_SECRET_ACCESS_KEY" ]]; then
        echo "AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID"
        echo "AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY"
        [[ -n "$AWS_SESSION_TOKEN" ]] && echo "AWS_SESSION_TOKEN: $AWS_SESSION_TOKEN"
    else
        echo "No AWS credentials found in environment variables or credentials file."
    fi
fi

# Describe VPCs
echo "Describing VPCs..."
vpcs=$(aws ec2 describe-vpcs --query "Vpcs[*].{ID:VpcId,Name:Tags[?Key=='Name']|[0].Value}" --output json)

# Extract IDs into variables
lab_vpc_id=$(echo "$vpcs" | jq -r '.[] | select(.Name=="Lab VPC") | .ID')
shared_vpc_id=$(echo "$vpcs" | jq -r '.[] | select(.Name=="Shared VPC") | .ID')

echo "Lab VPC ID: $lab_vpc_id"
echo "Shared VPC ID: $shared_vpc_id"

# Describe Route Tables
echo "Describing Route Tables..."
route_tables=$(aws ec2 describe-route-tables --query "RouteTables[*].{ID:RouteTableId,VPC:VpcId,Name:Tags[?Key=='Name']|[0].Value}" --output json)

# Extract Route Table IDs into variables
lab_route_table_id=$(echo "$route_tables" | jq -r '.[] | select(.Name=="Lab Private Route Table") | .ID')
shared_route_table_id=$(echo "$route_tables" | jq -r '.[] | select(.Name=="Shared-VPC Route Table") | .ID')

echo "Lab Route Table ID: $lab_route_table_id"
echo "Shared Route Table ID: $shared_route_table_id"

# Create VPC Peering Connection
echo "Creating VPC Peering Connection..."
peering_response=$(aws ec2 create-vpc-peering-connection \
  --vpc-id "$lab_vpc_id" \
  --peer-vpc-id "$shared_vpc_id" \
  --tag-specifications 'ResourceType=vpc-peering-connection,Tags=[{Key=Name,Value=Lab-Peer}]')
echo "$peering_response"

# Accept VPC Peering Connection
peering_id=$(echo "$peering_response" | jq -r '.VpcPeeringConnection.VpcPeeringConnectionId')
echo "Accepting VPC Peering Connection..."
accept_response=$(aws ec2 accept-vpc-peering-connection --vpc-peering-connection-id "$peering_id")
echo "$accept_response"

# Create Routes
echo "Creating routes in route tables..."
aws ec2 create-route \
  --route-table-id "$lab_route_table_id" \
  --destination-cidr-block 10.5.0.0/16 \
  --vpc-peering-connection-id "$peering_id"

aws ec2 create-route \
  --route-table-id "$shared_route_table_id" \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id "$peering_id"

# Create CloudWatch Log Group
echo "Creating CloudWatch Log Group..."
aws logs create-log-group --log-group-name ShareVPCFlowLogs

# Create Flow Logs
echo "Creating Flow Logs..."
aws ec2 create-flow-logs \
  --resource-ids "$shared_vpc_id" \
  --resource-type VPC \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name ShareVPCFlowLogs \
  --deliver-logs-permission-arn arn:aws:iam::146904539270:role/vpc-flow-logs-Role \
  --max-aggregation-interval 60
# Function to retrieve flow logs from the specified log group
get_flow_logs() {
    log_group_name=$1
    start_time=$2
    end_time=$3

    query="fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action | sort @timestamp desc | limit 100"
    
    # Start query
    query_id=$(aws logs start-query --log-group-name "$log_group_name" --start-time "$start_time" --end-time "$end_time" --query-string "$query" --query 'queryId' --output text)
    
    # Wait for query to complete
    while true; do
        status=$(aws logs get-query-results --query-id "$query_id" --query 'status' --output text)
        if [ "$status" == "Complete" ]; then
            break
        fi
        echo "Waiting for query to complete..."
        sleep 1
    done

    # Fetch and return results
    aws logs get-query-results --query-id "$query_id" --output json
}

# Function to retrieve CloudWatch log streams
get_log_streams() {
    log_group_name=$1

    # Fetch the latest 5 log streams
    aws logs describe-log-streams --log-group-name "$log_group_name" --order-by LastEventTime --descending --limit 5 --output json
}

# Function to get log events from a specific log stream
get_log_events() {
    log_group_name=$1
    log_stream_name=$2

    # Fetch log events from the specified log stream
    aws logs get-log-events --log-group-name "$log_group_name" --log-stream-name "$log_stream_name" --start-from-head --output json
}

# Set time range for the flow log query
end_time=$(($(date +%s) * 1000)) # Current time in milliseconds
start_time=$(("$end_time" - 3600000)) # Last hour in milliseconds

# Specify the log group name
log_group_name="ShareVPCFlowLogs"

# Fetch flow logs
echo "Fetching flow logs from $log_group_name..."
flow_logs=$(get_flow_logs $log_group_name $start_time $end_time)

# Print flow log analysis
echo "VPC Flow Logs Analysis:"
echo "$flow_logs" | jq -r '.results[] | "Timestamp: \(.[] | select(.field == \"@timestamp\").value), Source IP: \(.[] | select(.field == \"srcAddr\").value), Destination IP: \(.[] | select(.field == \"dstAddr\").value), Source Port: \(.[] | select(.field == \"srcPort\").value), Destination Port: \(.[] | select(.field == \"dstPort\").value), Protocol: \(.[] | select(.field == \"protocol\").value), Action: \(.[] | select(.field == \"action\").value)"'

# Retrieve and print log streams
echo "Fetching log streams from $log_group_name..."
log_streams=$(get_log_streams $log_group_name)
echo "$log_streams" | jq -r '.logStreams[] | "Log Stream: \(.logStreamName), Last Event: \(.lastIngestionTime)"'

# Retrieve events from a specific log stream (you can replace the log stream name as needed)
log_stream_name=$(echo "$log_streams" | jq -r '.logStreams[0].logStreamName') # Get the first log stream name
echo "Fetching log events from log stream: $log_stream_name..."
log_events=$(get_log_events $log_group_name "$log_stream_name")

# Print log events
echo "Log events from $log_stream_name:"
echo "$log_events" | jq -r '.events[] | "Timestamp: \(.timestamp), Message: \(.message)"'
