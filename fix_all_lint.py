
#!/usr/bin/env python3
"""
Fix ALL flake8 errors: F541, F841, W391, W504
Run from DataTrust project root.
"""

import os
import re

total_fixes = 0


def find_python_files():
    """Find all Python files in src/, tests/, lambda/ and root."""
    files = []
    for folder in ["src", "tests", "lambda"]:
        for root, dirs, fnames in os.walk(folder):
            # Skip __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in fnames:
                if fname.endswith(".py"):
                    files.append(os.path.join(root, fname))
    if os.path.exists("datatrust.py"):
        files.append("datatrust.py")
    return files


def fix_f541(content, filepath):
    """Fix F541: f-string without placeholders — remove the f prefix."""
    global total_fixes
    fixed = content

    def replace_double(match):
        global total_fixes
        prefix = match.group(1)  # f or F
        text = match.group(2)
        if "{" not in text:
            total_fixes += 1
            return f'"{text}"'
        return match.group(0)

    def replace_single(match):
        global total_fixes
        prefix = match.group(1)
        text = match.group(2)
        if "{" not in text:
            total_fixes += 1
            return f"'{text}'"
        return match.group(0)

    # Match f"..." without { inside
    fixed = re.sub(r'[fF]("(?:[^"\\]|\\.)*")', lambda m: m.group(1) if "{" not in m.group(1) else m.group(0), fixed)
    diff1 = content.count('f"') + content.count("f'") - fixed.count('f"') - fixed.count("f'")

    # Match f'...' without { inside
    fixed = re.sub(r"[fF]('(?:[^'\\]|\\.)*')", lambda m: m.group(1) if "{" not in m.group(1) else m.group(0), fixed)
    diff2 = content.count('f"') + content.count("f'") - fixed.count('f"') - fixed.count("f'")

    total_fixes += max(diff1, 0) + max(diff2 - diff1, 0)
    return fixed


def fix_f841(content, filepath):
    """Fix F841: unused variable 'critical' — prefix with underscore."""
    global total_fixes
    lines = content.split("\n")
    new_lines = []

    # Find all variable assignments and check if they're used elsewhere
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for 'critical = ...' pattern
        match = re.match(r'^(\s*)(critical)\s*=\s*(.+)$', line)
        if match:
            indent = match.group(1)
            var_name = match.group(2)
            value = match.group(3)

            # Check if 'critical' is used elsewhere (not just this assignment)
            other_lines = "\n".join(lines[:i] + lines[i+1:])
            # Look for usage as variable (not in strings or comments)
            uses = len(re.findall(r'\bcritical\b', other_lines))
            if uses == 0:
                new_lines.append(f"{indent}_ = {value}")
                total_fixes += 1
                continue

        # Also catch 'high = ...' if unused
        match = re.match(r'^(\s*)(high)\s*=\s*(.+)$', line)
        if match:
            indent = match.group(1)
            var_name = match.group(2)
            value = match.group(3)

            other_lines = "\n".join(lines[:i] + lines[i+1:])
            uses = len(re.findall(r'\bhigh\b', other_lines))
            if uses == 0:
                new_lines.append(f"{indent}_ = {value}")
                total_fixes += 1
                continue

        new_lines.append(line)

    return "\n".join(new_lines)


def fix_w391(content, filepath):
    """Fix W391: blank line at end of file."""
    global total_fixes
    original = content

    # Remove trailing blank lines, keep exactly one newline at end
    content = content.rstrip("\n\r ") + "\n"

    if content != original:
        total_fixes += 1

    return content


def fix_w504(content, filepath):
    """Fix W504: line break after binary operator."""
    global total_fixes
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # Check if line ends with a binary operator
        if i + 1 < len(lines) and re.search(r'[\+\-\*\/\&\|]\s*$', stripped):
            # Get the operator
            match = re.search(r'([\+\-\*\/\&\|])\s*$', stripped)
            if match:
                operator = match.group(1)
                # Remove operator from end of this line
                fixed_line = stripped[:match.start()].rstrip()
                # Add operator to start of next line
                next_line = lines[i + 1]
                next_indent = len(next_line) - len(next_line.lstrip())
                next_content = next_line.lstrip()
                fixed_next = " " * next_indent + operator + " " + next_content

                new_lines.append(fixed_line)
                new_lines.append(fixed_next)
                total_fixes += 1
                i += 2
                continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


print("=" * 60)
print("  Scanning and fixing all lint errors...")
print("=" * 60)
print()

files = find_python_files()
print(f"  Found {len(files)} Python files")
print()

for filepath in files:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        continue

    original = content
    before = total_fixes

    content = fix_f541(content, filepath)
    content = fix_f841(content, filepath)
    content = fix_w504(content, filepath)
    content = fix_w391(content, filepath)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        fixes_in_file = total_fixes - before
        print(f"  Fixed {fixes_in_file} issue(s) in: {filepath}")

print()
print("=" * 60)
print(f"  Total fixes applied: {total_fixes}")
print("=" * 60)
print()
print("  Verify locally:")
print("    flake8 src/ tests/ datatrust.py --max-line-length=120 --ignore=E501,W503 --statistics")
print()
print("  Then push:")
print("    git add .")
print('    git commit -m "Fix all flake8 lint errors"')
print("    git push")
print()

