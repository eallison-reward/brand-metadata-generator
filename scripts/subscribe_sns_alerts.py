#!/usr/bin/env python3
"""
Subscribe email addresses to SNS topic for production alerts.

This script subscribes email addresses to the brand-metadata-generator-alarms-prod
SNS topic to receive CloudWatch alarm notifications.
"""

import boto3
import sys
from typing import List

# Configuration
SNS_TOPIC_ARN = "arn:aws:sns:eu-west-1:536824473420:brand-metadata-generator-alarms-prod"
AWS_REGION = "eu-west-1"


def subscribe_email(email: str, topic_arn: str, region: str) -> dict:
    """
    Subscribe an email address to an SNS topic.
    
    Args:
        email: Email address to subscribe
        topic_arn: ARN of the SNS topic
        region: AWS region
        
    Returns:
        Response from SNS subscribe API
    """
    sns_client = boto3.client('sns', region_name=region)
    
    try:
        response = sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email,
            ReturnSubscriptionArn=True
        )
        return response
    except Exception as e:
        print(f"Error subscribing {email}: {str(e)}")
        raise


def list_subscriptions(topic_arn: str, region: str) -> List[dict]:
    """
    List all subscriptions for an SNS topic.
    
    Args:
        topic_arn: ARN of the SNS topic
        region: AWS region
        
    Returns:
        List of subscription details
    """
    sns_client = boto3.client('sns', region_name=region)
    
    try:
        response = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
        return response.get('Subscriptions', [])
    except Exception as e:
        print(f"Error listing subscriptions: {str(e)}")
        raise


def main():
    """Main function to subscribe email addresses."""
    
    # Email addresses to subscribe
    emails = [
        "ed.allison@rewardinsight.com"
    ]
    
    print(f"Subscribing email addresses to SNS topic:")
    print(f"Topic ARN: {SNS_TOPIC_ARN}")
    print(f"Region: {AWS_REGION}")
    print()
    
    # Subscribe each email
    for email in emails:
        print(f"Subscribing: {email}")
        try:
            response = subscribe_email(email, SNS_TOPIC_ARN, AWS_REGION)
            subscription_arn = response.get('SubscriptionArn', 'pending confirmation')
            print(f"  ✓ Subscription created: {subscription_arn}")
            
            if subscription_arn == 'pending confirmation':
                print(f"  → Confirmation email sent to {email}")
                print(f"  → Please check inbox and click confirmation link")
            
        except Exception as e:
            print(f"  ✗ Failed to subscribe {email}")
            print(f"  Error: {str(e)}")
            continue
        
        print()
    
    # List all subscriptions
    print("\nCurrent subscriptions:")
    print("-" * 80)
    try:
        subscriptions = list_subscriptions(SNS_TOPIC_ARN, AWS_REGION)
        
        if not subscriptions:
            print("No subscriptions found")
        else:
            for sub in subscriptions:
                endpoint = sub.get('Endpoint', 'N/A')
                protocol = sub.get('Protocol', 'N/A')
                status = sub.get('SubscriptionArn', 'N/A')
                
                if status == 'PendingConfirmation':
                    status_display = "⏳ Pending Confirmation"
                else:
                    status_display = "✓ Confirmed"
                
                print(f"  {protocol}: {endpoint}")
                print(f"    Status: {status_display}")
                print()
                
    except Exception as e:
        print(f"Error listing subscriptions: {str(e)}")
    
    print("\nIMPORTANT:")
    print("- Each email address will receive a confirmation email from AWS")
    print("- Click the 'Confirm subscription' link in the email to activate")
    print("- Subscriptions remain in 'PendingConfirmation' until confirmed")
    print("- Unconfirmed subscriptions are automatically deleted after 3 days")


if __name__ == "__main__":
    main()
