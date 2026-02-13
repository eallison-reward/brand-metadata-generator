# QuickSight dashboard for brand metadata generator monitoring

# Note: QuickSight requires manual setup of data sources and user permissions
# This configuration provides the dashboard template structure

# QuickSight data source for Athena
resource "aws_quicksight_data_source" "athena" {
  count = var.enable_quicksight ? 1 : 0

  data_source_id = "brand-metagen-athena-${var.environment}"
  name           = "Brand Metadata Generator Athena"
  type           = "ATHENA"

  parameters {
    athena {
      work_group = "primary"
    }
  }

  permission {
    principal = var.quicksight_principal_arn
    actions = [
      "quicksight:DescribeDataSource",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:PassDataSource",
      "quicksight:UpdateDataSource",
      "quicksight:DeleteDataSource",
      "quicksight:UpdateDataSourcePermissions"
    ]
  }

  tags = var.common_tags
}

# QuickSight data set for brand processing status
resource "aws_quicksight_data_set" "brand_status" {
  count = var.enable_quicksight ? 1 : 0

  data_set_id = "brand-metagen-status-${var.environment}"
  name        = "Brand Processing Status"
  import_mode = "DIRECT_QUERY"

  physical_table_map {
    physical_table_map_id = "brand-status-table"

    custom_sql {
      data_source_arn = aws_quicksight_data_source.athena[0].arn
      name            = "Brand Status Query"
      sql_query       = <<-SQL
        SELECT 
          brandid,
          brandname,
          processing_status,
          metadata_generated,
          combos_matched,
          combos_confirmed,
          combos_excluded,
          requires_human_review,
          last_updated
        FROM brand_metadata_generator_db.brand
        WHERE processing_status IS NOT NULL
      SQL
    }
  }

  tags = var.common_tags
}

# QuickSight data set for combo matching statistics
resource "aws_quicksight_data_set" "combo_stats" {
  count = var.enable_quicksight ? 1 : 0

  data_set_id = "brand-metagen-combo-stats-${var.environment}"
  name        = "Combo Matching Statistics"
  import_mode = "DIRECT_QUERY"

  physical_table_map {
    physical_table_map_id = "combo-stats-table"

    custom_sql {
      data_source_arn = aws_quicksight_data_source.athena[0].arn
      name            = "Combo Stats Query"
      sql_query       = <<-SQL
        SELECT 
          b.brandid,
          b.brandname,
          COUNT(DISTINCT c.ccid) as total_combos,
          COUNT(DISTINCT CASE WHEN c.confirmed = true THEN c.ccid END) as confirmed_combos,
          COUNT(DISTINCT CASE WHEN c.excluded = true THEN c.ccid END) as excluded_combos,
          COUNT(DISTINCT CASE WHEN c.requires_review = true THEN c.ccid END) as review_required
        FROM brand_metadata_generator_db.brand b
        LEFT JOIN brand_metadata_generator_db.combo c ON b.brandid = c.brandid
        GROUP BY b.brandid, b.brandname
      SQL
    }
  }

  tags = var.common_tags
}

# QuickSight data set for tie resolution
resource "aws_quicksight_data_set" "tie_resolution" {
  count = var.enable_quicksight ? 1 : 0

  data_set_id = "brand-metagen-ties-${var.environment}"
  name        = "Tie Resolution Status"
  import_mode = "DIRECT_QUERY"

  physical_table_map {
    physical_table_map_id = "tie-resolution-table"

    custom_sql {
      data_source_arn = aws_quicksight_data_source.athena[0].arn
      name            = "Tie Resolution Query"
      sql_query       = <<-SQL
        SELECT 
          ccid,
          bankid,
          narrative,
          mccid,
          matched_brands,
          resolution_status,
          selected_brandid,
          confidence_score,
          requires_human_review
        FROM brand_metadata_generator_db.combo
        WHERE matched_brands > 1
      SQL
    }
  }

  tags = var.common_tags
}

# Output QuickSight dashboard URL (manual setup required)
output "quicksight_setup_instructions" {
  value = var.enable_quicksight ? "QuickSight data sets created. See docs/QUICKSIGHT_DASHBOARD_SETUP.md for setup instructions." : "QuickSight is disabled. Set enable_quicksight = true to enable."
}
