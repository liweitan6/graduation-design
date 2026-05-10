import zipfile
import xml.etree.ElementTree as ET

try:
    with zipfile.ZipFile('中期报告.docx') as docx:
        xml_content = docx.read('word/document.xml')
        
    tree = ET.XML(xml_content)
    namespace = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    text_nodes = []
    for node in tree.iter(f'{namespace}t'):
        if node.text:
            text_nodes.append(node.text)
            
    with open('中期报告_text.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(text_nodes))
        
    print("Success")
except Exception as e:
    print(f"Error: {e}")
