
#!/usr/bin/env python3
"""Fix all flake8 lint errors in DataTrust source files."""

import os
import re

fixes_applied = 0

def fix_file(filepath):
    global fixes_applied
    if not os.path.exists(filepath):
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Fix F541: f-strings without placeholders
    # Match f"..." or f'...' that don't contain { }
    def fix_fstring(match):
        global fixes_applied
        quote = match.group(1)
        text = match.group(2)
        if "{" not in text:
            fixes_applied += 1
            return f"{quote}{text}{quote}"
        return match.group(0)

    content = re.sub(r'f(")((?:[^"\\]|\\.)*)"', fix_fstring, content)
    content = re.sub(r"f(')((?:[^'\\]|\\.)*)'", fix_fstring, content)

    # Fix W391: Remove trailing blank lines at end of file
    while content.endswith("\n\n"):
        content = content[:-1]
        fixes_applied += 1

    if not content.endswith("\n"):
        content += "\n"

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Fixed: {filepath}")


def fix_unused_critical(filepath):
    """Fix F841: Remove unused 'critical' variable assignments."""
    global fixes_applied
    if not os.path.exists(filepath):
        return

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        # Remove lines like: critical = something (if variable is never used)
        if re.match(r'^critical\s*=\s*', stripped) and 'critical' not in ''.join(lines).replace(stripped, '', 1).replace('# critical', ''):
            # Check if critical is used elsewhere
            all_text = ''.join(lines)
            # Count occurrences of 'critical' as a variable (not in strings/comments)
            uses = len(re.findall(r'\bcritical\b', all_text))
            if uses <= 2:  # Only assignment and maybe one other mention
                new_lines.append(line.replace('critical = ', '_ = '))
                fixes_applied += 1
                continue
        new_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


print("=" * 60)
print("  Fixing lint errors...")
print("=" * 60)

# Walk through all Python files
for root, dirs, files in os.walk("src"):
    for fname in files:
        if fname.endswith(".py"):
            fix_file(os.path.join(root, fname))

for root, dirs, files in os.walk("tests"):
    for fname in files:
        if fname.endswith(".py"):
            fix_file(os.path.join(root, fname))

for root, dirs, files in os.walk("lambda"):
    for fname in files:
        if fname.endswith(".py"):
            fix_file(os.path.join(root, fname))

fix_file("datatrust.py")

# Fix the specific unused variable issue
for root, dirs, files in os.walk("src"):
    for fname in files:
        if fname.endswith(".py"):
            fix_unused_critical(os.path.join(root, fname))

print(f"\n  Total fixes applied: {fixes_applied}")
print()
print("  Now run:")
print('    git add .')
print('    git commit -m "Fix lint errors"')
print("    git push")
print()

