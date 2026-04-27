#!/usr/bin/env python3
"""
Example Python usage of codesign.py standalone tool
Demonstrates programmatic interaction with CoDesign
"""

import json
import subprocess
import sys
from pathlib import Path

# Path to codesign.py
CODESIGN_TOOL = Path(__file__).parent / "codesign.py"


def query_codesign(question, output_file="./temp_result.json", **kwargs):
    """
    Query CoDesign and return structured response
    
    Args:
        question: Question to ask
        output_file: Where to save JSON output
        **kwargs: Additional arguments (limit, source, thread_id, verbose, etc.)
    
    Returns:
        dict: Parsed JSON response
    """
    cmd = [
        sys.executable,
        str(CODESIGN_TOOL),
        "-q", question,
        "-output_file", output_file
    ]
    
    # Add optional arguments
    if kwargs.get('limit'):
        cmd.extend(["--limit", str(kwargs['limit'])])
    if kwargs.get('source'):
        cmd.extend(["--source", kwargs['source']])
    if kwargs.get('thread_id'):
        cmd.extend(["--thread_id", kwargs['thread_id']])
    if kwargs.get('verbose'):
        cmd.append("--verbose")
    if kwargs.get('graph_id'):
        cmd.extend(["--graph_id", kwargs['graph_id']])
    
    # Execute command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Read output
    with open(output_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print("=" * 60)
    print("Example 1: Basic Query")
    print("=" * 60)
    
    result = query_codesign(
        "What is PMC?",
        output_file="./example_pmc.json",
        limit=3,
        verbose=True
    )
    
    if result['status'] == 'success':
        print(f"✅ Success!")
        print(f"\nAnswer:\n{result['response']['answer'][:200]}...")
        print(f"\nReferences: {len(result['response']['references'])} found")
    else:
        print(f"❌ Error: {result['response']['error']}")
    
    print("\n" + "=" * 60)
    print("Example 2: Conversational Follow-up")
    print("=" * 60)
    
    # First question
    result1 = query_codesign(
        "What causes PCIe link training failures?",
        output_file="./example_q1.json",
        limit=5
    )
    
    if result1['status'] == 'success':
        thread_id = result1['query']['thread_id']
        print(f"Thread ID: {thread_id}")
        print(f"\nFirst answer:\n{result1['response']['answer'][:150]}...")
        
        # Follow-up question
        result2 = query_codesign(
            "What registers should I check?",
            output_file="./example_q2.json",
            thread_id=thread_id
        )
        
        if result2['status'] == 'success':
            print(f"\nFollow-up answer:\n{result2['response']['answer'][:150]}...")
        else:
            print(f"\n❌ Follow-up error: {result2['response']['error']}")
    else:
        print(f"❌ Error: {result1['response']['error']}")
    
    print("\n" + "=" * 60)
    print("Example 3: Error Handling")
    print("=" * 60)
    
    # Example with minimal context (may return sparse answer)
    result = query_codesign(
        "What is the airspeed velocity of an unladen swallow?",
        output_file="./example_error.json",
        limit=1
    )
    
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        if result['response']['answer']:
            print(f"Answer: {result['response']['answer'][:100]}...")
        else:
            print("No answer found (question may be out of scope)")
    else:
        print(f"Error: {result['response']['error']}")
    
    print("\n" + "=" * 60)
    print("Example 4: Integration in Debug Workflow")
    print("=" * 60)
    
    # Simulate a debug workflow
    debug_questions = [
        ("What is eSPI?", 3),
        ("What are common eSPI boot failures?", 5),
        ("What registers indicate eSPI errors?", 5),
    ]
    
    for i, (question, limit) in enumerate(debug_questions, 1):
        print(f"\n[Step {i}] {question}")
        result = query_codesign(
            question,
            output_file=f"./debug_step_{i}.json",
            limit=limit
        )
        
        if result['status'] == 'success':
            answer = result['response']['answer'][:120]
            print(f"   ✅ {answer}...")
        else:
            print(f"   ❌ {result['response']['error']}")
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
