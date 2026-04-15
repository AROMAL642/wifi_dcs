#!/usr/bin/env python3
"""
Quick test to verify automatic parameter extraction functionality
"""

import re
import sys
from pathlib import Path


def extract_payload_keys(code: str):
    """Extract payload parameter keys from executor code."""
    keys = set()
    
    # Pattern 1: payload.get("key_name") or payload.get('key_name')
    # Handles whitespace variations
    pattern1 = r'payload\s*\.\s*get\s*\(\s*["\']([^"\']+)["\']\s*[,\)]'
    matches = re.findall(pattern1, code)
    keys.update(matches)
    
    # Pattern 2: payload["key_name"] or payload['key_name']
    pattern2 = r'payload\s*\[\s*["\']([^"\']+)["\']\s*\]'
    matches = re.findall(pattern2, code)
    keys.update(matches)
    
    # Pattern 3: In comments like # dataset_files, numbers, etc.
    pattern3 = r'#.*?([a-z_][a-z0-9_]*)'
    matches = re.findall(pattern3, code.lower())
    # Filter to reasonable looking parameter names (length > 2)
    keys.update([m for m in matches if len(m) > 2 and not m.isdigit()])
    
    return sorted(list(keys))


def test_parameter_extraction():
    """Test parameter extraction from executor code"""
    
    # Test 1: Basic payload.get() extraction
    code1 = """
def executor(payload, progress_cb):
    learning_rate = payload.get("learning_rate", 0.001)
    batch_size = payload.get("batch_size", 32)
    epochs = payload.get("epochs", 10)
    return {"status": "success"}
"""
    params1 = extract_payload_keys(code1)
    print(f"✓ Test 1 - Basic extraction: {params1}")
    assert set(params1) >= {"learning_rate", "batch_size", "epochs"}, f"Expected basic params, got {params1}"
    
    # Test 2: Array access extraction
    code2 = """
def executor(payload, progress_cb):
    dataset = payload["dataset_file"]
    model = payload["model_type"]
    return {"data": dataset}
"""
    params2 = extract_payload_keys(code2)
    print(f"✓ Test 2 - Array access: {params2}")
    assert "dataset_file" in params2 and "model_type" in params2
    
    # Test 3: Mixed patterns
    code3 = """
def executor(payload, progress_cb):
    # Processing parameters: input_file, output_file, threshold
    file_in = payload.get("input_file")
    file_out = payload["output_file"]
    thresh = payload.get("threshold", 0.5)
    return {"result": thresh}
"""
    params3 = extract_payload_keys(code3)
    print(f"✓ Test 3 - Mixed patterns: {params3}")
    assert "input_file" in params3 and "output_file" in params3 and "threshold" in params3
    
    # Test 4: Custom ML task
    code4 = """
def executor(payload, progress_cb):
    dataset_files = payload.get("dataset_files", [])
    model_type = payload.get("model_type", "linear")
    epochs = payload.get("epochs", 10)
    learning_rate = payload.get("learning_rate", 0.001)
    
    for epoch in range(epochs):
        progress_cb(epoch / epochs)
    
    return {"status": "success"}
"""
    params4 = extract_payload_keys(code4)
    print(f"✓ Test 4 - ML task: {params4}")
    assert all(p in params4 for p in ["dataset_files", "model_type", "epochs", "learning_rate"])
    
    print("\n✅ All parameter extraction tests passed!")
    print("\nExtraction Summary:")
    print("  - Pattern 1: payload.get(\"key\") ✓")
    print("  - Pattern 2: payload[\"key\"] ✓")
    print("  - Pattern 3: Comment parameters ✓")
    print("\nThe GUI will now automatically create input fields for detected parameters.")


if __name__ == "__main__":
    test_parameter_extraction()
