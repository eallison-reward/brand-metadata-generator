# Implementation Plan: Brand Metadata Generator

## Overview

This implementation plan breaks down the brand-metadata-generator system into discrete coding tasks. The system is a multi-agent orchestration platform built on AWS Bedrock AgentCore using Python and the Strands API. The implementation follows a phased approach: infrastructure setup, agent development, workflow orchestration, and testing.

## Tasks

- [x] 1. Project Setup and Infrastructure Foundation
  - Create GitHub repository with proper structure
  - Set up Python virtual environment and dependencies
  - Configure Terraform for AWS infrastructure
  - Initialize project documentation
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_

- [x] 2. Terraform Infrastructure as Code
  - [x] 2.1 Create Terraform module structure
    - Create modules for agents, step_functions, storage, and monitoring
    - Set up environment-specific configurations (dev, staging, prod)
    - Define shared IAM roles and policies
    - _Requirements: 11.11, 11.12_
  
  - [x] 2.2 Implement S3 and Athena infrastructure
    - Create S3 bucket resource (brand-generator-rwrd-023-eu-west-1)
    - Configure Glue catalog database (brand_metadata_generator_db)
    - Define Glue tables for brand, brand_to_check, combo, and mcc
    - Set up Athena workgroup and query result location
    - _Requirements: 11.5, 11.6_
  
  - [x] 2.3 Implement IAM roles and policies
    - Create agent execution role with Bedrock permissions
    - Add Athena query permissions
    - Add S3 read/write permissions
    - Add DynamoDB permissions for agent memory
    - Add CloudWatch Logs permissions
    - _Requirements: 11.10_
  
  - [x] 2.4 Create DynamoDB tables for agent memory
    - Define memory tables with TTL configuration
    - Set up appropriate indexes
    - _Requirements: 11.1_

- [x] 3. Data Transformation Agent
  - [x] 3.1 Implement Athena query tools
    - Create query_athena tool for executing SQL queries
    - Implement connection to brand_metadata_generator_db
    - Add error handling and retry logic
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7_
  
  - [x] 3.2 Implement data validation tools
    - Create validate_foreign_keys tool
    - Create validate_regex tool for syntax checking
    - Create validate_mccids tool for existence checking
    - _Requirements: 1.6, 8.4, 8.5_
  
  - [x] 3.3 Implement S3 storage tools
    - Create write_to_s3 tool for metadata storage
    - Create read_from_s3 tool for retrieval
    - Implement proper error handling
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 3.4 Implement data preparation tools
    - Create prepare_brand_data tool to aggregate combo records
    - Create apply_metadata_to_combos tool for matching
    - _Requirements: 2.3, 2.4_
  
  - [x] 3.5 Write property test for data transformation agent
    - **Property 1: Foreign Key Referential Integrity**
    - **Validates: Requirements 1.6**
  
  - [x] 3.6 Write unit tests for data transformation agent
    - Test Athena query execution
    - Test validation functions
    - Test S3 read/write operations
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 8.4, 8.5_

- [x] 4. Evaluator Agent
  - [x] 4.1 Implement narrative analysis tools
    - Create analyze_narratives tool for pattern consistency
    - Calculate narrative variance metrics
    - _Requirements: 4.1, 4.3_
  
  - [x] 4.2 Implement payment wallet detection
    - Create detect_payment_wallets tool
    - Identify PAYPAL, PP, SQ, SQUARE indicators (case-insensitive)
    - Flag wallet-affected combo records
    - _Requirements: 3.1, 3.2_
  
  - [x] 4.3 Implement MCCID analysis tools
    - Create assess_mccid_consistency tool
    - Check MCCID alignment with brand sector
    - Identify wallet-specific MCCIDs
    - _Requirements: 4.2, 4.4, 3.4_
  
  - [x] 4.4 Implement confidence scoring
    - Create calculate_confidence_score tool
    - Incorporate data quality metrics
    - Return score between 0.0 and 1.0
    - _Requirements: 4.6_
  
  - [x] 4.5 Implement production prompt generation
    - Create generate_production_prompt tool
    - Describe identified issues for metadata production
    - Provide guidance on wallet handling
    - _Requirements: 4.5, 3.5_
  
  - [x] 4.6 Write property tests for evaluator agent
    - **Property 4: Wallet Detection and Flagging**
    - **Property 7: Consistency Assessment**
    - **Property 10: Confidence Score Calculation**
    - **Validates: Requirements 3.1, 3.2, 4.1, 4.2, 4.6**
  
  - [x] 4.7 Write unit tests for evaluator agent
    - Test narrative variance calculation
    - Test wallet detection with various indicators
    - Test confidence score edge cases
    - _Requirements: 3.1, 4.1, 4.6_

- [x] 5. Commercial Assessment Agent
  - [x] 5.1 Implement brand validation tools
    - Create verify_brand_exists tool
    - Create validate_sector tool
    - Create suggest_alternative_sectors tool
    - _Requirements: 5.3, 5.4_
  
  - [x] 5.2 Implement agent handler and integration
    - Set up Strands Agent with appropriate instructions
    - Register all tools
    - Implement handler function for AgentCore
    - _Requirements: 5.5_
  
  - [x] 5.3 Write unit tests for commercial assessment agent
    - Test brand existence validation
    - Test sector validation logic
    - Test alternative sector suggestions
    - _Requirements: 5.3, 5.4_

- [x] 6. Metadata Production Agent
  - [x] 6.1 Implement regex generation tool
    - Create generate_regex tool
    - Analyze narrative patterns
    - Handle wallet text exclusion
    - Generate regex with appropriate quantifiers and groups
    - _Requirements: 2.1, 3.3_
  
  - [x] 6.2 Implement MCCID list generation tool
    - Create generate_mccid_list tool
    - Filter wallet-specific MCCIDs
    - Return deduplicated list
    - _Requirements: 2.2_
  
  - [x] 6.3 Implement pattern validation tool
    - Create validate_pattern_coverage tool
    - Test regex against sample narratives
    - Calculate coverage and false positive rates
    - _Requirements: 2.5_
  
  - [x] 6.4 Implement iteration context management
    - Maintain context from previous iterations
    - Apply feedback for regeneration
    - Track iteration count
    - _Requirements: 10.4_
  
  - [x] 6.5 Write property tests for metadata production agent
    - **Property 2: Metadata Completeness**
    - **Property 5: Wallet Text Exclusion**
    - **Validates: Requirements 2.1, 2.2, 3.3**
  
  - [x] 6.6 Write unit tests for metadata production agent
    - Test regex generation with various narrative patterns
    - Test wallet text filtering
    - Test MCCID list generation
    - _Requirements: 2.1, 2.2, 3.3_

- [x] 7. Confirmation Agent
  - [x] 7.1 Implement combo review tools
    - Create review_matched_combos tool
    - Analyze combo-brand fit
    - Identify false positives (ambiguous brand names)
    - _Requirements: 6.5_
  
  - [x] 7.2 Implement confirmation decision tools
    - Create confirm_combo tool
    - Create exclude_combo tool
    - Create flag_for_human_review tool
    - _Requirements: 6.5_
  
  - [x] 7.3 Write property test for confirmation agent
    - **Property 12: Confirmation Decision Completeness**
    - **Validates: Requirements 6.5**
  
  - [x] 7.4 Write unit tests for confirmation agent
    - Test combo review logic
    - Test exclusion reasoning
    - Test human review flagging
    - _Requirements: 6.5_

- [x] 8. Tiebreaker Agent
  - [x] 8.1 Implement tie resolution tools
    - Create resolve_multi_match tool
    - Create analyze_narrative_similarity tool
    - Create compare_mccid_alignment tool
    - Create calculate_match_confidence tool
    - _Requirements: 7.3_
  
  - [x] 8.2 Implement resolution decision logic
    - Determine most likely brand based on analysis
    - Calculate confidence score
    - Flag low-confidence ties for human review
    - _Requirements: 7.4_
  
  - [x] 8.3 Write property tests for tiebreaker agent
    - **Property 13: Tie Detection and Resolution Workflow**
    - **Property 14: Low Confidence Tie Handling**
    - **Validates: Requirements 7.1, 7.2, 7.4, 7.5**
  
  - [x] 8.4 Write unit tests for tiebreaker agent
    - Test narrative similarity analysis
    - Test MCCID alignment comparison
    - Test confidence calculation
    - _Requirements: 7.3, 7.4_

- [x] 9. Orchestrator Agent
  - [x] 9.1 Implement workflow initialization
    - Create initialize_workflow tool
    - Load configuration (thresholds, max iterations, batch size)
    - Trigger data ingestion
    - _Requirements: 9.1_
  
  - [x] 9.2 Implement agent invocation tools
    - Create invoke_data_transformation tool
    - Create invoke_evaluator tool
    - Create invoke_metadata_production tool
    - Create invoke_confirmation tool
    - Create invoke_tiebreaker tool
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  
  - [x] 9.3 Implement error handling and retry logic
    - Add exponential backoff retry for agent failures
    - Log errors with context
    - Implement max retry limits
    - _Requirements: 9.9_
  
  - [x] 9.4 Implement workflow state management
    - Create update_workflow_state tool
    - Track brand processing status
    - Maintain iteration counters
    - _Requirements: 10.5_
  
  - [x] 9.5 Implement feedback routing
    - Route validation errors to metadata production
    - Route confirmation rejections with feedback
    - Route tie resolutions
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [x] 9.6 Write property tests for orchestrator agent
    - **Property 18: Conditional Routing**
    - **Property 19: Agent Failure Retry**
    - **Property 22: Iteration Limit**
    - **Validates: Requirements 9.5, 9.6, 9.9, 10.5**
  
  - [x] 9.7 Write unit tests for orchestrator agent
    - Test workflow initialization
    - Test agent invocation
    - Test retry logic with simulated failures
    - Test iteration limit enforcement
    - _Requirements: 9.1, 9.9, 10.5_

- [x] 10. Checkpoint - Ensure all agent tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Step Functions Workflow Definition
  - [x] 11.1 Create Step Functions state machine JSON
    - Define workflow states for each phase
    - Add error handling with retry and catch blocks
    - Configure timeouts and parallel execution where appropriate
    - _Requirements: 9.8_
  
  - [x] 11.2 Implement Lambda functions for Step Functions integration
    - Create Lambda to invoke Orchestrator Agent
    - Create Lambda for workflow initialization
    - Create Lambda for result aggregation
    - _Requirements: 11.3_
  
  - [x] 11.3 Add Step Functions to Terraform
    - Create step_functions module
    - Define state machine resource
    - Configure IAM role for Step Functions
    - _Requirements: 11.4_

- [x] 12. Agent Deployment
  - [x] 12.1 Create AgentCore deployment scripts
    - Write Python script to deploy each agent using agentcore CLI
    - Configure agent names, models, timeouts, memory
    - Set up agent memory with DynamoDB
    - _Requirements: 11.1_
  
  - [x] 12.2 Create agent instruction prompts
    - Write detailed instructions for each agent
    - Include tool usage guidelines
    - Define agent personalities and behaviors
    - _Requirements: 11.1_
  
  - [x] 12.3 Deploy agents to dev environment
    - Run deployment scripts for all 7 agents
    - Verify agent creation in AWS Bedrock
    - Test agent invocation
    - _Requirements: 11.1_

- [x] 13. Integration and End-to-End Testing
  - [x] 13.1 Write integration test for complete workflow
    - Set up test data in Athena
    - Invoke Step Functions workflow
    - Verify metadata generation
    - Verify combo matching and confirmation
    - Verify S3 storage of results
    - _Requirements: All_
  
  - [x] 13.2 Write integration test for tie resolution
    - Create tie scenario in test data
    - Verify Tiebreaker Agent invocation
    - Verify tie resolution and combo assignment
    - _Requirements: 7.1, 7.2, 7.3, 7.5_
  
  - [x] 13.3 Write integration test for confirmation workflow
    - Create ambiguous brand scenario
    - Verify Confirmation Agent invocation
    - Verify combo exclusion
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 14. Monitoring and Dashboard Setup
  - [x] 14.1 Configure CloudWatch Logs and Metrics
    - Set up log groups for each agent
    - Create custom metrics for workflow progress
    - Configure alarms for failures
    - _Requirements: 12.6_
  
  - [x] 14.2 Set up Quick_Suite dashboard
    - Create dashboard for brand processing status
    - Add visualizations for combo matching statistics
    - Display brands and combos requiring human review
    - Add drill-down capabilities
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.7_

- [x] 15. Documentation and Deployment Guide
  - [x] 15.1 Create README.md
    - Document project overview
    - Add setup instructions
    - Include deployment steps
    - Add usage examples
    - _Requirements: 13.6_
  
  - [x] 15.2 Create deployment guide
    - Document Terraform deployment process
    - Document agent deployment process
    - Document environment configuration
    - Add troubleshooting section
    - _Requirements: 11.13_
  
  - [x] 15.3 Create .gitignore file
    - Exclude sensitive data and credentials
    - Exclude Terraform state files
    - Exclude Python virtual environment
    - Exclude temporary files
    - _Requirements: 13.7_

- [x] 16. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. MCP Integration for Commercial Assessment
  - [x] 17.1 Configure Crunchbase MCP Server
    - Add Crunchbase MCP configuration to .kiro/settings/mcp.json
    - Set up API key in environment variables
    - Test MCP connectivity
    - _Requirements: 15.1, 15.2_
  
  - [x] 17.2 Build Custom Brand Registry MCP Server
    - Create Python MCP server for brand registry
    - Implement search_brands tool
    - Implement get_brand_info tool
    - Implement validate_sector tool
    - Connect to Athena database
    - _Requirements: 15.1_
  
  - [x] 17.3 Integrate MCP into Commercial Assessment Agent
    - Add MCP tool usage to agent
    - Implement query logic for brand validation
    - Add fallback to web search
    - Implement response caching in DynamoDB
    - Add error handling and retry logic
    - _Requirements: 15.3, 15.4, 15.5, 15.9, 15.10_
  
  - [x] 17.4 Write tests for MCP integration
    - Test MCP connectivity
    - Test brand validation with MCP data
    - Test fallback to web search
    - Test caching mechanism
    - Test error handling
    - _Requirements: 15.6_

- [ ] 18. Feedback Processing Agent
  - [ ] 18.1 Implement feedback parsing tools
    - Create parse_feedback tool for natural language processing
    - Create identify_misclassified_combos tool
    - Create analyze_feedback_category tool
    - _Requirements: 14.2, 14.3_
  
  - [ ] 18.2 Implement refinement prompt generation
    - Create generate_refinement_prompt tool
    - Analyze feedback to extract actionable guidance
    - Generate specific prompts for Metadata Production Agent
    - _Requirements: 14.4, 14.5_
  
  - [ ] 18.3 Implement feedback storage
    - Create store_feedback tool for S3 and DynamoDB
    - Create retrieve_feedback_history tool
    - Implement version tracking
    - _Requirements: 14.4, 14.9_
  
  - [ ] 18.4 Implement agent handler
    - Set up Strands Agent with instructions
    - Register all tools
    - Implement handler function for AgentCore
    - _Requirements: 14.5_
  
  - [ ] 18.5 Write tests for feedback processing agent
    - Test feedback parsing with various input types
    - Test refinement prompt generation
    - Test feedback storage and retrieval
    - Test combo ID extraction
    - _Requirements: 14.2, 14.3, 14.4_

- [ ] 19. Learning Analytics Agent
  - [ ] 19.1 Implement trend analysis tools
    - Create analyze_feedback_trends tool
    - Create identify_common_issues tool
    - Aggregate feedback across brands
    - _Requirements: 16.6, 16.11_
  
  - [ ] 19.2 Implement accuracy metrics calculation
    - Create calculate_accuracy_metrics tool
    - Create calculate_improvement_rate tool
    - Track false positive/negative rates
    - _Requirements: 16.7, 16.8_
  
  - [ ] 19.3 Implement report generation
    - Create generate_improvement_report tool
    - Create identify_problematic_brands tool
    - Generate executive summaries
    - _Requirements: 16.13_
  
  - [ ] 19.4 Implement agent handler
    - Set up Strands Agent with instructions
    - Register all tools
    - Implement handler function for AgentCore
    - _Requirements: 16.6_
  
  - [ ] 19.5 Write tests for learning analytics agent
    - Test trend analysis with sample data
    - Test accuracy metrics calculation
    - Test report generation
    - Test problematic brand identification
    - _Requirements: 16.7, 16.8, 16.13_

- [ ] 20. Human Review Interface
  - [ ] 20.1 Extend Quick_Suite dashboard for review
    - Create brand review page
    - Display classification results grouped by brand
    - Show regex pattern and MCCID list
    - Display sample matched and excluded narratives
    - Add confidence score visualization
    - _Requirements: 14.2, 12.1, 12.2_
  
  - [ ] 20.2 Implement feedback input forms
    - Create general feedback text input
    - Create specific combo flagging interface
    - Add approve/reject buttons
    - Implement feedback submission
    - _Requirements: 14.3_
  
  - [ ] 20.3 Implement feedback history view
    - Display all previous feedback for a brand
    - Show metadata version history
    - Display iteration count and trends
    - _Requirements: 14.9_
  
  - [ ] 20.4 Add real-time status updates
    - Show processing status per brand
    - Display when feedback is being processed
    - Show regeneration progress
    - _Requirements: 12.1_

- [ ] 21. Updated Workflow Integration
  - [ ] 21.1 Update Step Functions workflow
    - Add human review phase after classification
    - Add feedback processing loop
    - Add iteration limit checks (max 10)
    - Add escalation path for exceeded limits
    - _Requirements: 14.6, 14.7, 14.8, 14.10, 16.14_
  
  - [ ] 21.2 Implement feedback processing loop
    - Invoke Feedback Processing Agent
    - Regenerate metadata based on feedback
    - Re-apply metadata to combos
    - Re-run classification agents
    - Return to human review
    - _Requirements: 14.5, 14.6, 14.7_
  
  - [ ] 21.3 Update Lambda functions
    - Create Lambda for feedback submission
    - Create Lambda for feedback processing trigger
    - Update orchestrator Lambda for new phases
    - _Requirements: 14.5_
  
  - [ ] 21.4 Update monitoring and logging
    - Add CloudWatch metrics for feedback phases
    - Log all feedback submissions
    - Track iteration counts per brand
    - Monitor escalations
    - _Requirements: 14.4, 15.8_

- [ ] 22. Integration Testing for HITL Workflow
  - [ ] 22.1 Write integration test for feedback loop
    - Set up test brand with known issues
    - Submit feedback through interface
    - Verify feedback processing
    - Verify metadata regeneration
    - Verify re-classification
    - Verify return to human review
    - _Requirements: 14.1-14.11_
  
  - [ ] 22.2 Write integration test for MCP validation
    - Test Crunchbase MCP integration
    - Test brand validation workflow
    - Test fallback to web search
    - Verify caching behavior
    - _Requirements: 15.1-15.10_
  
  - [ ] 22.3 Write integration test for learning analytics
    - Generate sample feedback data
    - Run trend analysis
    - Verify accuracy metrics
    - Verify report generation
    - _Requirements: 16.6-16.14_

- [ ] 23. Final System Testing and Deployment
  - [ ] 23.1 End-to-end testing with HITL
    - Test complete workflow from ingestion to approval
    - Include multiple feedback iterations
    - Test iteration limit and escalation
    - Verify all agents working together
    - _Requirements: All_
  
  - [ ] 23.2 Deploy all agents to production
    - Deploy Feedback Processing Agent
    - Deploy Learning Analytics Agent
    - Update existing agents with MCP integration
    - Deploy to production environment
    - _Requirements: 11.1_
  
  - [ ] 23.3 Configure production monitoring
    - Set up CloudWatch alarms for new phases
    - Configure SNS notifications
    - Set up Quick_Suite production dashboard
    - _Requirements: 12.6, 12.7_
  
  - [ ] 23.4 Create operational runbooks
    - Document feedback processing procedures
    - Document escalation procedures
    - Document MCP troubleshooting
    - Document learning analytics interpretation
    - _Requirements: 11.13_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- All tests are REQUIRED to ensure system correctness and reliability
- All agents use Python 3.12+ and Strands API
- All infrastructure uses Terraform for portability
- AWS region is eu-west-1 for all services
