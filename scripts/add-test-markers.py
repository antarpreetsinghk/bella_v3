#!/usr/bin/env python3
"""
Automatically add pytest markers to test functions based on patterns and rules.
This script intelligently categorizes tests to enable fast tiered testing.
"""

import os
import re
import sys
from pathlib import Path

# Marker categorization rules
MARKER_RULES = {
    # Smoke tests - fastest, most critical
    'smoke': [
        r'test.*health.*',
        r'test.*basic.*',
        r'test.*simple.*',
        r'test.*import.*',
        r'test.*connectivity.*',
        r'test.*startup.*',
        r'.*_basic$',
        r'.*_simple$',
    ],

    # Essential tests - core functionality
    'essential': [
        r'test.*extract.*',
        r'test.*parse.*',
        r'test.*format.*',
        r'test.*validate.*',
        r'test.*booking.*',
        r'test.*session.*',
        r'test.*call_flow.*',
        r'.*_core$',
        r'.*_main$',
    ],

    # Slow tests - performance or complex scenarios
    'slow': [
        r'test.*performance.*',
        r'test.*benchmark.*',
        r'test.*load.*',
        r'test.*stress.*',
        r'test.*timeout.*',
        r'test.*concurrent.*',
        r'.*_slow$',
        r'.*_performance$',
    ],

    # Integration tests - external dependencies
    'integration': [
        r'test.*integration.*',
        r'test.*api.*',
        r'test.*webhook.*',
        r'test.*twilio.*',
        r'test.*google.*',
        r'test.*redis.*',
        r'test.*database.*',
        r'test.*db.*',
        r'.*_integration$',
    ],

    # Production tests
    'production': [
        r'test.*production.*',
        r'test.*lambda.*',
        r'test.*aws.*',
        r'test.*deployment.*',
    ],

    # Unit tests - pure functions, no external deps
    'unit': [
        r'test.*_basic$',
        r'test.*_simple$',
        r'test.*extract.*',
        r'test.*parse.*',
        r'test.*format.*',
        r'test.*validation.*',
    ]
}

def categorize_test_function(func_name, file_path):
    """Determine appropriate markers for a test function."""
    markers = set()
    func_lower = func_name.lower()
    file_lower = str(file_path).lower()

    # Check each marker rule
    for marker, patterns in MARKER_RULES.items():
        for pattern in patterns:
            if re.search(pattern, func_lower) or re.search(pattern, file_lower):
                markers.add(marker)

    # Default categorization based on file location
    if 'production' in file_lower:
        markers.add('production')
    elif 'integration' in file_lower:
        markers.add('integration')
    elif 'performance' in file_lower:
        markers.add('slow')
        markers.add('performance')
    else:
        # Default to unit test if not otherwise categorized
        if not markers or markers == {'essential'}:
            markers.add('unit')

    # Ensure every test has at least one speed marker
    speed_markers = {'smoke', 'essential', 'slow'}
    if not markers.intersection(speed_markers):
        # Default to essential for uncategorized tests
        markers.add('essential')

    return sorted(markers)

def process_test_file(file_path):
    """Add markers to test functions in a file."""
    print(f"Processing {file_path}")

    with open(file_path, 'r') as f:
        content = f.read()

    lines = content.split('\n')
    modified = False
    new_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for test function definitions
        test_match = re.match(r'^(\s*)(def test_\w+.*|async def test_\w+.*)', line)

        if test_match:
            indent = test_match.group(1)
            func_def = test_match.group(2)
            func_name = re.search(r'def (test_\w+)', func_def).group(1)

            # Check if markers already exist in the lines above
            has_markers = False
            look_back = min(5, i)  # Look at most 5 lines back
            for j in range(i - look_back, i):
                if j >= 0 and '@pytest.mark.' in lines[j]:
                    has_markers = True
                    break

            if not has_markers:
                # Determine appropriate markers
                markers = categorize_test_function(func_name, file_path)

                # Add marker decorators
                for marker in markers:
                    new_lines.append(f"{indent}@pytest.mark.{marker}")
                    modified = True

                print(f"  Added markers to {func_name}: {', '.join(markers)}")

        new_lines.append(line)
        i += 1

    if modified:
        # Write back to file
        with open(file_path, 'w') as f:
            f.write('\n'.join(new_lines))
        print(f"  ✅ Updated {file_path}")
    else:
        print(f"  ⏭️  No changes needed for {file_path}")

def main():
    """Process all test files in the tests directory."""
    tests_dir = Path(__file__).parent.parent / 'tests'

    if not tests_dir.exists():
        print("Tests directory not found!")
        return 1

    # Find all test files
    test_files = []
    for pattern in ['test_*.py', '*_test.py']:
        test_files.extend(tests_dir.rglob(pattern))

    print(f"Found {len(test_files)} test files")

    for test_file in sorted(test_files):
        try:
            process_test_file(test_file)
        except Exception as e:
            print(f"❌ Error processing {test_file}: {e}")

    print("\n🎉 Test marker addition complete!")
    print("\nAvailable markers:")
    for marker, patterns in MARKER_RULES.items():
        print(f"  @pytest.mark.{marker}")

    print("\nUsage examples:")
    print("  pytest -m smoke              # Run only smoke tests")
    print("  pytest -m 'essential or smoke'  # Run quick tests")
    print("  pytest -m 'not slow'         # Skip slow tests")
    print("  pytest -m production         # Run production tests only")

if __name__ == '__main__':
    sys.exit(main())