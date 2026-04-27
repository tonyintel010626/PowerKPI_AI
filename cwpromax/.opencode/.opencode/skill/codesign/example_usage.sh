#!/bin/bash
# Example usage of codesign.py standalone tool

# Example 1: Basic query
echo "Example 1: Basic query"
python codesign.py -q "What is PMC?" -output_file ./pmc_info.json

# Read the result
cat ./pmc_info.json

echo -e "\n---\n"

# Example 2: Query with verbose output
echo "Example 2: Verbose query with limited context"
python codesign.py \
  -q "What are eSPI register offsets?" \
  -output_file ./espi_regs.json \
  --limit 5 \
  --verbose

echo -e "\n---\n"

# Example 3: Parse result in bash
echo "Example 3: Parse result programmatically"
python codesign.py -q "Explain PCIe enumeration" -output_file ./result.json --limit 3

# Check status and extract answer
STATUS=$(jq -r '.status' ./result.json)
if [ "$STATUS" == "success" ]; then
    echo "Success! Answer:"
    jq -r '.response.answer' ./result.json
    echo -e "\nReferences:"
    jq -r '.response.references[]' ./result.json
else
    echo "Error:"
    jq -r '.response.error' ./result.json
fi

echo -e "\n---\n"

# Example 4: Conversational follow-up
echo "Example 4: Conversational follow-up"
python codesign.py -q "What causes PMC crashes?" -output_file ./q1.json -v

# Extract thread_id
THREAD_ID=$(jq -r '.query.thread_id' ./q1.json)
echo "Thread ID: $THREAD_ID"

# Follow-up question
python codesign.py \
  -q "What registers should I check for PMC debug?" \
  -output_file ./q2.json \
  --thread_id $THREAD_ID
