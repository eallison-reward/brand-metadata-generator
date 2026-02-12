# Storage module - S3, Athena, and Glue resources

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# S3 bucket for data storage
resource "aws_s3_bucket" "data_bucket" {
  bucket = var.s3_bucket_name

  tags = merge(
    var.common_tags,
    {
      Name = var.s3_bucket_name
    }
  )
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "data_bucket_versioning" {
  bucket = aws_s3_bucket.data_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket_encryption" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "data_bucket_public_access" {
  bucket = aws_s3_bucket.data_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Glue catalog database
resource "aws_glue_catalog_database" "athena_database" {
  name        = var.athena_database
  description = "Database for brand metadata generator"

  tags = var.common_tags
}

# Glue table: brand
resource "aws_glue_catalog_table" "brand" {
  name          = "brand"
  database_name = aws_glue_catalog_database.athena_database.name

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_bucket.id}/source-data/brand/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
      parameters = {
        "field.delim" = ","
      }
    }

    columns {
      name = "brandid"
      type = "int"
    }

    columns {
      name = "brandname"
      type = "string"
    }

    columns {
      name = "sector"
      type = "string"
    }
  }
}

# Glue table: brand_to_check
resource "aws_glue_catalog_table" "brand_to_check" {
  name          = "brand_to_check"
  database_name = aws_glue_catalog_database.athena_database.name

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_bucket.id}/source-data/brand_to_check/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
      parameters = {
        "field.delim" = ","
      }
    }

    columns {
      name = "brandid"
      type = "int"
    }
  }
}

# Glue table: combo
resource "aws_glue_catalog_table" "combo" {
  name          = "combo"
  database_name = aws_glue_catalog_database.athena_database.name

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_bucket.id}/source-data/combo/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
      parameters = {
        "field.delim" = ","
      }
    }

    columns {
      name = "ccid"
      type = "int"
    }

    columns {
      name = "mid"
      type = "string"
    }

    columns {
      name = "brandid"
      type = "int"
    }

    columns {
      name = "mccid"
      type = "int"
    }

    columns {
      name = "narrative"
      type = "string"
    }
  }
}

# Glue table: mcc
resource "aws_glue_catalog_table" "mcc" {
  name          = "mcc"
  database_name = aws_glue_catalog_database.athena_database.name

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_bucket.id}/source-data/mcc/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
      parameters = {
        "field.delim" = ","
      }
    }

    columns {
      name = "mccid"
      type = "int"
    }

    columns {
      name = "mcc_desc"
      type = "string"
    }

    columns {
      name = "sector"
      type = "string"
    }
  }
}

# Athena workgroup
resource "aws_athena_workgroup" "main" {
  name = "${var.project_name}-${var.environment}"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_bucket.id}/query-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = var.common_tags
}
