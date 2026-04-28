#!/usr/bin/env python3
"""
Script to download complete Axon record with all objects
Usage: python download_record.py --record-id <record_id> --output-dir <directory>
"""

import argparse
import json
import os
import sys
from pathlib import Path
from pyaxon import Axon, PyaxonError, ServerError, ClientError


def extract_record_id_from_url(url_or_id):
    """Extract record ID from Axon URL or return as-is if already an ID"""
    if url_or_id.startswith('http'):
        parts = url_or_id.split('/')
        try:
            idx = parts.index('record-viewer')
            return parts[idx + 1]
        except (ValueError, IndexError):
            print(f"Error: Could not extract record ID from URL: {url_or_id}", file=sys.stderr)
            sys.exit(1)
    return url_or_id


def download_record(record_id, output_dir, host="https://axonsv.app.intel.com", verbose=False):
    """
    Download complete Axon record with all content and objects
    """
    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        with Axon(host=host) as axon:
            if verbose:
                print(f"Fetching record: {record_id}", file=sys.stderr)
            
            record = axon.failure.get(failure_id=record_id)
            
            if verbose:
                print(f"Record retrieved successfully", file=sys.stderr)
            
            # Save metadata
            metadata_file = output_path / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(record.get("metadata", {}), f, indent=2)
            
            if verbose:
                print(f"Saved metadata to: {metadata_file}", file=sys.stderr)
            
            # Save record summary
            summary = {
                "record_id": record_id,
                "metadata_file": "metadata.json",
                "content_types": {}
            }
            
            # Process each content type
            for content_type, content_data in record.get("content", {}).items():
                if verbose:
                    print(f"Processing content type: {content_type}", file=sys.stderr)
                
                # Create directory for this content type
                content_dir = output_path / content_type
                content_dir.mkdir(exist_ok=True)
                
                objects = content_data.get("objects", [])
                summary["content_types"][content_type] = {
                    "object_count": len(objects),
                    "directory": content_type
                }
                
                # Save each object
                for idx, obj in enumerate(objects):
                    obj_id = obj.get('id', f'object_{idx}')
                    # Sanitize filename
                    safe_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in str(obj_id))
                    obj_file = content_dir / f"{safe_id}.json"
                    
                    with open(obj_file, 'w') as f:
                        json.dump(obj, f, indent=2)
                    
                    if verbose:
                        print(f"  Saved object: {obj_file.name}", file=sys.stderr)
            
            # Save summary
            summary_file = output_path / "summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"Record downloaded successfully to: {output_path}", file=sys.stderr)
            print(f"Summary:", file=sys.stderr)
            print(json.dumps(summary, indent=2))
            
            return summary
            
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
        description="Download complete Axon record with all objects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_record.py --record-id c425ebc4-aed6-4c6e-8eb1-a47726ffce47 --output-dir ./axon_data
  python download_record.py --record-id "https://axonsv.app.intel.com/apps/record-viewer/c425ebc4-aed6-4c6e-8eb1-a47726ffce47/intel-svtools-report-v1" --output-dir ./output
        """
    )
    
    parser.add_argument(
        '--record-id',
        required=True,
        help='Axon record ID or full URL'
    )
    
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for downloaded files'
    )
    
    parser.add_argument(
        '--host',
        default='https://axonsv.app.intel.com',
        help='Axon host URL (default: https://axonsv.app.intel.com)'
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
    
    download_record(record_id, args.output_dir, host=args.host, verbose=args.verbose)


if __name__ == '__main__':
    main()
