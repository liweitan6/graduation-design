import re
try:
    with open("template_extracted/word/document.xml", "r", encoding="utf-8") as f:
        content = f.read()
    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", content)
    with open("template_text.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(texts))
    print("Extracted successfully")
except Exception as e:
    print(e)
