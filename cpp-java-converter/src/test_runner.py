import sys
import os
import glob
sys.path.append(os.path.dirname(__file__))
from converter import CppToJavaConverter

def run_tests():
    converter = CppToJavaConverter(mode='flexible', verbose=True)
    test_files = glob.glob('tests/*.cpp')
    
    os.makedirs('out', exist_ok=True)
    
    for cpp_file in test_files:
        try:
            print(f"----- Converting {cpp_file} -----")
            with open(cpp_file, 'r', encoding='utf-8') as f:
                cpp_code = f.read()
            
            java_code = converter.convert(cpp_code, cpp_file)
            
            base_name = os.path.basename(cpp_file).replace('.cpp', '')
            out_path = os.path.join('out', f"{base_name}.java")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(java_code)
                
            print(f"SUCCESS: {cpp_file} -> {out_path}")
            if converter.errors:
                print("ERRORS:", converter.errors)
        except Exception as e:
            print(f"FAILED: {cpp_file} with error: {e}")

if __name__ == '__main__':
    run_tests()
