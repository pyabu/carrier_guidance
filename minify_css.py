import re
import sys
import os

def minify_css(input_file, output_file):
    print(f"Minifying {input_file} -> {output_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            css = f.read()

        # Remove CSS comments
        css = re.sub(r'/\*[\s\S]*?\*/', '', css)
        
        # Remove whitespace around structural characters
        css = re.sub(r'\s*([\{\}\:\;\,\>])\s*', r'\1', css)
        
        # Remove newlines and tabs
        css = re.sub(r'[\r\n\t]+', '', css)
        
        # Remove trailing semicolons inside blocks
        css = re.sub(r';}', '}', css)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(css)
            
        original_size = os.path.getsize(input_file)
        new_size = os.path.getsize(output_file)
        savings = (original_size - new_size) / original_size * 100
        
        print(f"Success! Reduced size by {savings:.1f}%")
        print(f"Original: {original_size/1024:.1f} KB")
        print(f"Minified: {new_size/1024:.1f} KB")
        
    except Exception as e:
        print(f"Error minifying CSS: {e}")
        sys.exit(1)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "static", "css", "style.css")
    output_path = os.path.join(base_dir, "static", "css", "style.min.css")
    minify_css(input_path, output_path)
