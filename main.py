import asyncio
import curses
import time
import random

import os

from math import inf

from curses_tools import draw_frame, read_controls, get_frame_size
from space_garbage import fly_garbage

coroutines = []


async def sleep(tics=1):
    iteration_count = int(tics * 10)
    for _ in range(iteration_count):
        await asyncio.sleep(0)


async def rocket(canvas, row, column):
    """ Анимация ракеты с поддержкой перемещения"""
    while True:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)

        draw_frame(canvas, row, column, FRAME_2, True)
        draw_frame(canvas, row, column, FRAME_1)
        await asyncio.sleep(0)

        draw_frame(canvas, row, column, FRAME_1, True)
        draw_frame(canvas, row, column, FRAME_2)
        await asyncio.sleep(0)

        draw_frame(canvas, row, column, FRAME_2, True)

        MAX_Y, MAX_X = canvas.getmaxyx()

        if (BORDER < row + rows_direction < MAX_Y - FRAME_HEIGHT - BORDER):
            row += rows_direction
        if (BORDER < column + columns_direction < MAX_X - FRAME_WIDTH - BORDER):
            column += columns_direction


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

    coroutines.append(rocket(canvas, MAX_Y / 2, MAX_X / 2))
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
