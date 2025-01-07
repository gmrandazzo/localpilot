import rumps
import requests
import threading
from pathlib import Path
import sys
import config
import subprocess
import tqdm

def download_file(url: str, filename: str):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)

def setup():
    model_folder = Path(config.model_folder)
    if not model_folder.exists():
        if input(f"Model folder {model_folder} does not exist. Create it? (y/n) ").lower() == 'y':
            model_folder.mkdir(parents=True, exist_ok=True)
    
    for model in config.models:
        if model == 'default':
            continue
        if config.models[model]['type'] == 'local':
            model_file = model_folder / config.models[model]['filename']
            if not model_file.exists():
                if input(f'Model {model} not found in {model_folder}. Would you like to download it? (y/n) ').lower() == 'y':
                    url = config.models[model]['url']
                    print(f"Downloading {model} from {url}...")
                    download_file(url, str(model_file))
            else:
                print(f"Model {model} found in {model_folder}.")


class ModelPickerApp(rumps.App):
    def __init__(self):
        super(ModelPickerApp, self).__init__("ModelPickerApp")

        # Dynamically create menu items from the MENUBAR_OPTIONS
        self.menu_items = {}
        for option in config.models:
            if option == 'default':
                continue
            self.menu_items[option] = rumps.MenuItem(
                title=option, callback=self.pick_model)

        self.menu = list(self.menu_items.values())
        self.menu_items[config.models['default']].state = True
        self.icon = str(Path(__file__).parent / "icon.png")

    def pick_model(self, sender):
        # Toggle the checked status of the clicked menu item
        sender.state = not sender.state

        # Send the choice to the local proxy app
        if sender.state:
            choice = sender.title
            try:
                response = requests.post(
                    "http://localhost:5001/set_target", json={"target": choice})
                if response.status_code == 200:
                    print(f"Successfully sent selection: {choice}.")
                else:
                    rumps.alert(
                        "Error", f"Failed to send selection. Server responded with: {response.status_code}.")
            except requests.RequestException as e:
                rumps.alert("Error", f"Failed to send selection. Error: {e}.")

        # If other options were previously selected, deselect them
        for item in self.menu:
            if item == 'Quit':
                continue
            if item != sender.title:
                self.menu_items[item].state = False

    def run_server(self):
        subprocess.run(['python', 'proxy.py'])

if __name__ == '__main__':
    if '--setup' in sys.argv:
        setup()
    app = ModelPickerApp()
    print("Running server...")
    server_thread = threading.Thread(target=app.run_server)
    server_thread.start()
    app.run()
