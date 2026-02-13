"""CloudWatch Metrics Publisher

This module provides utilities for publishing custom metrics to CloudWatch
for monitoring brand metadata generation workflow progress.
"""

import boto3
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetricsPublisher:
    """Publishes custom metrics to CloudWatch."""
    
    def __init__(self, namespace: str = "BrandMetadataGenerator", region: str = "eu-west-1"):
        """
        Initialize metrics publisher.
        
        Args:
            namespace: CloudWatch namespace for metrics
            region: AWS region
        """
        self.namespace = namespace
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
    
    def publish_metric(self, metric_name: str, value: float, 
                      unit: str = "Count", dimensions: Optional[Dict[str, str]] = None) -> None:
        """
        Publish a single metric to CloudWatch.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Count, Seconds, etc.)
            dimensions: Optional dimensions for the metric
        """
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            logger.debug(f"Published metric: {metric_name}={value} {unit}")
        except Exception as e:
            logger.error(f"Failed to publish metric {metric_name}: {str(e)}")
    
    def publish_brand_processed(self, brandid: int, success: bool = True) -> None:
        """
        Publish metric when a brand is processed.
        
        Args:
            brandid: Brand identifier
            success: Whether processing succeeded
        """
        metric_name = "BrandsProcessed" if success else "BrandsFailed"
        self.publish_metric(metric_name, 1.0, dimensions={"BrandId": str(brandid)})
    
    def publish_brand_status(self, processed: int, in_progress: int, pending: int) -> None:
        """
        Publish brand processing status metrics.
        
        Args:
            processed: Number of brands processed
            in_progress: Number of brands in progress
            pending: Number of brands pending
        """
        self.publish_metric("BrandsProcessed", float(processed))
        self.publish_metric("BrandsInProgress", float(in_progress))
        self.publish_metric("BrandsPending", float(pending))
    
    def publish_combo_metrics(self, matched: int = 0, confirmed: int = 0, 
                             excluded: int = 0, flagged: int = 0) -> None:
        """
        Publish combo matching and confirmation metrics.
        
        Args:
            matched: Number of combos matched
            confirmed: Number of combos confirmed
            excluded: Number of combos excluded (false positives)
            flagged: Number of combos flagged for human review
        """
        if matched > 0:
            self.publish_metric("CombosMatched", float(matched))
        if confirmed > 0:
            self.publish_metric("CombosConfirmed", float(confirmed))
        if excluded > 0:
            self.publish_metric("CombosExcluded", float(excluded))
        if flagged > 0:
            self.publish_metric("CombosFlaggedForReview", float(flagged))
    
    def publish_tie_metrics(self, detected: int = 0, resolved: int = 0, 
                           flagged: int = 0) -> None:
        """
        Publish tie detection and resolution metrics.
        
        Args:
            detected: Number of ties detected
            resolved: Number of ties resolved
            flagged: Number of ties flagged for human review
        """
        if detected > 0:
            self.publish_metric("TiesDetected", float(detected))
        if resolved > 0:
            self.publish_metric("TiesResolved", float(resolved))
        if flagged > 0:
            self.publish_metric("TiesFlaggedForReview", float(flagged))
    
    def publish_agent_invocation(self, agent_name: str) -> None:
        """
        Publish metric when an agent is invoked.
        
        Args:
            agent_name: Name of the agent
        """
        metric_name = f"{agent_name.replace('-', '').replace('_', '').title()}Invocations"
        self.publish_metric(metric_name, 1.0, dimensions={"Agent": agent_name})
    
    def publish_agent_error(self, agent_name: str, error_type: str = "General") -> None:
        """
        Publish metric when an agent encounters an error.
        
        Args:
            agent_name: Name of the agent
            error_type: Type of error (General, Validation, etc.)
        """
        self.publish_metric("AgentErrors", 1.0, 
                          dimensions={"Agent": agent_name, "ErrorType": error_type})
    
    def publish_validation_error(self, error_type: str) -> None:
        """
        Publish metric for validation errors.
        
        Args:
            error_type: Type of validation error
        """
        self.publish_metric("ValidationErrors", 1.0, 
                          dimensions={"ErrorType": error_type})
    
    def publish_retry_attempt(self, agent_name: str, attempt: int) -> None:
        """
        Publish metric when a retry is attempted.
        
        Args:
            agent_name: Name of the agent
            attempt: Retry attempt number
        """
        self.publish_metric("RetryAttempts", 1.0, 
                          dimensions={"Agent": agent_name, "Attempt": str(attempt)})


# Global metrics publisher instance
_metrics_publisher: Optional[MetricsPublisher] = None


def get_metrics_publisher() -> MetricsPublisher:
    """
    Get or create the global metrics publisher instance.
    
    Returns:
        MetricsPublisher instance
    """
    global _metrics_publisher
    if _metrics_publisher is None:
        _metrics_publisher = MetricsPublisher()
    return _metrics_publisher
