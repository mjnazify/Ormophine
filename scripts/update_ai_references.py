#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to aggregate Ormophine source code and docstrings into unified,
clean AI Reference files for SQLite, MySQL, and PostgreSQL.

Features:
- Completely avoids import duplication across runs (Idempotent).
- Gathers, deduplicates, and sorts external & standard-library imports at the top.
- Strips intra-package relative imports (e.g. `from . import ...`).
- Preserves 100% of class definitions, method docstrings, and logic.
- Adds clean module divider banners for AI readability.
"""

import ast
from collections import defaultdict
from pathlib import Path

# Paths to the AI reference files relative to the project root
MODULES = {
    'Sqlite': 'Ormophine/Sqlite.AI.Refrence.txt',
    'Mysql': 'Ormophine/MySQL.AI.Refrence.txt',
    'Postgresql': 'Ormophine/PostgreSQL.AI.Refrence.txt'
}

# Logical order of files when combining
FILE_ORDER = [
    'setpragma.py',
    'tablestructure.py',
    'columnsoperation.py',
    'builtins.py',
    'join.py',
    'table.py',
    'driver.py'
]


def get_prompt_header(module_name: str) -> str:
    """Generate the standardized AI instruction docstring."""
    db_name = (
        'SQLite' if module_name.lower() == 'sqlite'
        else ('MySQL' if module_name.lower() == 'mysql' else 'PostgreSQL')
    )
    return (
        f'"""You are an expert assistant specialized in the Ormophine {db_name} Python ORM.\n'
        f'The text below this line is the COMPLETE source code of the Ormophine {db_name} ORM library.\n'
        f'Your sole reference for answering any question is this code.\n'
        f'When a user asks about usage, errors, features, or implementation details, analyze the code and provide accurate, clear answers.\n'
        f'Include relevant code snippets and explain how they relate to the user\'s question.\n'
        f'Do not mention that you are an AI; simply respond as a knowledgeable human expert.\n'
        f'Be concise, helpful, and practical."""'
    )


def build_module_reference(module_name: str, base_dir: Path) -> str:
    """Read, deduplicate imports, and combine all python files of a module."""
    module_path = base_dir / 'Ormophine' / module_name
    core_path = module_path / 'Core'

    # 1. Determine list of files to combine in logical order
    files_to_read = []
    for filename in FILE_ORDER:
        if filename == 'driver.py':
            f_path = module_path / 'driver.py'
        else:
            f_path = core_path / filename

        if f_path.exists():
            files_to_read.append(f_path)

    # Add any remaining python files in Core (if any)
    if core_path.exists():
        for extra_file in sorted(core_path.glob('*.py')):
            if not extra_file.name.startswith('_') and extra_file not in files_to_read:
                files_to_read.append(extra_file)

    future_imports = set()
    direct_imports = set()
    from_imports = defaultdict(set)
    file_bodies = []

    # 2. Parse each file, extract imports, and clean the body
    for file_path in files_to_read:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)
        top_level_import_nodes = []

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                top_level_import_nodes.append(node)

                if isinstance(node, ast.Import):
                    for n in node.names:
                        alias = f' as {n.asname}' if n.asname else ''
                        direct_imports.add(f'{n.name}{alias}')

                elif isinstance(node, ast.ImportFrom):
                    # Skip relative imports (e.g. `from . import ...`, `from .. import ...`)
                    if node.level > 0:
                        continue

                    if node.module == '__future__':
                        for n in node.names:
                            future_imports.add(n.name)
                    else:
                        for n in node.names:
                            alias = f' as {n.asname}' if n.asname else ''
                            from_imports[node.module].add(f'{n.name}{alias}')

        # Strip top-level import lines from the source file
        lines = content.splitlines()
        skip_ranges = [(n.lineno - 1, n.end_lineno) for n in top_level_import_nodes]

        cleaned_lines = []
        i = 0
        while i < len(lines):
            if any(start <= i < end for start, end in skip_ranges):
                pass
            else:
                cleaned_lines.append(lines[i])
            i += 1

        body = '\n'.join(cleaned_lines).strip()
        divider = f'# {"=" * 70}\n# Module: {file_path.name}\n# {"=" * 70}'
        file_bodies.append(f'{divider}\n\n{body}')

    # 3. Assemble unified top-level imports
    all_imports = []
    if future_imports:
        all_imports.append(f'from __future__ import {", ".join(sorted(future_imports))}')
        all_imports.append('')

    for direct_imp in sorted(direct_imports):
        all_imports.append(f'import {direct_imp}')

    for mod in sorted(from_imports.keys()):
        names = sorted(from_imports[mod])
        all_imports.append(f'from {mod} import {", ".join(names)}')

    imports_section = '\n'.join(all_imports).strip()
    prompt = get_prompt_header(module_name)

    # 4. Final document assembly
    full_output = f'{prompt}\n\n\n{imports_section}\n\n\n' + '\n\n\n'.join(file_bodies) + '\n'
    return full_output


def update_ai_reference_file(module_name: str, target_rel_path: str, base_dir: Path):
    target_path = base_dir / target_rel_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    content = build_module_reference(module_name, base_dir)

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    base_dir = Path(__file__).resolve().parent.parent if Path(__file__).parent.name == 'scripts' else Path('.')
    # Fallback to current working directory if Ormophine directory is present
    if not (base_dir / 'Ormophine').exists() and Path('Ormophine').exists():
        base_dir = Path('.')

    for module_name, rel_path in MODULES.items():
        print(f"Aggregating {rel_path} for module {module_name}...")
        update_ai_reference_file(module_name, rel_path, base_dir)
        print(f"Successfully generated clean reference: {rel_path}")


if __name__ == '__main__':
    main()