"""
Streamlit web interface for the C++ to Java source code converter
"""
import streamlit as st
from converter import CppToJavaConverter

def main():
    st.set_page_config(
        page_title="C++ to Java Converter",
        page_icon="🔄",
        layout="wide"
    )
    
    st.title("🔄 C++ to Java Source Code Converter")
    st.markdown("""
    This tool converts C++ source code to Java source code. 
    It handles basic type conversions, variable declarations, and class structures.
    """)
    
    # Initialize session state
    if 'converted_code' not in st.session_state:
        st.session_state.converted_code = ""
    
    # Create tabs for input and examples
    tab1, tab2 = st.tabs(["📝 Input Code", "📚 Examples"])
    
    with tab1:
        # Text area for C++ code input
        cpp_input = st.text_area(
            "Enter your C++ code:",
            height=300,
            placeholder="Paste your C++ code here...",
            key="cpp_input"
        )
        
        # Conversion button
        col1, col2 = st.columns([1, 3])
        with col1:
            convert_clicked = st.button("🔄 Convert to Java", type="primary")
        
        with col2:
            st.caption("Note: This converter handles basic C++ constructs. Complex features like templates, operator overloading, and advanced OOP concepts may not be fully supported.")
    
    with tab2:
        st.subheader("Sample C++ Code")
        example_code = """// Basic variable declarations
int a;
char b = a + a;
short c;
int d;
long e;
long long f;

// Arrays
char aarr[20];
long barr[10][20];

// Simple class
class foo {
public:
    int x;
    float y;
};
"""
        st.code(example_code, language="cpp")
        if st.button("Load Example"):
            st.session_state.cpp_input = example_code
            st.rerun()
    
    # Perform conversion when button is clicked
    if convert_clicked and cpp_input.strip():
        try:
            converter = CppToJavaConverter()
            java_output = converter.convert(cpp_input)
            st.session_state.converted_code = java_output
            
            st.success("✅ Conversion successful!")
        except Exception as e:
            st.error(f"❌ Error during conversion: {str(e)}")
            st.session_state.converted_code = ""
    
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
    
    # Add information about the tool
    with st.expander("ℹ️ About this tool"):
        st.markdown("""
        ### Features:
        - Basic type conversion (int, char, float, etc.)
        - Variable declarations with initialization
        - Array declarations
        - Simple class structures
        - Pointer and reference handling
        
        ### Limitations:
        - No support for templates
        - Limited operator overloading support
        - No exception handling conversion
        - STL containers not converted
        
        This tool provides a foundation that can be extended with more sophisticated parsing capabilities.
        """)

if __name__ == "__main__":
    main()