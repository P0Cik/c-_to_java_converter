import re

def debug_parse():
    line = "char aarr[20];"
    print(f"Original line: {line}")
    
    line = line.rstrip(';')
    print(f"After removing semicolon: {line}")
    
    parts = line.split()
    print(f"Parts: {parts}")
    
    # Identify the type by looking for the type keyword and any modifiers
    type_parts = []
    var_part_idx = 0
    
    # Look for common type patterns
    for i, part in enumerate(parts):
        print(f"Checking part {i}: '{part}'")
        if part in ['int', 'long', 'short', 'char', 'wchar_t', 'bool', 'float', 'double', 'void', 
                   'unsigned', 'signed']:
            # Gather all type-related parts (including modifiers like unsigned, long long, etc.)
            j = i
            while j < len(parts) and parts[j] in ['int', 'long', 'short', 'char', 'wchar_t', 'bool', 
                                                 'float', 'double', 'void', 'unsigned', 'signed']:
                type_parts.append(parts[j])
                j += 1
            var_part_idx = j
            print(f"Found type at index {i}, gathered parts {type_parts}, var_part_idx={var_part_idx}")
            break
        elif '*' in part or '&' in part:
            # Handle pointer/reference types
            if i > 0:
                type_parts.append(parts[i-1])
            type_parts.append(part)
            var_part_idx = i + 1
            print(f"Found pointer/reference at index {i}, type_parts={type_parts}, var_part_idx={var_part_idx}")
            break
        elif i == len(parts) - 1:
            # Last resort: assume first part is type
            type_parts = [parts[0]]
            var_part_idx = 1
            print(f"Last resort, type_parts={type_parts}, var_part_idx={var_part_idx}")

    cpp_type = ' '.join(type_parts).strip()
    print(f"C++ type: '{cpp_type}'")
    
    # Extract variable names (everything after the type)
    var_defs = ' '.join(parts[var_part_idx:]).split(',')
    print(f"Variable definitions: {var_defs}")
    
    for var_def in var_defs:
        var_def = var_def.strip()
        print(f"Processing variable: '{var_def}'")
        
        if '[' in var_def:
            # Array declaration - handle multi-dimensional arrays
            array_parts = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)((?:\[[^\]]*\])+)', var_def)
            print(f"Array regex match result: {array_parts}")
            if array_parts:
                base_name = array_parts.group(1)
                dimensions = array_parts.group(2)  # This captures all bracket parts like [10][20]
                print(f"Matched array - base: '{base_name}', dimensions: '{dimensions}'")
            else:
                base_name = re.sub(r'\[.*\]', '', var_def).strip()
                print(f"No match, fallback - base: '{base_name}'")

debug_parse()