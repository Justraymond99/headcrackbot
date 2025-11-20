import sys
import pygame
import numpy as np

pygame.init()

#Colors

WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

# Proportions & Sizes
WIDTH = 300
HEIGHT = 300
LINE_WIDTH = 5
BOARD_ROWS = 3
BOARD_COLS = 3
SQUARE_SIZE = WIDTH // BOARD_COLS
CIRCLE_RADIUS = SQUARE_SIZE
CIRCLE_WIDTH = 15
CROSS_WIDTH = 25

screen= pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Tic Tac Toe')
screen.fill(BLACK)


board = np.zeros((BOARD_ROWS, BOARD_COLS))

def draw_lines(color=WHITE):
   for i in range(1, BOARD_ROWS):
       pygame.draw.line(screen, color, start_pos:(0, i * SQUARE_SIZE), end_pos:(WIDTH, i * SQUARE_SIZE), LINE_WIDTH)
       pygame.draw.line(screen, color, start_pos:(i * SQUARE_SIZE, 0), end_pos(i * SQUARE_SIZE, HEIGHT), LINE_WIDTH)



def draw_figures(color=WHITE):
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] == 1:
                pygame.draw.circle(screen, color, center:(int(col * SQUARE_SIZE + SQUARE_SIZE // 2), int(row * SQUARE_SIZE + SQUARE_SIZE // 2)), CIRCLE_RADIUS, CIRCLE_WIDTH)
            elif board[row][col] == 2:
                pygame.draw.line(screen, color, start_pos:(col * SQUARE_SIZE + SQUARE_SIZE // 4, row * SQUARE_SIZE + SQUARE_SIZE // 4), end_pos:(col * SQUARE_SIZE + 3 * SQUARE_SIZE // 4, row * SQUARE_SIZE + 3 * SQUARE_SIZE // 4), CROSS_WIDTH)