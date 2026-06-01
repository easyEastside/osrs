import time
import random
import pyautogui
import numpy as np

# Adjust pyautogui delays to be instantaneous by default so we control them manually
pyautogui.PAUSE = 0.001
pyautogui.FAILSAFE = True  # Move mouse to any corner to abort execution

def wind_mouse(start_x, start_y, target_x, target_y, G_0=9.0, W_0=3.0, M_0=15.0, D_0=12.0):
    """
    Generates a list of coordinates representing a human-like mouse movement path
    from (start_x, start_y) to (target_x, target_y) using the WindMouse algorithm.
    
    G_0 (Gravity): Pull force towards target. High values make the cursor move straighter.
    W_0 (Wind): Random force. High values make the cursor curve and sway more.
    M_0 (Min distance): Distance limit for calculations.
    D_0 (Deceleration distance): The distance from target at which cursor starts slowing down.
    """
    points = []
    current_x, current_y = float(start_x), float(start_y)
    vx, vy = 0.0, 0.0
    
    # Calculate initial distance
    dist = np.hypot(target_x - current_x, target_y - current_y)
    
    wind_x, wind_y = 0.0, 0.0
    
    # Define a random target precision (e.g. we stop the loop when we are very close, then snap)
    target_precision = random.uniform(1.2, 2.5)
    
    # Randomize parameters slightly for each movement to vary behavior
    G_0 = random.uniform(G_0 - 1.5, G_0 + 1.5)
    W_0 = random.uniform(W_0 - 0.8, W_0 + 0.8)
    
    # Keep track of iteration count to prevent infinite loop
    max_iterations = 2000
    iterations = 0
    
    while dist > target_precision and iterations < max_iterations:
        iterations += 1
        
        # Wind vector changes randomly but retains some momentum
        wind_x = wind_x / 1.5 + (random.random() * 2 - 1) * W_0 / 2.0
        wind_y = wind_y / 1.5 + (random.random() * 2 - 1) * W_0 / 2.0
        
        # Calculate forces
        vx += wind_x + G_0 * (target_x - current_x) / (dist + 1e-5)
        vy += wind_y + G_0 * (target_y - current_y) / (dist + 1e-5)
        
        # Define speed limits
        speed = np.hypot(vx, vy)
        max_speed = random.uniform(12.0, 20.0)
        
        # Decelerate when approaching the target
        if dist < D_0:
            max_speed = random.uniform(3.0, 5.0)
            
        if speed > max_speed:
            vx = (vx / speed) * max_speed
            vy = (vy / speed) * max_speed
            
        # Update coordinates
        current_x += vx
        current_y += vy
        dist = np.hypot(target_x - current_x, target_y - current_y)
        
        points.append((int(current_x), int(current_y)))
        
    # Append the exact target at the end
    points.append((target_x, target_y))
    return points

def move_to(target_x, target_y, min_steps=10):
    """
    Moves the cursor to target_x, target_y using the wind_mouse algorithm.
    """
    start_x, start_y = pyautogui.position()
    
    # If already at target, return
    if start_x == target_x and start_y == target_y:
        return
        
    path = wind_mouse(start_x, start_y, target_x, target_y)
    
    # Smoothly move through path points
    for idx, (x, y) in enumerate(path):
        pyautogui.moveTo(x, y)
        
        # Simulate realistic mouse polls (around 125-1000Hz refresh rate)
        # Slower movement near the target
        remaining_dist = len(path) - idx
        if remaining_dist < 15:
            # Slower at the end for accuracy
            time.sleep(random.uniform(0.005, 0.012))
        else:
            time.sleep(random.uniform(0.001, 0.004))

def fast_move_to(target_x, target_y):
    """
    Moves the cursor to target coordinates at a moderate speed (~2-3 actions/sec).
    """
    start_x, start_y = pyautogui.position()
    
    if start_x == target_x and start_y == target_y:
        return
        
    path = wind_mouse(start_x, start_y, target_x, target_y, G_0=18.0, W_0=0.8, M_0=10.0, D_0=4.0)
    
    for idx, (x, y) in enumerate(path):
        pyautogui.moveTo(x, y)
        remaining_dist = len(path) - idx
        if remaining_dist < 5:
            time.sleep(random.uniform(0.008, 0.018))
        else:
            time.sleep(random.uniform(0.005, 0.015))

def click(button='left'):
    """
    Simulates a human-like mouse click.
    """
    # Small reaction delay before pressing down
    time.sleep(random.uniform(0.02, 0.08))
    
    # Press down
    pyautogui.mouseDown(button=button)
    
    # Click duration (how long the mouse key is held down, typically 50ms - 150ms for humans)
    time.sleep(random.uniform(0.06, 0.14))
    
    # Release
    pyautogui.mouseUp(button=button)
    
    # Small reaction delay after clicking
    time.sleep(random.uniform(0.05, 0.15))

def fast_click(button='left'):
    """
    Simulates a moderate-speed mouse click (~2-3 clicks per second).
    """
    time.sleep(random.uniform(0.08, 0.15))
    pyautogui.mouseDown(button=button)
    time.sleep(random.uniform(0.06, 0.12))
    pyautogui.mouseUp(button=button)
    time.sleep(random.uniform(0.08, 0.15))
