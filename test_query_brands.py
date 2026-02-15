#!/usr/bin/env python3
"""Test the query_brands_to_check handler."""

from lambda_functions.query_brands_to_check.handler import QueryBrandsToCheckHandler

def test_query_brands():
    """Test querying brands."""
    handler = QueryBrandsToCheckHandler()
    
    try:
        result = handler.execute({'limit': 5})
        print('Query result:')
        print('Total count:', result['total_count'])
        print('Brands:')
        for brand in result['brands']:
            print(f'  - {brand["brandid"]}: {brand["brandname"]} ({brand["sector"]}) - {brand["status"]}')
        
        # Test status filtering
        print('\nTesting status filtering (unprocessed):')
        result = handler.execute({'status': 'unprocessed', 'limit': 5})
        print('Unprocessed count:', result['total_count'])
        for brand in result['brands']:
            print(f'  - {brand["brandid"]}: {brand["brandname"]} - {brand["status"]}')
            
    except Exception as e:
        print('Error:', e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_query_brands()