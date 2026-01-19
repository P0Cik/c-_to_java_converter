# C++ to Java Converter

Advanced C++ to Java source code converter that uses libclang for AST parsing and provides comprehensive transformation capabilities.

## Features

- **AST-based parsing**: Uses libclang to parse C++ code and build a complete Abstract Syntax Tree
- **Semantic preservation**: Maintains semantic meaning during conversion from C++ to Java
- **Multiple inheritance handling**: Converts C++ multiple inheritance to Java interfaces + composition
- **Template support**: Transforms C++ templates to Java generics
- **RAII emulation**: Converts C++ RAII patterns to Java AutoCloseable/Try-with-resources
- **Operator overloading**: Maps C++ operators to appropriate Java methods
- **Flexible conversion modes**: Strict mode (stops on unsupported features) or flexible mode (generates stubs)
- **Streamlit web interface**: User-friendly web interface for easy conversion
- **Detailed reporting**: Comprehensive conversion reports with statistics and diagnostics

## Requirements

- Python 3.9+
- Clang 12.0+ (for libclang)
- Linux/macOS/Windows with WSL2

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Web Interface (Recommended)

```bash
cd src
streamlit run app.py
```

The web interface provides:
- Real-time C++ to Java conversion
- Multiple conversion modes (strict/flexible)
- Code examples and templates
- Detailed conversion reports
- Downloadable Java output

### Command Line Interface

```bash
cd src
python converter.py
```

## Supported Conversions

### Classes and Inheritance
- Single inheritance: `class A : public B` → `class A extends B`
- Multiple inheritance: Converted to interfaces + composition
- Virtual/final/override: Mapped to Java equivalents

### Templates
- `template<typename T>` → `<T>`
- Partial specializations: Converted to overloaded classes with explanatory comments

### RAII
- Constructors/destructors: Emulated with AutoCloseable + try-with-resources
- Temporal objects: Mapped to try blocks

### Operators
- `operator+` → `plus(T other)`
- `operator==` → Override `equals(Object)` + `hashCode()`
- `operator[]` → `get(int i)` / `set(int i, T value)`
- `operator bool()` → `boolean isValid()` or `boolean asBoolean()`

### Namespaces
- `namespace A::B { class C; }` → `package a.b; public class C { ... }`

### Constants
- `#define N 10` → `public static final int N = 10;`
- `const` and `constexpr` → `final` and `static final`

## Architecture

The converter follows a pipeline architecture:

1. **Parser**: Uses libclang to parse C++ code into AST
2. **Validator**: Checks AST for semantic correctness
3. **Transformer**: Applies conversion rules to transform C++ AST to Java representation
4. **Generator**: Outputs Java source code from transformed AST
5. **Reporter**: Generates translation reports

## Modes

- **Strict mode**: Stops conversion when encountering unsupported C++ features
- **Flexible mode**: Generates stubs with `// TODO: manual fix required` comments

## Error Handling

The converter provides detailed diagnostic messages for:
- Unsupported C++ features (e.g., multiple inheritance, union declarations)
- Compilation errors in source code
- Semantic issues during transformation
- Complex idioms requiring manual review

## Testing

Unit tests cover individual transformation rules, and end-to-end tests compare behavior between original C++ and converted Java code.

## License

MIT License