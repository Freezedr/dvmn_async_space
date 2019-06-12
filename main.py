import asyncio
import curses
import time
import random
import itertools

import os

from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from fire_animation import fire

coroutines = []
obstacles = []

spaceship_frame = ''


async def sleep(secs=1):
    iteration_count = int(secs * 10)
    for _ in range(iteration_count):
        await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


async def run_spaceship(canvas, row, column):
    """ Анимация ракеты с поддержкой перемещения"""
    row_speed = column_speed = 0
    MAX_Y, MAX_X = canvas.getmaxyx()
    while True:
        draw_frame(canvas, row, column, spaceship_frame, True)

        row_acceleration, column_acceleration, space_pressed = read_controls(canvas)
        row_speed, column_speed = update_speed(row_speed, column_speed, row_acceleration, column_acceleration)

        if (BORDER < row + row_speed < MAX_Y - FRAME_HEIGHT - BORDER):
            row += row_speed
        if (BORDER < column + column_speed < MAX_X - FRAME_WIDTH - BORDER):
            column += column_speed
        if space_pressed:
            coroutines.append(fire(canvas, row, column + FRAME_WIDTH / 2))

        draw_frame(canvas, row, column, spaceship_frame)
        await sleep(0.2)


async def animate_spaceship():
    global spaceship_frame

    frames_cycle = itertools.cycle([FRAME_1, FRAME_2])
    while True:
        spaceship_frame = next(frames_cycle)
        await sleep(0.1)


async def blink(canvas, row, column, symbol, start_blink_phase):
    """ Анимация звезды """
    PHASES_COUNT = 4
    BLINK_TIMEOUTS = (2, 0.3, 0.5, 0.3)
    LIGHT_MODES = (curses.A_DIM, curses.A_NORMAL, curses.A_BOLD, curses.A_NORMAL)

    while True:
        for phase in range(PHASES_COUNT):
            current_phase = (phase + start_blink_phase) % PHASES_COUNT
            canvas.addstr(row, column, symbol, LIGHT_MODES[current_phase])
            await sleep(BLINK_TIMEOUTS[current_phase])


async def fill_orbit_with_garbage(canvas):
    MAX_Y, MAX_X = canvas.getmaxyx()

    while True:
        await sleep(random.randint(0, 25))
        await fly_garbage(
            canvas,
            random.randint(BORDER, MAX_X - BORDER - 1),
            TRASH_FRAMES[random.randint(0, len(TRASH_FRAMES) - 1)])


def seconds_to_ticks(seconds):
    return seconds / TIC_TIMEOUT


def draw(canvas):
    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)

    MAX_Y, MAX_X = canvas.getmaxyx()
    STARS = 100
    TRASH_AMOUNT = 20

    coroutines.extend(blink(
        canvas,
        random.randint(BORDER, MAX_Y - BORDER - 1),
        random.randint(BORDER, MAX_X - BORDER - 1),
        random.choice('+*.:'),
        random.randint(0, 3)) for _ in range(STARS))

    coroutines.append(run_spaceship(canvas, MAX_Y / 2, MAX_X / 2))
    coroutines.append(animate_spaceship())
    coroutines.extend(fill_orbit_with_garbage(canvas) for _ in range(TRASH_AMOUNT))

    while True:
        for i, coroutine in enumerate(coroutines):
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    FRAME_1 = ''
    FRAME_2 = ''

    TRASH_FRAMES = []

    with open('rocket_frames/rocket_frame_1.txt', 'r') as f:
        FRAME_1 = f.read()

    with open('rocket_frames/rocket_frame_2.txt', 'r') as f:
        FRAME_2 = f.read()

    for root, dirs, files in os.walk('trash_frames/'):
        for file in files:
            with open(os.path.join(root, file)) as f:
                FRAME = f.read()
                TRASH_FRAMES.append(FRAME)

    # Размеры кадров совпадают, возьмём только первый
    FRAME_HEIGHT, FRAME_WIDTH = get_frame_size(FRAME_1)

    TIC_TIMEOUT = 0.1
    BORDER = 1

    curses.update_lines_cols()
    curses.wrapper(draw)
    time.sleep(0.1)
