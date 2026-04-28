#!/usr/bin/env python3
"""
Script to retrieve Axon record by ID
Usage: python get_record.py --record-id <record_id> [--output <file>]
"""

import argparse
import json
import sys
from pyaxon import Axon, PyaxonError, ServerError, ClientError


def extract_record_id_from_url(url_or_id):
    """
    Extract record ID from Axon URL or return as-is if already an ID
    URL format: https://axonsv.app.intel.com/apps/record-viewer/{RECORD_ID}/{CONTENT_TYPE}?...
    """
    if url_or_id.startswith('http'):
        parts = url_or_id.split('/')
        # Find 'record-viewer' and get the next part
        try:
            idx = parts.index('record-viewer')
            return parts[idx + 1]
        except (ValueError, IndexError):
            print(f"Error: Could not extract record ID from URL: {url_or_id}", file=sys.stderr)
            sys.exit(1)
    return url_or_id


def get_record(record_id, host="https://axonsv.app.intel.com", output_file=None, verbose=False):
    """
    Retrieve Axon record by ID and optionally save to file
    """
    try:
        with Axon(host=host) as axon:
            if verbose:
                print(f"Fetching record: {record_id}", file=sys.stderr)
            
            record = axon.failure.get(failure_id=record_id)
            
            if verbose:
                print(f"Record retrieved successfully", file=sys.stderr)
                print(f"Content types: {list(record.get('content', {}).keys())}", file=sys.stderr)
            
            # Format the output
            result = {
                "record_id": record_id,
                "metadata": record.get("metadata", {}),
                "content": {}
            }
            
            # Summarize content
            for content_type, content_data in record.get("content", {}).items():
                objects = content_data.get("objects", [])
                result["content"][content_type] = {
                    "object_count": len(objects),
                    "objects": objects
                }
            
            output = json.dumps(result, indent=2)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(output)
                print(f"Record saved to: {output_file}", file=sys.stderr)
            else:
                print(output)
            
            return result
            
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
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve Axon record by ID or URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_record.py --record-id c425ebc4-aed6-4c6e-8eb1-a47726ffce47
  python get_record.py --record-id "https://axonsv.app.intel.com/apps/record-viewer/c425ebc4-aed6-4c6e-8eb1-a47726ffce47/intel-svtools-report-v1"
  python get_record.py --record-id c425ebc4-aed6-4c6e-8eb1-a47726ffce47 --output record.json
        """
    )
    
    parser.add_argument(
        '--record-id',
        required=True,
        help='Axon record ID or full URL'
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
    
    # Extract record ID from URL if needed
    record_id = extract_record_id_from_url(args.record_id)
    
    if args.verbose:
        print(f"Using record ID: {record_id}", file=sys.stderr)
    
    get_record(record_id, host=args.host, output_file=args.output, verbose=args.verbose)


if __name__ == '__main__':
    main()
