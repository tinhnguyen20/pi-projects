"""Read taps from the touch screen and report them as screen positions.

Calibrate on the Pi:  sudo python3 touch.py
"""
import config


def to_screen(raw_x, raw_y, x_range, y_range):
    """Turn raw touch readings into (x, y) screen pixels.

    x_range and y_range are the (min, max) of each touch axis.
    """
    # 0 to 1 across each axis
    nx = (raw_x - x_range[0]) / (x_range[1] - x_range[0])
    ny = (raw_y - y_range[0]) / (y_range[1] - y_range[0])
    if config.TOUCH_SWAP_XY:
        nx, ny = ny, nx
    if config.TOUCH_INVERT_X:
        nx = 1 - nx
    if config.TOUCH_INVERT_Y:
        ny = 1 - ny
    x = int(min(max(nx, 0), 0.999) * config.WIDTH)
    y = int(min(max(ny, 0), 0.999) * config.HEIGHT)
    return x, y


def _find_device(evdev):
    if config.TOUCH_DEVICE != "auto":
        return evdev.InputDevice(config.TOUCH_DEVICE)
    for path in evdev.list_devices():
        device = evdev.InputDevice(path)
        keys = device.capabilities().get(evdev.ecodes.EV_KEY, [])
        if evdev.ecodes.BTN_TOUCH in keys:
            return device
    return None


def run(on_tap):
    """Call on_tap(x, y) each time a finger lifts. Blocks forever."""
    try:
        import evdev
    except ImportError:
        print("python3-evdev not installed: touch disabled")
        return
    device = _find_device(evdev)
    if device is None:
        print("no touch screen found: touch disabled")
        return
    print(f"Using touch device {device.path}: {device.name}")
    codes = evdev.ecodes
    x_axis, y_axis = device.absinfo(codes.ABS_X), device.absinfo(codes.ABS_Y)
    x_range, y_range = (x_axis.min, x_axis.max), (y_axis.min, y_axis.max)
    raw_x, raw_y = None, None
    for event in device.read_loop():
        if event.type == codes.EV_ABS and event.code == codes.ABS_X:
            raw_x = event.value
        elif event.type == codes.EV_ABS and event.code == codes.ABS_Y:
            raw_y = event.value
        elif event.type == codes.EV_KEY and event.code == codes.BTN_TOUCH and event.value == 0:
            if raw_x is not None and raw_y is not None:
                on_tap(*to_screen(raw_x, raw_y, x_range, y_range))


if __name__ == "__main__":
    # Tap each corner: top-left should print a small x and y, bottom-right
    # should print close to the screen size.
    print(f"Screen is {config.WIDTH}x{config.HEIGHT}. Tap the corners, Ctrl+C to stop.")
    run(lambda x, y: print(f"tap at x={x} y={y}"))
