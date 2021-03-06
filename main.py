import asyncio
import curses
import time
import random
import itertools

import os

from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from fire_animation import fire
from explosion import explode
from game_scenario import get_garbage_delay_tics

import obstacles as obs

coroutines = []

obstacles = []
obstacles_in_last_collisions = []

spaceship_frame = ''

year = 1957


async def sleep(secs=1.0):
    iteration_count = int(secs * 10)
    for _ in range(iteration_count):
        await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    global obstacles, obstacles_in_last_collisions
    rows_number, columns_number = canvas.getmaxyx()
    height, width = get_frame_size(garbage_frame)

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    obstacle = obs.Obstacle(row, column, height, width)
    obstacles.append(obstacle)

    while row < rows_number:
        if obstacle in obstacles_in_last_collisions:
            obstacles.remove(obstacle)
            obstacles_in_last_collisions.remove(obstacle)
            await explode(canvas, row + height / 2, column + width / 2)
            return

        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
        obstacle.row = row
    obstacles.remove(obstacle)


async def run_spaceship(canvas, row, column):
    """ Анимация ракеты с поддержкой перемещения"""
    global year
    row_speed = column_speed = 0
    MAX_Y, MAX_X = canvas.getmaxyx()
    while True:
        current_frame, current_row, current_column = spaceship_frame, row, column
        draw_frame(canvas, row, column, spaceship_frame)

        row_acceleration, column_acceleration, space_pressed = read_controls(canvas)
        row_speed, column_speed = update_speed(row_speed, column_speed, row_acceleration, column_acceleration)

        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                await show_gameover(canvas)
                return

        if (BORDER < row + row_speed < MAX_Y - FRAME_HEIGHT - BORDER):
            row += row_speed
        if (BORDER < column + column_speed < MAX_X - FRAME_WIDTH - BORDER):
            column += column_speed
        if space_pressed and year >= 2020:
            coroutines.append(fire(canvas, row, column + FRAME_WIDTH / 2, obstacles, obstacles_in_last_collisions))
        await sleep(0.1)
        draw_frame(canvas, current_row, current_column, current_frame, True)
        draw_frame(canvas, row, column, spaceship_frame)


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
    global year
    MAX_Y, MAX_X = canvas.getmaxyx()

    while True:
        delay = get_garbage_delay_tics(year)
        if delay:
            await sleep(delay / 10)
            coroutines.append(fly_garbage(
                canvas,
                random.randint(BORDER, MAX_X - BORDER - 1),
                TRASH_FRAMES[random.randint(0, len(TRASH_FRAMES) - 1)]))
        else:
            await sleep(0.1)


async def show_gameover(canvas):
    height, width = canvas.getmaxyx()

    GAME_OVER = ''

    with open('rocket_frames/game_over.txt', 'r') as f:
        GAME_OVER = f.read()

    text_height, text_width = get_frame_size(GAME_OVER)
    while True:
        draw_frame(canvas, height / 2 - text_height / 2, width / 2 - text_width / 2, GAME_OVER)
        await sleep(0.1)


def seconds_to_ticks(seconds):
    return seconds / TIC_TIMEOUT


def draw(canvas):
    global year
    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)

    MAX_Y, MAX_X = canvas.getmaxyx()
    STARS = 100

    game_window = canvas.derwin(MAX_Y - BORDER * 3, MAX_X // 2)

    coroutines.extend(blink(
        canvas,
        random.randint(BORDER, MAX_Y - BORDER - 1),
        random.randint(BORDER, MAX_X - BORDER - 1),
        random.choice('+*.:'),
        random.randint(0, 3)) for _ in range(STARS))

    coroutines.append(run_spaceship(canvas, MAX_Y / 2, MAX_X / 2))
    coroutines.append(animate_spaceship())
    coroutines.append(fill_orbit_with_garbage(canvas))

    ticks = 0

    while True:
        draw_frame(game_window, 1, 1, str(year))
        game_window.refresh()

        if ticks == seconds_to_ticks(1.5):
            ticks = 0
            year += 1

        for i, coroutine in enumerate(coroutines):
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)
        ticks += 1


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
