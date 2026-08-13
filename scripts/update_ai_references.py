#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

MODULES = {
    'Sqlite': 'Ormophine/Sqlite.AI.Refrence.txt',
    'Mysql': 'Ormophine/MySQL.AI.Refrence.txt',
    'Postgresql': 'Ormophine/PostgreSQL.AI.Refrence.txt'
}

def get_prompt_and_code(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.splitlines(keepends=True)
    prompt_lines = []
    for line in lines:
        if line.startswith('class Driver'):
            break
        prompt_lines.append(line)
    
    prompt = ''.join(prompt_lines)
    return prompt

def get_python_files(module_name):
    module_path = Path('Ormophine') / module_name
    files_content = []
    
    driver_path = module_path / 'driver.py'
    if driver_path.exists():
        with open(driver_path, 'r', encoding='utf-8') as f:
            files_content.append(f.read())
    
    core_path = module_path / 'Core'
    if core_path.exists():
        core_files = sorted(core_path.glob('*.py'))
        for file in core_files:
            if file.name.startswith('__') or file.name.startswith('_'):
                continue
            with open(file, 'r', encoding='utf-8') as f:
                files_content.append(f.read())
    
    combined_code = '\n\n'.join(files_content)
    return combined_code

def update_ai_reference_file(module_name, ai_ref_path):
    prompt = get_prompt_and_code(ai_ref_path)
    new_code = get_python_files(module_name)
    
    with open(ai_ref_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
        f.write('\n\n')  
        f.write(new_code)

def main():
    for module_name, ai_ref_path in MODULES.items():
        print(f"Updating {ai_ref_path} for module {module_name}...")
        update_ai_reference_file(module_name, ai_ref_path)
        print(f"Done updating {ai_ref_path}.")

if __name__ == '__main__':
    main()