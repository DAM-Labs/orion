import os, random, time, sys

def animated_starfield():
    try: cols, rows = os.get_terminal_size()
    except OSError: cols, rows = 80, 24

    # Large ORION logo using blocks and pipes
    logo = [
        " █████╗  ██████╗ ██╗ ██████╗ ███╗   ██╗",
        "██╔═══██╗██╔══██╗██║██╔═══██╗████╗  ██║",
        "██║   ██║██████╔╝██║██║   ██║██╔██╗ ██║",
        "██║   ██║██╔══██╗██║██║   ██║██║╚██╗██║",
        "╚██████╔╝██║  ██║██║╚██████╔╝██║ ╚████║",
        " ╚═════╝ ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝"
    ]
    lw, lh = len(logo[0]), len(logo)
    oy, ox = (rows - lh) // 2, (cols - lw) // 2
    frames = 20

    # Pre-generate a static layer of stars
    stars = {}
    for _ in range(int(cols * rows * 0.05)):
        sy, sx = random.randint(0, rows-2), random.randint(0, cols-1)
        stars[(sy, sx)] = random.choice(['.', '+', '*', '°', '♦'])

    os.system('cls' if os.name == 'nt' else 'clear')

    for i in range(frames):
        # Move cursor to top left instead of clearing screen (prevents flickering)
        sys.stdout.write("\033[H")

        for y in range(rows - 1):
            line = []
            for x in range(cols):
                # 1. Draw the Logo
                if oy <= y < oy + lh and ox <= x < ox + lw and logo[y-oy][x-ox] != ' ':
                    line.append(f"\033[1;34m{logo[y-oy][x-ox]}\033[0m") # Dark gray for "far view"

                # 2. Draw Twinkling Stars
                elif (y, x) in stars:
                    char = stars[(y, x)]
                    # Randomly dim or brighten stars to simulate twinkling
                    if random.random() < 0.1:
                        line.append(f"\033[1;37m{char}\033[0m") # Bright white
                    elif random.random() < 0.1:
                        line.append(f"\033[1;30m{char}\033[0m") # Dim gray
                    else:
                        line.append(char) # Normal

                # 3. Empty Space
                else:
                    line.append(" ")

            sys.stdout.write("".join(line) + "\n")

        sys.stdout.flush()
        time.sleep(0.1) # Controls animation speed

    os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    animated_starfield()
