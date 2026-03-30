import urllib.request
import xml.etree.ElementTree as ET

url = "https://careerguidance.me/sitemap.xml"
try:
    response = urllib.request.urlopen(url)
    xml_data = response.read()
    root = ET.fromstring(xml_data)
    print("Sitemap XML is perfectly valid!")
    print(f"Total URLs: {len(root)}")
except ET.ParseError as e:
    print(f"XML Parsing Error: {e}")
except Exception as e:
    print(f"Other Error: {e}")
