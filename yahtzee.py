"""
YAHTZEE GAME
------------
A simplified Yahtzee game built with Pygame.
Allows multiple players (1-9) to roll, keep/unkeep dice, and score in various categories.
At the end of 13 rounds, displays final scores for each player and offers a replay option.
"""

import pygame
import sys
import random
from collections import Counter

# ---------------------------------------------------------------------------
#                               CONSTANTS
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 30

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (34, 139, 34)      # Greenish background for rolling screen
BROWN = (222, 184, 135)    # Very light brown for scorecard & final screens

# Dice & Game Play
NUM_DICE = 5
MAX_TURNS = 13             # Each player gets 13 turns total (standard Yahtzee).
MAX_ROLLS_PER_TURN = 2     # Each turn, a player can roll up to 2 extra times after the initial roll.

# ---------------------------------------------------------------------------
#                               PYGAME SETUP
# ---------------------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Yahtzee")
clock = pygame.time.Clock()

# Fonts
font = pygame.font.SysFont("consolas", 28)
small_font = pygame.font.SysFont("consolas", 24)

# ---------------------------------------------------------------------------
#                               LOAD IMAGES
# ---------------------------------------------------------------------------

# --- Load dice faces ---
dice_image = pygame.image.load("dice.png").convert_alpha()
DICE_FACE_WIDTH = dice_image.get_width() // 6   # 6 faces horizontally
DICE_FACE_HEIGHT = dice_image.get_height()
dice_faces = []
for i in range(6):
    # Crop each face from the sprite sheet
    face_rect = pygame.Rect(i * DICE_FACE_WIDTH, 0, DICE_FACE_WIDTH, DICE_FACE_HEIGHT)
    face_surf = dice_image.subsurface(face_rect)
    dice_faces.append(face_surf)

# --- Load and scale cup sprite sheet ---
cup_image = pygame.image.load("dice-cup.png").convert_alpha()
CUP_FRAME_COUNT = 4
CUP_FRAME_WIDTH = cup_image.get_width() // CUP_FRAME_COUNT
CUP_FRAME_HEIGHT = cup_image.get_height()
CUP_SCALE = 2.5  # How much we scale the cup images

scaled_cup_frames = []
for i in range(CUP_FRAME_COUNT):
    # Crop each cup frame from the sprite sheet
    frame_rect = pygame.Rect(i * CUP_FRAME_WIDTH, 0, CUP_FRAME_WIDTH, CUP_FRAME_HEIGHT)
    frame_surf = cup_image.subsurface(frame_rect)
    scaled_frame = pygame.transform.scale(
        frame_surf,
        (int(CUP_FRAME_WIDTH * CUP_SCALE), int(CUP_FRAME_HEIGHT * CUP_SCALE))
    )
    scaled_cup_frames.append(scaled_frame)

# Derived scaled dimensions for the cup
SCALED_CUP_WIDTH = CUP_FRAME_WIDTH * CUP_SCALE
SCALED_CUP_HEIGHT = CUP_FRAME_HEIGHT * CUP_SCALE

# ---------------------------------------------------------------------------
#                 DICE POSITIONS FOR ROLLING SCREEN
# ---------------------------------------------------------------------------
# Predefined positions for each of the 5 dice on the rolling screen
dice_positions = [
    (100, 250),
    (250, 250),
    (400, 250),
    (550, 250),
    (700, 250),
]

# Each player's scoreboard is a dictionary of category -> score (or None).
scoreboards = []  # List of dicts; one per player

# ---------------------------------------------------------------------------
#                       INITIALIZE SCOREBOARDS
# ---------------------------------------------------------------------------
def init_scoreboards(num_players):
    """
    Create and initialize a scoreboard (dict) for each player with None values
    for each scoring category.
    """
    global scoreboards
    scoreboards = []
    for _ in range(num_players):
        sb = {
            "ones": None,
            "twos": None,
            "threes": None,
            "fours": None,
            "fives": None,
            "sixes": None,
            "three_of_a_kind": None,
            "four_of_a_kind": None,
            "full_house": None,
            "small_straight": None,
            "large_straight": None,
            "yahtzee": None,
            "chance": None
        }
        scoreboards.append(sb)

# ---------------------------------------------------------------------------
#                       PROMPT NUMBER OF PLAYERS
# ---------------------------------------------------------------------------
def prompt_player_count():
    """
    Displays a prompt page asking how many players want to play.
    The user presses a key from 1-9; the chosen number is displayed with a
    message telling the user to press Enter to start with that many players.
    The user can press another number key to change the selection.
    Returns the chosen number as an integer.
    """
    chosen_number = None
    waiting_for_enter = False
    box_width, box_height = 700, 150

    while True:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                # If a number key 1-9 is pressed, update chosen_number
                if pygame.K_1 <= event.key <= pygame.K_9:
                    chosen_number = event.key - pygame.K_0  # Convert key to number
                    waiting_for_enter = True
                elif waiting_for_enter and event.key == pygame.K_RETURN:
                    if chosen_number is not None:
                        return chosen_number

        # Drawing the prompt screen
        screen.fill(BROWN)
        box_x = (WINDOW_WIDTH - box_width) // 2
        box_y = (WINDOW_HEIGHT - box_height) // 2
        pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, BLACK, (box_x, box_y, box_width, box_height), 2)

        if not waiting_for_enter:
            prompt_text = "Select Number of Players: Press [1]-[9]"
        else:
            plural_s = "s" if chosen_number > 1 else ""
            prompt_text = f"You selected {chosen_number} player{plural_s}. Press Enter to start."

        draw_text(prompt_text, box_x + box_width//2, box_y + box_height//2, RED, center=True, font_obj=font)

        pygame.display.flip()
        clock.tick(FPS)

# ---------------------------------------------------------------------------
#                               ROLL DICE
# ---------------------------------------------------------------------------
def roll_dice(dice_kept, dice_values):
    """
    Roll dice that are not kept (dice_kept[i] == False).
    Each rolled die gets a random value from 1-6.
    Returns updated dice_values list.
    """
    for i in range(NUM_DICE):
        if not dice_kept[i]:
            dice_values[i] = random.randint(1, 6)
    return dice_values

# ---------------------------------------------------------------------------
#                           HELPER DRAW FUNCTIONS
# ---------------------------------------------------------------------------
def draw_text(text, x, y, color=BLACK, center=False, font_obj=font):
    """
    Renders text onto the screen at (x, y).
    If center=True, draws the text centered at (x, y).
    """
    text_surface = font_obj.render(text, True, color)
    if center:
        rect = text_surface.get_rect(center=(x, y))
        screen.blit(text_surface, rect)
    else:
        screen.blit(text_surface, (x, y))

def draw_dashed_line(surface, color, start_pos, end_pos, width=1, dash_length=10):
    """
    Draws a horizontal dashed line on the given surface from start_pos to end_pos.
    The dash_length determines how long each dash is.
    """
    x1, y = start_pos
    x2, _ = end_pos
    for x in range(x1, x2, dash_length*2):
        end_dash = min(x + dash_length, x2)
        pygame.draw.line(surface, color, (x, y), (end_dash, y), width)

# ---------------------------------------------------------------------------
#                       CALCULATE POSSIBLE SCORES
# ---------------------------------------------------------------------------
def calculate_possible_scores(dice_values):
    """
    Given a list of 5 dice values, calculates all possible scores for each category,
    and returns a dictionary of category -> possible score.
    """
    counts = Counter(dice_values)
    score_dict = {}

    # Upper section
    score_dict["ones"]   = sum(d for d in dice_values if d == 1)
    score_dict["twos"]   = sum(d for d in dice_values if d == 2)
    score_dict["threes"] = sum(d for d in dice_values if d == 3)
    score_dict["fours"]  = sum(d for d in dice_values if d == 4)
    score_dict["fives"]  = sum(d for d in dice_values if d == 5)
    score_dict["sixes"]  = sum(d for d in dice_values if d == 6)

    # Lower section
    score_dict["three_of_a_kind"] = sum(dice_values) if any(count >= 3 for count in counts.values()) else 0
    score_dict["four_of_a_kind"]  = sum(dice_values) if any(count >= 4 for count in counts.values()) else 0
    score_dict["full_house"]      = 25 if sorted(counts.values()) == [2, 3] else 0

    unique_vals = set(dice_values)
    small_straights = [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]
    score_dict["small_straight"] = 30 if any(s.issubset(unique_vals) for s in small_straights) else 0

    large_straights = [{1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}]
    # Also ensure there are exactly 5 unique values
    score_dict["large_straight"] = 40 if any(s == unique_vals for s in large_straights) and len(unique_vals) == 5 else 0

    score_dict["yahtzee"] = 50 if any(count == 5 for count in counts.values()) else 0
    score_dict["chance"]  = sum(dice_values)

    return score_dict

# ---------------------------------------------------------------------------
#                  CUP ANIMATION FOR ROLLING DICE
# ---------------------------------------------------------------------------
def animate_cup_shake(dice_kept, dice_values):
    """
    Animates the cup shaking process for dice that are not kept.
    Moves dice into the cup, shows shaking animation, and moves them back out.
    Then actually rolls (randomizes) the unkept dice.
    """
    # Cup location
    cup_x = WINDOW_WIDTH // 2 - (SCALED_CUP_WIDTH // 2)
    cup_y = 400

    # Starting positions are the current dice positions
    start_positions = [list(dice_positions[i]) for i in range(NUM_DICE)]
    dice_scales = [1.0] * NUM_DICE

    # Target is somewhere inside the cup area
    target_x = cup_x + (SCALED_CUP_WIDTH // 2) - (DICE_FACE_WIDTH // 2)
    target_y = cup_y + (SCALED_CUP_HEIGHT // 4)

    # Final positions (where dice originally were)
    final_positions = [list(dice_positions[i]) for i in range(NUM_DICE)]

    # Move the dice in
    steps_in = 15
    for step in range(steps_in):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        frac = (step + 1) / steps_in
        for i in range(NUM_DICE):
            if not dice_kept[i]:
                sx, sy = start_positions[i]
                start_positions[i][0] = sx + (target_x - sx) * frac
                start_positions[i][1] = sy + (target_y - sy) * frac
                dice_scales[i] = 1.0 - 0.5 * frac

        draw_rolling_scene(dice_values, dice_kept, scaled_cup_frames[0],
                           (cup_x, cup_y), start_positions, dice_scales)
        clock.tick(FPS)

    # Shake the cup (cycling through cup frames)
    shake_frames = 36
    for frame_idx in range(shake_frames):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        cup_frame = scaled_cup_frames[frame_idx % CUP_FRAME_COUNT]
        draw_rolling_scene(dice_values, dice_kept, cup_frame,
                           (cup_x, cup_y), start_positions, dice_scales, skip_unkept=True)
        clock.tick(FPS)

    # Roll the unkept dice
    roll_dice(dice_kept, dice_values)

    # Move the dice back out
    steps_out = 15
    for i in range(NUM_DICE):
        if not dice_kept[i]:
            start_positions[i][0] = target_x
            start_positions[i][1] = target_y
            dice_scales[i] = 0.5

    for step in range(steps_out):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        frac = (step + 1) / steps_out
        for i in range(NUM_DICE):
            if not dice_kept[i]:
                sx, sy = start_positions[i]
                fx, fy = final_positions[i]
                start_positions[i][0] = sx + (fx - sx) * frac
                start_positions[i][1] = sy + (fy - sy) * frac
                dice_scales[i] = 0.5 + 0.5 * frac

        draw_rolling_scene(dice_values, dice_kept, scaled_cup_frames[0],
                           (cup_x, cup_y), start_positions, dice_scales)
        clock.tick(FPS)

# ---------------------------------------------------------------------------
#                     DRAW DICE/CUP SCENE (ROLLING SCREEN)
# ---------------------------------------------------------------------------
def draw_rolling_scene(dice_values, dice_kept, cup_frame, cup_pos,
                       current_dice_positions, dice_scales, skip_unkept=False):
    """
    Draws the main "rolling" screen with background, a status box at the top,
    the dice in their current positions, and the cup sprite.
    If skip_unkept=True, unkept dice are not drawn (used during cup shaking).
    """
    screen.fill(GREEN)

    # A white box at the top with a border
    box_width, box_height = 600, 150
    box_x = (WINDOW_WIDTH - box_width) // 2
    box_y = 20
    pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height))
    pygame.draw.rect(screen, BLACK, (box_x, box_y, box_width, box_height), 2)

    # Some text inside that box
    text_x = box_x + 20
    text_y = box_y + 20
    draw_text("Rolling Dice...", text_x, text_y, font_obj=small_font)

    # Draw the dice
    for i in range(NUM_DICE):
        if skip_unkept and not dice_kept[i]:
            continue  # Skip drawing unkept dice
        die_value = dice_values[i]
        x, y = current_dice_positions[i]
        scale = dice_scales[i]

        # Scale the dice image
        w = int(DICE_FACE_WIDTH * scale)
        h = int(DICE_FACE_HEIGHT * scale)
        scaled_face = pygame.transform.scale(dice_faces[die_value - 1], (w, h))
        face_rect = scaled_face.get_rect(center=(x, y))
        screen.blit(scaled_face, face_rect.topleft)

        # Draw a red outline if the die is kept
        if dice_kept[i]:
            outline_rect = pygame.Rect(face_rect.topleft, (w, h))
            pygame.draw.rect(screen, RED, outline_rect, 3)

    # Draw the cup
    screen.blit(cup_frame, cup_pos)
    pygame.display.flip()

# ---------------------------------------------------------------------------
#                      DISPLAY SCORECARD & CHOOSE CATEGORY
# ---------------------------------------------------------------------------
def display_scorecard_options(dice_values, current_player, round_num):
    """
    Display all scoring categories to the current player based on dice_values.
    The player can press a key to select a category. If [0] is pressed first,
    the player is forced into ZERO MODE, meaning their next category selection
    is assigned 0 points.
    Returns the chosen category and a boolean indicating if zero mode is active.
    """
    possible_scores = calculate_possible_scores(dice_values)
    chosen_category = None
    zero_selected = False
    zero_mode = False

    # Mapping each category to a prompt and a key
    cat_key_map = [
        ("ones", "Press [1] for Ones", pygame.K_1),
        ("twos", "Press [2] for Twos", pygame.K_2),
        ("threes", "Press [3] for Threes", pygame.K_3),
        ("fours", "Press [4] for Fours", pygame.K_4),
        ("fives", "Press [5] for Fives", pygame.K_5),
        ("sixes", "Press [6] for Sixes", pygame.K_6),
        ("three_of_a_kind", "Press [A] for 3 of a Kind", pygame.K_a),
        ("four_of_a_kind",  "Press [B] for 4 of a Kind", pygame.K_b),
        ("full_house",      "Press [C] for Full House", pygame.K_c),
        ("small_straight",  "Press [D] for Small Straight", pygame.K_d),
        ("large_straight",  "Press [E] for Large Straight", pygame.K_e),
        ("yahtzee",         "Press [F] for Yahtzee", pygame.K_f),
        ("chance",          "Press [G] for Chance", pygame.K_g)
    ]

    current_scoreboard = scoreboards[current_player]

    while chosen_category is None:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Check for zero-mode toggle
                if event.key == pygame.K_0:
                    zero_mode = True

                # Check each category
                for cat, prompt, key in cat_key_map:
                    if event.key == key and current_scoreboard[cat] is None:
                        # If zero mode is active, forcibly assign 0
                        if zero_mode:
                            chosen_category = cat
                            zero_selected = True
                        else:
                            # For some categories, only allow selection if there's a positive score
                            if cat in ["three_of_a_kind", "four_of_a_kind", "full_house",
                                       "small_straight", "large_straight", "yahtzee"]:
                                if possible_scores[cat] > 0:
                                    chosen_category = cat
                            else:
                                chosen_category = cat

        # Drawing the scorecard screen
        screen.fill(BROWN)

        # Header
        header_text = f"Player {current_player+1} Scorecard - Round {round_num} of {MAX_TURNS}"
        draw_text(header_text, WINDOW_WIDTH//2, 30, RED, center=True, font_obj=font)
        header_surface = font.render(header_text, True, RED)
        header_rect = header_surface.get_rect(center=(WINDOW_WIDTH//2, 30))
        line_y = header_rect.bottom + 5
        draw_dashed_line(screen, BLACK, (50, line_y), (WINDOW_WIDTH-50, line_y), width=2, dash_length=10)

        # Zero mode info
        if zero_mode:
            draw_text("ZERO MODE ACTIVE: Choose category to assign 0",
                      WINDOW_WIDTH//2, 66, RED, center=True, font_obj=small_font)
        else:
            draw_text("Press [0] to take a 0 on a category",
                      WINDOW_WIDTH//2, 66, RED, center=True, font_obj=small_font)

        # Display category prompts and possible scores
        x_prompt = 50
        x_score = 600
        y_offset = 80
        line_height = 40

        for cat, prompt, key in cat_key_map:
            if current_scoreboard[cat] is not None:
                score_text = f"USED (Score: {current_scoreboard[cat]})"
            else:
                if cat in ["three_of_a_kind", "four_of_a_kind", "full_house",
                           "small_straight", "large_straight", "yahtzee"]:
                    if possible_scores[cat] == 0:
                        score_text = "Not eligible"
                    else:
                        score_text = f"Possible Score = {possible_scores[cat]}"
                else:
                    score_text = f"Possible Score = {possible_scores[cat]}"

            draw_text(prompt, x_prompt, y_offset, font_obj=small_font)
            draw_text(score_text, x_score, y_offset, font_obj=small_font)
            y_offset += line_height

        # Show the dice
        half_w = DICE_FACE_WIDTH // 2
        half_h = DICE_FACE_HEIGHT // 2
        total_w = NUM_DICE * half_w + (NUM_DICE - 1) * 20
        start_x = (WINDOW_WIDTH - total_w) // 2
        y_dice = WINDOW_HEIGHT - half_h - 20

        for i in range(NUM_DICE):
            scaled_die = pygame.transform.scale(dice_faces[dice_values[i]-1], (half_w, half_h))
            x = start_x + i * (half_w + 20)
            screen.blit(scaled_die, (x, y_dice))

        pygame.display.flip()
        clock.tick(FPS)

    return chosen_category, zero_selected

# ---------------------------------------------------------------------------
#                 APPLY SCORE TO SELECTED CATEGORY
# ---------------------------------------------------------------------------
def apply_score_to_category(category, dice_values, current_player, zero_selected=False):
    """
    Apply the dice_values to the chosen category in the scoreboard.
    If zero_selected is True, that category is assigned 0 points.
    Otherwise, the category is assigned the calculated possible score.
    """
    if zero_selected:
        scoreboards[current_player][category] = 0
    else:
        scores = calculate_possible_scores(dice_values)
        scoreboards[current_player][category] = scores[category]

# ---------------------------------------------------------------------------
#                         CALCULATE FINAL SCORES
# ---------------------------------------------------------------------------
def calculate_final_score(current_scoreboard):
    """
    Given a player's scoreboard, calculates final scores:
    - Upper section total
    - Bonus (35 pts for >=63 in upper section)
    - Lower section total
    - Grand total
    Returns a tuple: (upper_score, bonus, lower_score, total_score).
    """
    upper_keys = ["ones", "twos", "threes", "fours", "fives", "sixes"]
    lower_keys = ["three_of_a_kind", "four_of_a_kind", "full_house",
                  "small_straight", "large_straight", "yahtzee", "chance"]

    upper_score = sum(current_scoreboard[k] for k in upper_keys if current_scoreboard[k] is not None)
    lower_score = sum(current_scoreboard[k] for k in lower_keys if current_scoreboard[k] is not None)
    bonus = 35 if upper_score >= 63 else 0
    total = upper_score + bonus + lower_score
    return upper_score, bonus, lower_score, total

# ---------------------------------------------------------------------------
#                       GAME OVER / FINAL SCORES SCREEN
# ---------------------------------------------------------------------------
def game_over_screen():
    """
    Displays the final scores for all players.
    Shows a "Play Again" button, which, when clicked, resets the scoreboards and restarts the game.
    """
    # Compute final results
    results = []
    for i, sb in enumerate(scoreboards):
        upper, bonus, lower, total = calculate_final_score(sb)
        results.append((i+1, upper, bonus, lower, total))

    # Positioning for the results box
    box_width, box_height = 600, 300
    box_x = (WINDOW_WIDTH - box_width) // 2
    box_y = 50

    # Positioning for the "Play Again" button
    button_width, button_height = 200, 50
    button_x = (WINDOW_WIDTH - button_width) // 2
    button_y = box_y + box_height + 20

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # If the "Play Again" button is clicked
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos
                button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
                if button_rect.collidepoint(mouse_x, mouse_y):
                    # Reset the scoreboards and restart
                    for key in range(len(scoreboards)):
                        scoreboards[key] = {k: None for k in scoreboards[key]}
                    main()

        # Draw final scores screen
        screen.fill(BROWN)
        pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, BLACK, (box_x, box_y, box_width, box_height), 2)

        # Title
        draw_text("Game Over!", box_x + box_width//2, box_y + 30, RED, center=True, font_obj=font)

        # Table header
        y_line = box_y + 70
        draw_text("Player   Upper   Bonus   Lower   Total", box_x + box_width//2, y_line, BLACK,
                  center=True, font_obj=small_font)
        y_line += 30

        # Player results
        for player_num, upper, bonus, lower, total in results:
            line = f"P{player_num}:     {upper}      {bonus}      {lower}     {total}"
            draw_text(line, box_x + 20, y_line, BLACK, font_obj=small_font)
            y_line += 30

        # "Play Again" button
        pygame.draw.rect(screen, WHITE, (button_x, button_y, button_width, button_height))
        pygame.draw.rect(screen, BLACK, (button_x, button_y, button_width, button_height), 2)
        draw_text("Play Again", button_x + button_width//2, button_y + button_height//2,
                  RED, center=True, font_obj=font)

        pygame.display.flip()
        clock.tick(FPS)

# ---------------------------------------------------------------------------
#                                MAIN GAME LOOP
# ---------------------------------------------------------------------------
def main():
    """
    Main game function that runs through each turn for all players,
    handles dice rolling and category scoring, and then shows the game-over screen.
    """
    # Ask for number of players and initialize their scoreboards
    num_players = prompt_player_count()
    init_scoreboards(num_players)

    # Each round: each player takes a turn
    for round_num in range(1, MAX_TURNS + 1):
        for current_player in range(num_players):
            # Initialize dice for this turn
            dice_values = [0] * NUM_DICE
            dice_kept = [False] * NUM_DICE
            rolls_left = MAX_ROLLS_PER_TURN
            turn_ended = False

            # First roll
            dice_values = roll_dice(dice_kept, dice_values)

            # During a turn, the player can roll up to MAX_ROLLS_PER_TURN times
            while not turn_ended:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                    if event.type == pygame.KEYDOWN:
                        # Exit if ESCAPE is pressed
                        if event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()

                        # Roll again if 'R' is pressed and rolls remain
                        if event.key == pygame.K_r:
                            if rolls_left > 0:
                                animate_cup_shake(dice_kept, dice_values)
                                rolls_left -= 1
                            else:
                                print("No rolls left this turn.")

                        # End turn if 'E' is pressed
                        if event.key == pygame.K_e:
                            turn_ended = True

                    # Click on a die to toggle "keep" status
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mouse_pos = event.pos
                        for i in range(NUM_DICE):
                            x, y = dice_positions[i]
                            rect = pygame.Rect(x, y, DICE_FACE_WIDTH, DICE_FACE_HEIGHT)
                            if rect.collidepoint(mouse_pos):
                                dice_kept[i] = not dice_kept[i]

                # Draw the rolling screen
                screen.fill(GREEN)
                box_width, box_height = 600, 150
                box_x = (WINDOW_WIDTH - box_width)//2
                box_y = 20
                pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height))
                pygame.draw.rect(screen, BLACK, (box_x, box_y, box_width, box_height), 2)

                text_x = box_x + 20
                text_y = box_y + 20
                header = f"Player {current_player+1} - Round {round_num} of {MAX_TURNS}"
                draw_text(header, text_x, text_y, RED, font_obj=small_font)
                draw_text(f"Rolls Left: {rolls_left}", text_x, text_y+30, font_obj=small_font)
                draw_text("Press R to roll, E to end turn.", text_x, text_y+60, font_obj=small_font)
                draw_text("Click a die to keep/unkeep it.", text_x, text_y+90, font_obj=small_font)

                # Draw dice, marking kept dice with a red outline
                for i in range(NUM_DICE):
                    val = dice_values[i]
                    x, y = dice_positions[i]
                    screen.blit(dice_faces[val - 1], (x, y))
                    if dice_kept[i]:
                        pygame.draw.rect(screen, RED, (x, y, DICE_FACE_WIDTH, DICE_FACE_HEIGHT), 3)

                pygame.display.flip()
                clock.tick(FPS)

                # If no rolls remain, forcibly end turn
                if rolls_left == 0:
                    turn_ended = True

            # After the player ends their turn, they must choose a category to score
            chosen_cat, zero_selected = display_scorecard_options(dice_values, current_player, round_num)
            apply_score_to_category(chosen_cat, dice_values, current_player, zero_selected)

    # After all rounds, show the final scores
    game_over_screen()

# ---------------------------------------------------------------------------
#                               ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
