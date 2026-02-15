"""Unit tests for escalation handler Lambda function."""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from lambda_functions.escalation.handler import (
    lambda_handler,
    create_escalation_ticket,
    store_escalation_dual_storage,
)


class TestEscalationHandler:
    """Test escalation handler Lambda function."""

    @patch('lambda_functions.escalation.handler.ESCALATION_SNS_TOPIC', 'arn:aws:sns:eu-west-1:123456789012:escalations')
    @patch('lambda_functions.escalation.handler.dual_storage')
    @patch('lambda_functions.escalation.handler.dynamodb')
    @patch('lambda_functions.escalation.handler.sns_client')
    @patch('lambda_functions.escalation.handler.s3_client')
    def test_lambda_handler_success(
        self, mock_s3, mock_sns, mock_dynamodb, mock_dual_storage
    ):
        """Test successful escalation creation."""
        # Arrange
        event = {
            'brands_rejected': [123, 456],
            'iteration': 10,
            'workflow_config': {'max_iterations': 10},
            'reason': 'Maximum iteration limit (10) exceeded'
        }
        
        # Mock S3 response for brand details
        mock_s3.get_object.return_value = {
            'Body': MagicMock(
                read=lambda: json.dumps({
                    'brandname': 'Test Brand',
                    'sector': 'Food & Beverage',
                    'metadata': {
                        'confidence_score': 0.65,
                        'generation_metadata': {
                            'issues_identified': ['low_confidence']
                        }
                    }
                }).encode('utf-8')
            )
        }
        
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock dual storage
        mock_dual_storage.write_escalation.return_value = {
            's3_key': 'escalations/brand_123_ESC-123.json',
            'escalation_id': 'ESC-123',
            'status': 'success'
        }
        
        # Mock SNS
        mock_sns.publish.return_value = {'MessageId': 'msg-123'}
        
        # Act
        result = lambda_handler(event, None)
        
        # Assert
        assert result['statusCode'] == 200
        assert result['status'] == 'success'
        assert result['escalation_ticket'] is not None
        assert result['notification_sent'] is True
        
        # Verify dual storage was called for each brand
        assert mock_dual_storage.write_escalation.call_count == 2

    @patch('lambda_functions.escalation.handler.dual_storage')
    @patch('lambda_functions.escalation.handler.dynamodb')
    @patch('lambda_functions.escalation.handler.sns_client')
    @patch('lambda_functions.escalation.handler.s3_client')
    def test_lambda_handler_no_brands(
        self, mock_s3, mock_sns, mock_dynamodb, mock_dual_storage
    ):
        """Test handler with no brands to escalate."""
        # Arrange
        event = {
            'brands_rejected': [],
            'iteration': 10,
            'workflow_config': {},
            'reason': 'Test'
        }
        
        # Act
        result = lambda_handler(event, None)
        
        # Assert
        assert result['statusCode'] == 200
        assert result['status'] == 'no_brands_to_escalate'
        assert result['escalation_ticket'] is None
        assert result['notification_sent'] is False
        
        # Verify dual storage was not called
        mock_dual_storage.write_escalation.assert_not_called()

    def test_create_escalation_ticket(self):
        """Test escalation ticket creation."""
        # Arrange
        brands_rejected = [123, 456]
        iteration = 10
        reason = 'Maximum iteration limit exceeded'
        
        with patch('lambda_functions.escalation.handler.get_brand_details') as mock_get_details:
            mock_get_details.side_effect = [
                {
                    'brandid': 123,
                    'brandname': 'Brand A',
                    'sector': 'Food',
                    'confidence_score': 0.65,
                    'issues': ['low_confidence']
                },
                {
                    'brandid': 456,
                    'brandname': 'Brand B',
                    'sector': 'Retail',
                    'confidence_score': 0.70,
                    'issues': []
                }
            ]
            
            # Act
            ticket = create_escalation_ticket(brands_rejected, iteration, reason)
            
            # Assert
            assert ticket['ticket_id'].startswith('ESC-')
            assert ticket['status'] == 'open'
            assert ticket['priority'] == 'high'
            assert ticket['reason'] == reason
            assert ticket['iteration'] == iteration
            assert ticket['brands_count'] == 2
            assert len(ticket['brands']) == 2
            assert ticket['brands'][0]['brandid'] == 123
            assert ticket['brands'][1]['brandid'] == 456

    @patch('lambda_functions.escalation.handler.dual_storage')
    def test_store_escalation_dual_storage_success(self, mock_dual_storage):
        """Test storing escalation via dual storage."""
        # Arrange
        ticket = {
            'ticket_id': 'ESC-20240101120000',
            'created_at': '2024-01-01T12:00:00Z',
            'status': 'open',
            'reason': 'Maximum iteration limit exceeded',
            'iteration': 10,
            'environment': 'dev',
            'brands': [
                {
                    'brandid': 123,
                    'brandname': 'Test Brand',
                    'sector': 'Food',
                    'confidence_score': 0.65,
                    'issues': ['low_confidence']
                }
            ]
        }
        
        mock_dual_storage.write_escalation.return_value = {
            's3_key': 'escalations/brand_123_ESC-20240101120000-123.json',
            'escalation_id': 'ESC-20240101120000-123',
            'status': 'success'
        }
        
        # Act
        store_escalation_dual_storage(ticket)
        
        # Assert
        mock_dual_storage.write_escalation.assert_called_once()
        call_args = mock_dual_storage.write_escalation.call_args[0][0]
        
        assert call_args['escalation_id'] == 'ESC-20240101120000-123'
        assert call_args['brandid'] == 123
        assert call_args['brandname'] == 'Test Brand'
        assert call_args['reason'] == 'Maximum iteration limit exceeded'
        assert call_args['confidence_score'] == 0.65
        assert call_args['escalated_at'] == '2024-01-01T12:00:00Z'
        assert call_args['status'] == 'open'
        assert call_args['iteration'] == 10
        assert call_args['environment'] == 'dev'

    @patch('lambda_functions.escalation.handler.dual_storage')
    def test_store_escalation_dual_storage_failure_does_not_crash(self, mock_dual_storage):
        """Test that dual storage failure doesn't crash the escalation process."""
        # Arrange
        ticket = {
            'ticket_id': 'ESC-20240101120000',
            'created_at': '2024-01-01T12:00:00Z',
            'status': 'open',
            'reason': 'Test',
            'iteration': 10,
            'environment': 'dev',
            'brands': [
                {
                    'brandid': 123,
                    'brandname': 'Test Brand',
                    'sector': 'Food',
                    'confidence_score': 0.65,
                    'issues': []
                }
            ]
        }
        
        # Mock dual storage to raise an exception
        mock_dual_storage.write_escalation.side_effect = Exception('S3 error')
        
        # Act - should not raise exception
        store_escalation_dual_storage(ticket)
        
        # Assert - function should complete without raising
        mock_dual_storage.write_escalation.assert_called_once()

    @patch('lambda_functions.escalation.handler.dual_storage')
    def test_store_escalation_dual_storage_multiple_brands(self, mock_dual_storage):
        """Test storing escalation for multiple brands."""
        # Arrange
        ticket = {
            'ticket_id': 'ESC-20240101120000',
            'created_at': '2024-01-01T12:00:00Z',
            'status': 'open',
            'reason': 'Maximum iteration limit exceeded',
            'iteration': 10,
            'environment': 'dev',
            'brands': [
                {
                    'brandid': 123,
                    'brandname': 'Brand A',
                    'sector': 'Food',
                    'confidence_score': 0.65,
                    'issues': []
                },
                {
                    'brandid': 456,
                    'brandname': 'Brand B',
                    'sector': 'Retail',
                    'confidence_score': 0.70,
                    'issues': []
                }
            ]
        }
        
        mock_dual_storage.write_escalation.return_value = {
            's3_key': 'escalations/brand_123_ESC-123.json',
            'escalation_id': 'ESC-123',
            'status': 'success'
        }
        
        # Act
        store_escalation_dual_storage(ticket)
        
        # Assert - should be called once for each brand
        assert mock_dual_storage.write_escalation.call_count == 2
        
        # Verify first call
        first_call_args = mock_dual_storage.write_escalation.call_args_list[0][0][0]
        assert first_call_args['brandid'] == 123
        assert first_call_args['brandname'] == 'Brand A'
        
        # Verify second call
        second_call_args = mock_dual_storage.write_escalation.call_args_list[1][0][0]
        assert second_call_args['brandid'] == 456
        assert second_call_args['brandname'] == 'Brand B'
