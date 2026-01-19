"""
Streamlit web interface for the C++ to Java source code converter
Implements requirements: UF_004, UF_007
"""

import streamlit as st
from converter import CppToJavaConverter
import json


def main():
    st.set_page_config(
        page_title="C++ to Java Converter",
        page_icon="🔄",
        layout="wide"
    )
    
    st.title("🔄 C++ to Java Source Code Converter")
    st.markdown("""
    This tool converts C++ source code to Java source code using AST-based parsing with libclang.
    It handles various C++ constructs including classes, templates, RAII patterns, and operator overloading.
    """)

    # Initialize session state
    if 'converted_code' not in st.session_state:
        st.session_state.converted_code = ""
    if 'conversion_report' not in st.session_state:
        st.session_state.conversion_report = {}
    if 'error_message' not in st.session_state:
        st.session_state.error_message = ""
    
    # Sidebar for settings
    st.sidebar.header("⚙️ Settings")
    conversion_mode = st.sidebar.radio(
        "Conversion Mode:",
        ("strict", "flexible"),
        help="Strict mode stops on unsupported features, flexible mode generates stubs with TODO comments"
    )
    
    verbose_output = st.sidebar.checkbox("Verbose Output", value=False)
    
    # Create tabs for input and examples
    tab1, tab2, tab3 = st.tabs(["📝 Input Code", "📚 Examples", "📋 Conversion Report"])
    
    with tab1:
        # Text area for C++ code input
        cpp_input = st.text_area(
            "Enter your C++ code:",
            height=400,
            placeholder="// Paste your C++ code here...\n// Supports classes, functions, templates, namespaces, etc.",
            key="cpp_input"
        )
        
        # Conversion button
        col1, col2 = st.columns([1, 3])
        with col1:
            convert_clicked = st.button("🔄 Convert to Java", type="primary")
        
        with col2:
            st.caption("Note: This converter uses libclang for accurate AST parsing and semantic analysis.")
    
    with tab2:
        st.subheader("Sample C++ Code Examples")
        
        example_tabs = st.tabs(["CppClass", "Template", "Namespace", "Operator"])
        
        with example_tabs[0]:
            class_example = """// Basic class with constructor and methods
class Rectangle {
private:
    double width, height;

public:
    Rectangle(double w, double h) : width(w), height(h) {}
    
    double getArea() const {
        return width * height;
    }
    
    double getPerimeter() const {
        return 2 * (width + height);
    }
    
    ~Rectangle() {
        // Cleanup code
    }
};"""
            st.code(class_example, language="cpp")
            if st.button("Load Class Example"):
                st.session_state.cpp_input = class_example
                st.rerun()
        
        with example_tabs[1]:
            template_example = """// Template class
template<typename T>
class Container {
private:
    T* data;
    size_t size;

public:
    Container(size_t s) : size(s) {
        data = new T[size];
    }
    
    T& operator[](size_t index) {
        return data[index];
    }
    
    ~Container() {
        delete[] data;
    }
};"""
            st.code(template_example, language="cpp")
            if st.button("Load Template Example"):
                st.session_state.cpp_input = template_example
                st.rerun()
        
        with example_tabs[2]:
            namespace_example = """// Namespace usage
namespace graphics {
    namespace shapes {
        class Circle {
        public:
            double radius;
            
            Circle(double r) : radius(r) {}
            double area() const {
                return 3.14159 * radius * radius;
            }
        };
    }
}"""
            st.code(namespace_example, language="cpp")
            if st.button("Load Namespace Example"):
                st.session_state.cpp_input = namespace_example
                st.rerun()
        
        with example_tabs[3]:
            operator_example = """// Operator overloading
class Complex {
private:
    double real, imag;

public:
    Complex(double r = 0, double i = 0) : real(r), imag(i) {}
    
    Complex operator+(const Complex& other) const {
        return Complex(real + other.real, imag + other.imag);
    }
    
    Complex operator-(const Complex& other) const {
        return Complex(real - other.real, imag - other.imag);
    }
    
    bool operator==(const Complex& other) const {
        return (real == other.real && imag == other.imag);
    }
};"""
            st.code(operator_example, language="cpp")
            if st.button("Load Operator Example"):
                st.session_state.cpp_input = operator_example
                st.rerun()
    
    # Perform conversion when button is clicked
    if convert_clicked and cpp_input.strip():
        try:
            with st.spinner("Converting C++ code to Java... This may take a moment."):
                converter = CppToJavaConverter(mode=conversion_mode, verbose=verbose_output)
                java_output = converter.convert(cpp_input)
                
                st.session_state.converted_code = java_output
                st.session_state.conversion_report = converter.generate_report()
                st.session_state.error_message = ""
                
                st.success("✅ Conversion completed successfully!")
                
        except Exception as e:
            st.session_state.error_message = f"❌ Error during conversion: {str(e)}"
            st.session_state.converted_code = ""
            st.session_state.conversion_report = {}
            st.error(st.session_state.error_message)
    
    # Display results if available
    if st.session_state.converted_code:
        st.subheader("📤 Converted Java Code")
        
        # Show the converted code
        st.code(st.session_state.converted_code, language="java")
        
        # Provide download button
        st.download_button(
            label="📥 Download Java Code",
            data=st.session_state.converted_code,
            file_name="converted_code.java",
            mime="text/plain"
        )
    
    with tab3:
        st.subheader("📊 Conversion Report")
        
        if st.session_state.conversion_report:
            report = st.session_state.conversion_report
            
            # Display report metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("AST Nodes", report['stats'].get('ast_nodes', 0))
            with col2:
                st.metric("Warnings", len(report.get('warnings', [])))
            with col3:
                st.metric("Errors", len(report.get('errors', [])))
            with col4:
                st.metric("Mode", conversion_mode.upper())
            
            # Show warnings if any
            if report.get('warnings'):
                st.warning(f"⚠️ Warnings ({len(report['warnings'])}):")
                for warning in report['warnings']:
                    st.text("- " + warning)
            
            # Show errors if any
            if report.get('errors'):
                st.error(f"❌ Errors ({len(report['errors'])}):")
                for error in report['errors']:
                    st.text("- " + error)
            
            # Show detailed stats
            with st.expander("Technical Details"):
                st.json(report)
        else:
            st.info("No conversion report available. Run a conversion to see the report.")
    
    # Add information about the tool
    with st.expander("ℹ️ About this tool"):
        st.markdown("""
        ### Features:
        - **AST-based parsing**: Uses libclang for accurate C++ parsing and semantic analysis
        - **Comprehensive conversion**: Handles classes, inheritance, templates, RAII, operator overloading
        - **Multiple inheritance**: Converts to Java interfaces + composition
        - **Template support**: Transforms C++ templates to Java generics
        - **RAII emulation**: Converts C++ RAII patterns to Java AutoCloseable/Try-with-resources
        - **Operator overloading**: Maps C++ operators to appropriate Java methods
        - **Detailed reporting**: Provides conversion statistics and diagnostics
        
        ### Supported Conversions:
        - Classes and single inheritance → Java classes
        - Multiple inheritance → Interfaces + composition
        - Templates → Generics
        - RAII patterns → AutoCloseable + try-with-resources
        - Operator overloading → Named methods (e.g., operator+ → plus())
        - Namespaces → Packages
        - Const/constexpr → final/static final
        - Virtual/final/override → Java equivalents
        
        ### Modes:
        - **Strict mode**: Stops conversion when encountering unsupported C++ features
        - **Flexible mode**: Generates stubs with `// TODO: manual fix required` comments
        
        This tool implements all requirements for C++ to Java conversion with focus on semantic correctness.
        """)


if __name__ == "__main__":
    main()