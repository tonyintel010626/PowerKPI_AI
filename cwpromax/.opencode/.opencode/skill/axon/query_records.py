#!/usr/bin/env python3
"""
Script to query Axon records using MongoDB-style queries
Usage: python query_records.py --query '{"metadata.platform": "MTL"}' [--limit 10]
"""

import argparse
import json
import sys
from pyaxon import Axon, PyaxonError, ServerError, ClientError


def query_records(query, database="failures", collection="records", 
                  host="https://axonsv.app.intel.com", limit=None, output_file=None, verbose=False):
    """
    Query Axon records using MongoDB-style query
    """
    try:
        # Parse query if it's a string
        if isinstance(query, str):
            query = json.loads(query)
        
        with Axon(host=host) as axon:
            if verbose:
                print(f"Executing query: {json.dumps(query, indent=2)}", file=sys.stderr)
                print(f"Database: {database}, Collection: {collection}", file=sys.stderr)
            
            # Execute query
            results = axon.query.mongodb.execute(
                database=database,
                collection=collection,
                query=query
            )
            
            # Apply limit if specified
            if limit:
                results = results[:limit]
            
            if verbose:
                print(f"Found {len(results)} records", file=sys.stderr)
            
            # Format output
            output_data = {
                "query": query,
                "database": database,
                "collection": collection,
                "count": len(results),
                "results": results
            }
            
            output = json.dumps(output_data, indent=2)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(output)
                print(f"Results saved to: {output_file}", file=sys.stderr)
            else:
                print(output)
            
            return output_data
            
    except json.JSONDecodeError as e:
        print(f"Invalid JSON query: {e}", file=sys.stderr)
        sys.exit(1)
    except ClientError as e:
        print(f"Client error (4xx): {e}", file=sys.stderr)
        sys.exit(1)
    except ServerError as e:
        print(f"Server error (5xx): {e}", file=sys.stderr)
        sys.exit(1)
    except PyaxonError as e:
        print(f"Axon error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Query Axon records using MongoDB-style queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_records.py --query '{"metadata.platform": "MTL"}'
  python query_records.py --query '{"metadata.tags": "regression"}' --limit 5
  python query_records.py --query '{"metadata.status": "FAIL"}' --output results.json
  python query_records.py --query '{"metadata.created_at": {"$gte": "2024-01-01"}}' --limit 10
        """
    )
    
    parser.add_argument(
        '--query',
        required=True,
        help='MongoDB-style query in JSON format'
    )
    
    parser.add_argument(
        '--database',
        default='failures',
        help='Database name (default: failures)'
    )
    
    parser.add_argument(
        '--collection',
        default='records',
        help='Collection name (default: records)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of results to return'
    )
    
    parser.add_argument(
        '--host',
        default='https://axonsv.app.intel.com',
        help='Axon host URL (default: https://axonsv.app.intel.com)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file path (default: print to stdout)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    query_records(
        query=args.query,
        database=args.database,
        collection=args.collection,
        host=args.host,
        limit=args.limit,
        output_file=args.output,
        verbose=args.verbose
    )


if __name__ == '__main__':
    main()
