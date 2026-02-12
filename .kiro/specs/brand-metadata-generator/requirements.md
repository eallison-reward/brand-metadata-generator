# Requirements Document: Brand Metadata Generator

## Introduction

The Brand Metadata Generator is a multi-agent system designed to automatically generate classification metadata for over 3,000 retail brands in a database. The system produces regex patterns for narrative matching, lists of valid MCCIDs (Merchant Category Codes), and optional agent confirmation flags for each brand. The system must handle complex scenarios including payment wallet complications and brand classification ties while maintaining high accuracy through coordinated agent workflows.

## Glossary

- **Brand**: A retail entity identified by brandid, brandname, and sector
- **Metadata**: Classification data including regex patterns, MCCID lists, and confirmation flags
- **MCCID**: Merchant Category Code Identifier, a standardized code for business types
- **Narrative**: Bank transaction description text associated with a brand
- **Combo**: A combination record linking brandid, mid, mccid, and narrative
- **Payment_Wallet**: Third-party payment processors (PayPal, Square) that alter narratives
- **Tie**: A scenario where a narrative/MCCID combination matches multiple brands
- **Orchestrator**: The coordinating agent that manages workflow between other agents
- **Data_Transformation_Agent**: Agent responsible for data preparation and validation
- **Evaluator_Agent**: Agent that assesses data accuracy and identifies issues
- **Metadata_Production_Agent**: Agent that generates regex patterns and MCCID lists
- **Commercial_Assessment_Agent**: Agent that validates brand identity against real-world data
- **Confirmation_Agent**: Agent that reviews brands requiring manual verification
- **Tiebreaker_Agent**: Agent that resolves multi-brand matches
- **Strands_API**: The API platform used for all agent implementations
- **AgentCore**: AWS Bedrock runtime environment for agent deployment
- **Athena**: AWS service for querying data from S3
- **Athena_Database**: The Athena database named brand_metadata_generator_db containing all source tables
- **Quick_Suite**: AWS technology for agent-specific user interface and monitoring
- **Terraform**: Infrastructure as Code (IaC) tool for managing AWS deployments
- **GitHub_Repository**: Version control repository for storing all project code, configurations, and documentation

## Requirements

### Requirement 1: Data Ingestion and Preparation

**User Story:** As a data engineer, I want to ingest brand and transaction data from AWS Athena, so that the system can process all necessary information for metadata generation.

#### Acceptance Criteria

1. WHEN the system starts, THE Data_Transformation_Agent SHALL query the brand table from Athena database brand_metadata_generator_db and retrieve all records with brandid, brandname, and sector
2. WHEN the system starts, THE Data_Transformation_Agent SHALL query the brand_to_check table from Athena database brand_metadata_generator_db and retrieve all brandid values requiring metadata generation
3. WHEN the system starts, THE Data_Transformation_Agent SHALL query the combo table from Athena database brand_metadata_generator_db and retrieve all records with ccid, mid, brandid, mccid, and narrative
4. WHEN the system starts, THE Data_Transformation_Agent SHALL query the mcc table from Athena database brand_metadata_generator_db and retrieve all records with mccid, mcc_desc, and sector
5. WHEN querying Athena, THE Data_Transformation_Agent SHALL use AWS region eu-west-1 and database brand_metadata_generator_db
6. WHEN data is retrieved, THE Data_Transformation_Agent SHALL validate that all foreign key relationships between tables are intact
7. IF any data retrieval fails, THEN THE Data_Transformation_Agent SHALL log the error and notify the Orchestrator

### Requirement 2: Brand Metadata Generation

**User Story:** As a system operator, I want the system to generate regex patterns and MCCID lists for each brand, so that transactions can be accurately classified.

#### Acceptance Criteria

1. FOR ALL brandid values in brand_to_check, THE Metadata_Production_Agent SHALL generate a regular expression pattern for narrative matching
2. FOR ALL brandid values in brand_to_check, THE Metadata_Production_Agent SHALL generate a list of legitimate mccid values
3. WHEN generating regex patterns, THE Metadata_Production_Agent SHALL analyze all narrative values associated with the brandid in the combo table
4. WHEN generating MCCID lists, THE Metadata_Production_Agent SHALL analyze all mccid values associated with the brandid in the combo table
5. WHEN metadata generation is complete, THE Metadata_Production_Agent SHALL return the regex pattern and MCCID list to the Orchestrator
6. THE Metadata_Production_Agent SHALL implement all functionality using the Strands_API

### Requirement 3: Payment Wallet Detection and Handling

**User Story:** As a data analyst, I want the system to detect and handle payment wallet complications, so that brand classification is not distorted by irrelevant wallet text.

#### Acceptance Criteria

1. WHEN analyzing narratives, THE Evaluator_Agent SHALL detect the presence of payment wallet indicators including "PAYPAL", "PP", "SQ", and "SQUARE"
2. WHEN a payment wallet is detected in a narrative, THE Evaluator_Agent SHALL flag the associated combo record as wallet-affected
3. WHEN generating regex patterns for wallet-affected brands, THE Metadata_Production_Agent SHALL exclude wallet-specific text from the pattern
4. WHEN generating MCCID lists for wallet-affected brands, THE Evaluator_Agent SHALL identify potentially misclassified MCCIDs
5. WHEN wallet complications are detected, THE Evaluator_Agent SHALL provide guidance to the Metadata_Production_Agent on handling the affected data

### Requirement 4: Data Quality Assessment

**User Story:** As a quality assurance specialist, I want the system to identify dirty or inaccurate data, so that metadata generation is based on reliable information.

#### Acceptance Criteria

1. FOR ALL combo records associated with a brandid, THE Evaluator_Agent SHALL assess the consistency of narrative patterns
2. FOR ALL combo records associated with a brandid, THE Evaluator_Agent SHALL assess the consistency of MCCID associations
3. WHEN narrative patterns show high variance, THE Evaluator_Agent SHALL flag the brand as having inconsistent data
4. WHEN MCCID associations conflict with the brand sector, THE Evaluator_Agent SHALL flag potential misclassification
5. WHEN dirty data is identified, THE Evaluator_Agent SHALL generate prompts for the Metadata_Production_Agent describing the issues
6. THE Evaluator_Agent SHALL calculate a confidence score for each brand based on data quality

### Requirement 5: Commercial Brand Validation

**User Story:** As a brand analyst, I want the system to validate brand names and sectors against real-world identity, so that metadata reflects accurate commercial information.

#### Acceptance Criteria

1. FOR ALL brands in brand_to_check, THE Commercial_Assessment_Agent SHALL verify that the brandname corresponds to a real commercial entity
2. FOR ALL brands in brand_to_check, THE Commercial_Assessment_Agent SHALL verify that the sector classification is appropriate for the brand
3. WHEN a brand name does not match a known commercial entity, THE Commercial_Assessment_Agent SHALL flag the brand for review
4. WHEN a sector classification appears incorrect, THE Commercial_Assessment_Agent SHALL suggest alternative sectors to the Evaluator_Agent
5. THE Commercial_Assessment_Agent SHALL provide validation results to the Evaluator_Agent for incorporation into quality assessment

### Requirement 6: Agent Confirmation Flagging

**User Story:** As a system operator, I want brands with low confidence or complex issues to be flagged for agent confirmation, so that human review can ensure accuracy.

#### Acceptance Criteria

1. WHEN the Evaluator_Agent determines a brand has a confidence score below a defined threshold, THE System SHALL mark the brand as "Requiring Agent Confirmation"
2. WHEN payment wallet complications cannot be automatically resolved, THE System SHALL mark the brand as "Requiring Agent Confirmation"
3. WHEN commercial validation fails, THE System SHALL mark the brand as "Requiring Agent Confirmation"
4. WHEN a brand is marked "Requiring Agent Confirmation", THE Orchestrator SHALL route the brand to the Confirmation_Agent
5. THE Confirmation_Agent SHALL review flagged brands and either approve the generated metadata or request regeneration with specific guidance

### Requirement 7: Tie Resolution

**User Story:** As a classification specialist, I want the system to resolve ties where narrative/MCCID combinations match multiple brands, so that transactions are assigned to the correct brand.

#### Acceptance Criteria

1. WHEN analyzing combo records, THE Evaluator_Agent SHALL identify narrative and MCCID combinations that are associated with multiple brandid values
2. WHEN a tie is identified, THE Orchestrator SHALL route the tie case to the Tiebreaker_Agent
3. WHEN resolving a tie, THE Tiebreaker_Agent SHALL analyze the narrative text, MCCID, and brand characteristics to determine the most likely brand
4. WHEN a tie cannot be resolved with high confidence, THE Tiebreaker_Agent SHALL recommend splitting the regex pattern or MCCID list to disambiguate
5. THE Tiebreaker_Agent SHALL return the resolution decision to the Orchestrator for incorporation into metadata

### Requirement 8: Metadata Output and Storage

**User Story:** As a data consumer, I want generated metadata to be stored in a structured format in S3, so that it can be used for transaction classification.

#### Acceptance Criteria

1. FOR ALL brands in brand_to_check, THE Data_Transformation_Agent SHALL write the generated metadata to S3 bucket brand-generator-rwrd-023-eu-west-1
2. WHEN writing metadata, THE Data_Transformation_Agent SHALL structure the output with brandid, regex pattern, MCCID list, and optional confirmation flag
3. WHEN writing to S3, THE Data_Transformation_Agent SHALL use AWS region eu-west-1
4. THE Data_Transformation_Agent SHALL validate that the regex pattern is syntactically correct before writing
5. THE Data_Transformation_Agent SHALL validate that all MCCID values in the list exist in the mcc table before writing
6. WHEN validation fails, THE Data_Transformation_Agent SHALL log the error and request regeneration from the Metadata_Production_Agent

### Requirement 9: Orchestration and Workflow Management

**User Story:** As a system architect, I want an orchestrator to coordinate all agents, so that the workflow executes efficiently and handles errors gracefully.

#### Acceptance Criteria

1. THE Orchestrator SHALL initialize the workflow by instructing the Data_Transformation_Agent to ingest data
2. WHEN data ingestion is complete, THE Orchestrator SHALL distribute brands from brand_to_check to the Evaluator_Agent for assessment
3. WHEN evaluation is complete, THE Orchestrator SHALL route brands to the Metadata_Production_Agent for metadata generation
4. WHEN metadata generation is complete, THE Orchestrator SHALL route output to the Data_Transformation_Agent for validation and storage
5. WHEN a brand requires confirmation, THE Orchestrator SHALL route it to the Confirmation_Agent
6. WHEN a tie is detected, THE Orchestrator SHALL route it to the Tiebreaker_Agent
7. WHEN commercial validation is needed, THE Orchestrator SHALL coordinate between the Commercial_Assessment_Agent and Evaluator_Agent
8. THE Orchestrator SHALL implement the workflow using AWS Step Functions
9. IF any agent fails, THEN THE Orchestrator SHALL log the error and implement retry logic with exponential backoff

### Requirement 10: Iterative Metadata Refinement

**User Story:** As a quality assurance specialist, I want the system to iteratively refine metadata based on feedback, so that accuracy improves over multiple iterations.

#### Acceptance Criteria

1. WHEN the Data_Transformation_Agent identifies validation errors in generated metadata, THE Orchestrator SHALL send feedback to the Metadata_Production_Agent
2. WHEN the Confirmation_Agent rejects metadata, THE Orchestrator SHALL send specific guidance to the Metadata_Production_Agent for regeneration
3. WHEN the Tiebreaker_Agent provides disambiguation guidance, THE Metadata_Production_Agent SHALL incorporate it into regex pattern generation
4. THE Metadata_Production_Agent SHALL maintain context from previous iterations when regenerating metadata
5. THE System SHALL limit iterations to a maximum of 5 attempts per brand before escalating to human review

### Requirement 11: AWS Infrastructure Integration

**User Story:** As a DevOps engineer, I want the system to integrate with AWS services following best practices and use Terraform for infrastructure management, so that deployment is reliable, maintainable, and portable across environments.

#### Acceptance Criteria

1. THE System SHALL deploy all agents to AWS Bedrock AgentCore runtime
2. THE System SHALL use AWS Glue for data catalog management
3. THE System SHALL use AWS Lambda for serverless compute functions
4. THE System SHALL use AWS Step Functions for workflow orchestration
5. THE System SHALL use AWS Athena for data querying with database brand_metadata_generator_db
6. THE System SHALL use AWS S3 for data storage with bucket brand-generator-rwrd-023-eu-west-1
7. THE System SHALL use AWS Quick_Suite for agent-specific user interface and monitoring
8. WHERE AWS services are used, THE System SHALL operate in region eu-west-1
9. THE System SHALL follow best practices documented in AGENTCORE_DEPLOYMENT_BEST_PRACTICES.md
10. THE System SHALL implement appropriate IAM roles and policies for least-privilege access
11. THE System SHALL define all infrastructure using Terraform configuration files
12. THE System SHALL organize Terraform configurations to enable deployment to different AWS environments
13. WHEN deploying infrastructure, THE System SHALL use Terraform to provision all AWS resources
14. THE System SHALL maintain Terraform state files to track infrastructure changes

### Requirement 12: User Interface and Monitoring

**User Story:** As a system operator, I want to monitor system progress and review results through Quick_Suite, so that I can track metadata generation and intervene when necessary.

#### Acceptance Criteria

1. THE System SHALL provide a Quick_Suite dashboard showing the number of brands processed, in progress, and pending
2. THE System SHALL provide a Quick_Suite dashboard showing brands flagged for agent confirmation
3. THE System SHALL provide a Quick_Suite dashboard showing identified ties and their resolution status
4. WHEN a brand requires human review, THE System SHALL display the brand details and generated metadata in Quick_Suite
5. THE System SHALL allow operators to approve or reject metadata through the Quick_Suite interface
6. THE System SHALL log all agent activities and decisions for audit purposes
7. WHEN errors occur, THE System SHALL display error details and affected brands in Quick_Suite

### Requirement 13: Version Control and Repository Management

**User Story:** As a developer, I want all project code, configurations, and documentation stored in a GitHub repository, so that changes are tracked and the project can be collaboratively maintained.

#### Acceptance Criteria

1. THE System SHALL maintain all source code in a dedicated GitHub repository
2. THE System SHALL store all Terraform configuration files in the GitHub_Repository
3. THE System SHALL store all agent implementation code in the GitHub_Repository
4. THE System SHALL store all documentation including requirements, design, and deployment guides in the GitHub_Repository
5. THE System SHALL organize the repository with clear directory structure separating infrastructure code, agent code, and documentation
6. THE System SHALL include a README.md file describing the project, setup instructions, and deployment process
7. THE System SHALL include a .gitignore file to exclude sensitive data, credentials, and Terraform state files
8. THE System SHALL use Git branches for feature development and maintain a stable main branch
9. THE System SHALL require pull requests and code reviews before merging changes to the main branch
10. THE System SHALL tag releases with semantic versioning for deployment tracking
