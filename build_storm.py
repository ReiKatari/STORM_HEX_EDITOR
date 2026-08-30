import os
import subprocess
import sys

def build_app(script, name, icon, hidden_imports=None, add_data=None):
    print(f"\n--- Building {name} ---")
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--icon={icon}",
        f"--name={name}",
    ]
    
    # Ensure the main icon is bundled as data so resource_path finds it
    datas = set(add_data) if add_data else set()
    datas.add(icon)
    
    for d in datas:
        cmd.append(f"--add-data={d};.")
    
    if hidden_imports:
        for imp in hidden_imports:
            cmd.append(f"--hidden-import={imp}")
    
    cmd.append(script)
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    apps = [
        {
            "script": "stormhexeditor.py",
            "name": "STORM HEX EDITOR",
            "icon": "stormhexeditor.ico"
        },
        {
            "script": "stormtilemanager.py",
            "name": "STORM TILE MANAGER",
            "icon": "stormtilemanager.ico"
        },
        {
            "script": "stormgamedictionary.py",
            "name": "STORM GAME DICTIONARY",
            "icon": "stormgamedictionary.ico"
        },
        {
            "script": "stormsuite.py",
            "name": "STORM SUITE",
            "icon": "stormsuite.ico",
            "hidden_imports": [], # Removed inter-app dependencies
            # Suite needs all icons to display buttons effectively
            "add_data": [
                "stormhexeditor.ico", 
                "stormtilemanager.ico", 
                "stormgamedictionary.ico",
                "stormsuite.ico"
            ]
        }
    ]
    
    for app in apps:
        try:
            build_app(
                app["script"], 
                app["name"], 
                app["icon"], 
                app.get("hidden_imports"),
                app.get("add_data")
            )
        except Exception as e:
            print(f"Failed to build {app['name']}: {e}")

if __name__ == "__main__":
    main()
