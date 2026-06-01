# OSRS Automation Tool

Cross-platform (Windows & Linux) automation tool using computer vision and human-like mouse movements.

## Features

- Human-like mouse movement simulation (WindMouse algorithm)
- Color-based contour detection and clicking
- Automatic window focus and management
- Idle behavior simulation to avoid detection
- Cross-platform support (Windows, Linux)

## Installation

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Additional system dependencies
sudo apt-get install xdotool wmctrl scrot
```

## Usage

```python
import osrs_api

# Start and focus the RuneLite window
osrs_api.start("RuneLite")

# Click on blue contours
osrs_api.click("blue")

# Click a random green contour
osrs_api.click_random("green")

# Click all yellow contours
osrs_api.click_all("yellow")

# Wait for a red contour to appear
osrs_api.wait_for("red", timeout=30.0)


```

## Available Colors

- `blue` - [255, 0, 0] (BGR)
- `green` - [0, 255, 0]
- `magenta` - [255, 0, 255]
- `pink` - [255, 0, 255]
- `yellow` - [0, 255, 255]
- `red` - [0, 0, 255]

## API Functions

- `start(window_title)` - Initialize and focus the game window
- `click(color, index=0)` - Click on a specific contour by color
- `click_random(color)` - Click a random contour of the specified color
- `click_all(color, delay=0.3)` - Click all contours of a color
- `count(color)` - Count visible contours of a color
- `wait_for(color, timeout=30.0)` - Wait for a contour to appear
- `wait_for_disappear(color, timeout=30.0)` - Wait for contours to disappear


## Advanced Usage

```python
from osrs_api import ContourManager

manager = ContourManager("RuneLite")
manager.focus_window()

# Get contours
contours, offset = manager.get_contours_on_screen("blue")

# Click with verification
manager.click_contour(contours[0], "blue", offset)

# Custom contour detection
img, offset = manager.capture_client_area()
contours = manager.find_contours(img, "green", min_area=20)
```

## Notes

- Move your mouse to any corner to abort execution (pyautogui failsafe)
- The tool simulates natural human idle behavior during waits
- DPI awareness is automatically handled on Windows
