#!/usr/bin/env python3
"""
Command-line interface for C++ to Java source code converter
Complies with requirements: FU_001-FU_007, UF_001-UF_007, SM_001-SM_003
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

from converter import CppToJavaConverter


def setup_logging(verbose: bool):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_input_files(input_paths: List[str]) -> List[Path]:
    """Validate input files exist and have valid extensions"""
    valid_extensions = {'.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx'}
    validated_paths = []
    
    for path_str in input_paths:
        path = Path(path_str)
        
        if not path.exists():
            print(f"Error: Input file does not exist: {path_str}", file=sys.stderr)
            continue
            
        if path.suffix.lower() not in valid_extensions:
            print(f"Warning: File extension '{path.suffix}' may not be a C++ file: {path_str}")
            
        validated_paths.append(path)
    
    return validated_paths


def write_report(report_data: Dict[str, Any], report_path: str, format_type: str = "json"):
    """Write translation report to file"""
    path = Path(report_path)
    
    if format_type.lower() == "json":
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
    else:  # txt format
        with open(path, 'w', encoding='utf-8') as f:
            f.write("C++ to Java Translation Report\n")
            f.write("=" * 40 + "\n\n")
            
            f.write(f"Translation Time: {report_data.get('translation_time', 'N/A')} seconds\n")
            f.write(f"Files Processed: {len(report_data.get('files_processed', []))}\n")
            f.write(f"Total AST Nodes: {report_data.get('total_ast_nodes', 0)}\n")
            f.write(f"Warnings: {len(report_data.get('warnings', []))}\n")
            f.write(f"Errors: {len(report_data.get('errors', []))}\n\n")
            
            if report_data.get('files_processed'):
                f.write("Processed Files:\n")
                for file_info in report_data['files_processed']:
                    f.write(f"  - {file_info['original_path']} -> {file_info['output_path']}\n")
            
            if report_data.get('warnings'):
                f.write("\nWarnings:\n")
                for warning in report_data['warnings']:
                    f.write(f"  - {warning}\n")
            
            if report_data.get('errors'):
                f.write("\nErrors:\n")
                for error in report_data['errors']:
                    f.write(f"  - {error}\n")


def main():
    parser = argparse.ArgumentParser(
        description="C++ to Java Source Code Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input src/main.cpp --output translated/
  %(prog)s --input src/ --output out/ --mode flexible --report report.json
  %(prog)s --input file1.cpp file2.h --output out/ --verbose
        """
    )
    
    parser.add_argument(
        "--input", 
        "-i", 
        nargs="+", 
        required=True,
        help="Input C++ file(s) or directory(ies) to convert"
    )
    
    parser.add_argument(
        "--output", 
        "-o", 
        required=True,
        help="Output directory for generated Java files"
    )
    
    parser.add_argument(
        "--mode", 
        choices=["strict", "flexible"], 
        default="strict",
        help="Conversion mode: strict (stop on unsupported constructs) or flexible (generate stubs)"
    )
    
    parser.add_argument(
        "--report", 
        help="Generate translation report to specified file (JSON or TXT)"
    )
    
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--help", 
        "-h", 
        action="help",
        help="Show this help message and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting C++ to Java conversion...")
    logger.debug(f"Arguments: {args}")
    
    # Validate inputs
    input_paths = []
    for input_arg in args.input:
        input_path = Path(input_arg)
        if input_path.is_file():
            input_paths.append(input_path)
        elif input_path.is_dir():
            # Recursively find C++ files in directory
            cpp_extensions = {'.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx'}
            for ext in cpp_extensions:
                input_paths.extend(input_path.rglob(f"*{ext}"))
        else:
            print(f"Error: Invalid input path: {input_arg}", file=sys.stderr)
            return 1
    
    if not input_paths:
        print("Error: No valid input files found", file=sys.stderr)
        return 1
    
    logger.info(f"Found {len(input_paths)} input file(s)")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize converter
    converter = CppToJavaConverter(mode=args.mode, verbose=args.verbose)
    
    # Prepare report data
    report_data = {
        "start_time": time.time(),
        "files_processed": [],
        "total_ast_nodes": 0,
        "warnings": [],
        "errors": [],
        "conversion_mode": args.mode
    }
    
    success_count = 0
    failure_count = 0
    
    # Process each file
    for cpp_file in input_paths:
        try:
            logger.info(f"Processing: {cpp_file}")
            
            start_time = time.time()
            
            # Read C++ source
            with open(cpp_file, 'r', encoding='utf-8') as f:
                cpp_source = f.read()
            
            # Convert to Java
            java_result = converter.convert(cpp_source, cpp_file)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Determine output path
            relative_path = cpp_file.relative_to(cpp_file.parent)  # Simplified - in real impl should preserve dir structure
            output_file = output_dir / f"{cpp_file.stem}.java"
            
            # Write Java file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(java_result)
            
            # Add to report
            file_info = {
                "original_path": str(cpp_file),
                "output_path": str(output_file),
                "processing_time": processing_time,
                "size_original": len(cpp_source),
                "size_translated": len(java_result),
                "ast_nodes_processed": getattr(converter, 'last_conversion_stats', {}).get('ast_nodes', 0)
            }
            
            report_data["files_processed"].append(file_info)
            report_data["total_ast_nodes"] += file_info["ast_nodes_processed"]
            
            success_count += 1
            logger.info(f"Successfully converted: {cpp_file} -> {output_file}")
            
        except Exception as e:
            error_msg = f"Failed to convert {cpp_file}: {str(e)}"
            logger.error(error_msg)
            report_data["errors"].append(error_msg)
            failure_count += 1
            
            if args.mode == "strict":
                print(f"Error in strict mode: {error_msg}", file=sys.stderr)
                return 1
    
    # Complete report
    report_data["end_time"] = time.time()
    report_data["translation_time"] = report_data["end_time"] - report_data["start_time"]
    report_data["success_count"] = success_count
    report_data["failure_count"] = failure_count
    report_data["warnings"] = list(set(report_data["warnings"]))  # Remove duplicates
    report_data["errors"] = list(set(report_data["errors"]))
    
    # Write report if requested
    if args.report:
        report_format = "json" if args.report.endswith('.json') else "txt"
        write_report(report_data, args.report, report_format)
        logger.info(f"Report written to: {args.report}")
    
    # Print summary
    print(f"\nConversion Summary:")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")
    print(f"  Total time: {report_data['translation_time']:.2f}s")
    print(f"  Total AST nodes processed: {report_data['total_ast_nodes']}")
    
    if report_data["warnings"]:
        print(f"  Warnings: {len(report_data['warnings'])}")
    
    if report_data["errors"]:
        print(f"  Errors: {len(report_data['errors'])}")
    
    return 0 if failure_count == 0 or args.mode == "flexible" else 1


if __name__ == "__main__":
    sys.exit(main())