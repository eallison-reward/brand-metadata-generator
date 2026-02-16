#!/usr/bin/env python3
"""Check CloudWatch logs for Lambda functions."""

import argparse
import boto3
import sys
from datetime import datetime, timedelta


def get_recent_logs(function_name: str, region: str = "eu-west-1", minutes: int = 10):
    """Get recent logs for a Lambda function.
    
    Args:
        function_name: Lambda function name
        region: AWS region
        minutes: How many minutes back to look
    """
    logs_client = boto3.client('logs', region_name=region)
    
    log_group_name = f"/aws/lambda/{function_name}"
    
    try:
        print(f"\n{'='*70}")
        print(f"CloudWatch Logs for {function_name}")
        print(f"{'='*70}")
        print(f"Log Group: {log_group_name}")
        print(f"Time Range: Last {minutes} minutes")
        print(f"{'='*70}\n")
        
        # Get log streams (most recent first)
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not streams_response.get('logStreams'):
            print("No log streams found")
            return True
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        # Get log events from recent streams
        all_events = []
        for stream in streams_response['logStreams'][:3]:  # Check last 3 streams
            stream_name = stream['logStreamName']
            
            try:
                events_response = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream_name,
                    startTime=start_ms,
                    endTime=end_ms,
                    startFromHead=True
                )
                
                events = events_response.get('events', [])
                if events:
                    all_events.extend(events)
            except Exception as e:
                print(f"Could not read stream {stream_name}: {str(e)}")
        
        if not all_events:
            print("No log events found in the specified time range")
            return True
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x['timestamp'])
        
        # Print events
        for event in all_events:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].rstrip()
            print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
        
        print(f"\n{'='*70}")
        print(f"Total events: {len(all_events)}")
        print(f"{'='*70}\n")
        
        return True
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"❌ Log group not found: {log_group_name}")
        print("   The Lambda function may not have been invoked yet.")
        return False
    except Exception as e:
        print(f"❌ Error fetching logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Check CloudWatch logs for Lambda functions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check router Lambda logs
  python check_lambda_logs.py --function brand_metagen_conversational_router_dev
  
  # Check start_workflow Lambda logs
  python check_lambda_logs.py --function brand_metagen_start_workflow_dev
  
  # Check logs from last 30 minutes
  python check_lambda_logs.py --function brand_metagen_conversational_router_dev --minutes 30
        """
    )
    parser.add_argument(
        "--function",
        required=True,
        help="Lambda function name"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region (default: eu-west-1)"
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=10,
        help="How many minutes back to look (default: 10)"
    )
    
    args = parser.parse_args()
    
    success = get_recent_logs(args.function, args.region, args.minutes)
    
    if success:
        sys.exit(0)
    else:
        print("\n❌ Failed to fetch logs")
        sys.exit(1)


if __name__ == "__main__":
    main()
