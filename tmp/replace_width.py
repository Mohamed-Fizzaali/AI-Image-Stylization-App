import os

files = [
    r"c:\Infosis\AI Image and Cartoonization\frontend\app.py",
    r"c:\Infosis\AI Image and Cartoonization\frontend\pages\dashboard.py"
]

for f in files:
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
        
        content = content.replace("use_container_width=True", "width=\"stretch\"")
        content = content.replace("use_container_width=False", "width=\"content\"")
        
        with open(f, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Updated {f}")
    else:
        print(f"File not found: {f}")
