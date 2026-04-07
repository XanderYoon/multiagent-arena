from game_engine import *
from architectures import *


def log(txt):
    with open("results.txt", "a", encoding="utf-8") as f:
        f.write(str(txt) + "\n")
    print(txt)


def format_trace(name, trace):
    """Formats the inner thoughts of the agents so it looks clean in the text file."""
    log(f"\n[ REASONING TRACE FOR {name} ]")
    for step in trace:
        log(f"  -> {step}")
    log("-" * 40)


def blotto_match(n1, f1, n2, f2, trial):
    log(f"\n" + "="*50)
    log(f"--- {n1} vs {n2} (Simultaneous Resource Game) | TRIAL {trial}/3 ---")

    pts, trps = generate_blotto_setup()

    # ABSTRACTED STRICT RULES
    # rules = (f"You are playing a simultaneous resource allocation game. "
    #          f"You have exactly {trps} units. You must distribute ALL of them across 3 distinct zones. "
    #          f"If you assign strictly more units to a zone than your opponent, you win the points for that zone. "
    #          f"Constraint: Your output must be a list of 3 integers that sum to exactly {trps}.")

    rules = (f"You are playing a simultaneous resource allocation game. "
             f"You have exactly {trps} units. You must distribute ALL of them across 3 distinct zones. "
             f"FATAL CONSTRAINT: Your output must be a list of 3 integers. "
             f"MATH CHECK: You MUST verify that Value 1 + Value 2 + Value 3 = EXACTLY {trps}. Do not fail this math check.")

    state = f"Zone Point Values: Zone A: {pts[0]}, Zone B: {pts[1]}, Zone C: {pts[2]}"

    # Player 1
    out1, trace1 = f1(rules, state)
    m1 = out1.get("move", [0, 0, 0]) if out1 else [0, 0, 0]
    format_trace(n1, trace1)

    # Player 2
    out2, trace2 = f2(rules, state)
    m2 = out2.get("move", [0, 0, 0]) if out2 else [0, 0, 0]
    if n2 != "Uniform Bot" and n2 != "Random Bot":
        format_trace(n2, trace2)

    # Strict Boundary Check
    if type(m1) != list or sum(m1) != trps:
        log(f"HALLUCINATION PENALTY: {n1} invalid {m1}")
        m1 = [0, 0, 0]
    if type(m2) != list or sum(m2) != trps:
        log(f"HALLUCINATION PENALTY: {n2} invalid {m2}")
        m2 = [0, 0, 0]

    s1, s2 = evaluate_blotto(m1, m2, pts)
    log(f"Board Points: {pts}")
    log(f"{n1}: {m1} (Score: {s1}) | {n2}: {m2} (Score: {s2})")

    if s1 > s2:
        log(f">>> WINNER: {n1} <<<")
    elif s2 > s1:
        log(f">>> WINNER: {n2} <<<")
    else:
        log(">>> WINNER: TIE <<<")


def connect4_ai_vs_ai(n1, f1, n2, f2, trial):
    log(f"\n" + "="*50)
    log(f"--- {n1} vs {n2} (Gravity Grid Game) | TRIAL {trial}/3 ---")
    board, turn = create_board(), 1

    # ABSTRACTED STRICT RULES
    rules = ("You are playing a sequential gravity-grid game on a 7-column by 6-row board. "
             "IMPORTANT ALIGNMENT: The columns are 0-indexed. They are numbered exactly 0, 1, 2, 3, 4, 5, and 6. "
             "Column 0 is the far left wall, and Column 6 is the far right wall. "
             "Players alternate dropping a single token into one of the available columns. "
             "The token falls straight down to the lowest available empty slot. "
             "Your goal is to connect 4 of your own tokens horizontally, vertically, or diagonally. "
             "Constraint: You must output a single integer between 0 and 6 representing your chosen column.")

    while True:
        valid = get_valid_cols(board)
        if not valid:
            log(">>> WINNER: DRAW (Board Full) <<<")
            break

        curr_name, curr_func = (n1, f1) if turn == 1 else (n2, f2)
        turn_rules = rules + f" You are Player {turn}."

        out, trace = curr_func(turn_rules, print_board(
            board) + f"\nValid Columns to play: {valid}")
        move = out.get("move", -1) if out else -1

        log(f"\nTurn {turn} - {curr_name} thinking...")
        format_trace(curr_name, trace)

        if move not in valid:
            log(f"HALLUCINATION: {curr_name} tried invalid {move}")
            move = random.choice(valid)

        drop_piece(board, move, turn)
        log(f"{curr_name} executes move: Column {move}")

        if check_win(board, turn):
            log(print_board(board))
            log(f">>> WINNER: {curr_name} <<<")
            break
        turn = 2 if turn == 1 else 1


def test_connect4_accuracy(name, func, trial):
    log(f"\n" + "="*50)
    log(f"=== ACCURACY TEST: {name} vs Minimax Oracle | TRIAL {trial}/3 ===")
    board, turn, perfects, blunders, moves = create_board(), 1, 0, 0, 0
    rules = ("Gravity Grid Game (7x6). Drop token in column (0-6). Token falls to bottom. "
             "Connect 4 to win. Output a single integer.")

    while True:
        valid = get_valid_cols(board)
        if not valid:
            break

        best_col, best_score = minimax_solver(
            board, 4, -float('inf'), float('inf'), turn == 2)

        if turn == 1:
            out, trace = func(rules, print_board(board) + f"\nValid: {valid}")
            move = out.get("move", -1) if out else -1
            moves += 1

            # Record reasoning in the log
            format_trace(name, trace)

            if move == best_col:
                perfects += 1
            else:
                tmp = copy.deepcopy(board)
                if drop_piece(tmp, move if move in valid else random.choice(valid), 1):
                    if minimax_solver(tmp, 3, -float('inf'), float('inf'), False)[1] < best_score:
                        blunders += 1

            if move not in valid:
                move = random.choice(valid)
            drop_piece(board, move, 1)
            if check_win(board, 1):
                log(f">>> {name} BEAT THE ORACLE! <<<")
                break
            turn = 2
        else:
            drop_piece(board, best_col, 2)
            if check_win(board, 2):
                log(">>> ORACLE WINS <<<")
                break
            turn = 1

    acc = (perfects/moves)*100 if moves > 0 else 0
    log(f"[{name} Trial {trial} Stats] Moves: {moves} | Perfect: {perfects} | Blunders: {blunders} | Accuracy: {acc:.1f}%")


if __name__ == "__main__":
    open("results.txt", "w").close()  # Clear old file
    archs = [("Single Agent", run_single_agent),
             ("Parallel Team", run_parallel_agent),
             ("Hierarchical Team", run_hierarchical_agent)]

    NUM_TRIALS = 3  # Runs every experiment 3 times

    # 1. AI vs AI TOURNAMENT
    log("\n" + "#"*60)
    log("PHASE 1: INTERNAL AI vs AI TOURNAMENT")
    log("#"*60)
    matchups = [(archs[0], archs[1]), (archs[0],
                                       archs[2]), (archs[1], archs[2])]

    for trial in range(1, NUM_TRIALS + 1):
        for (n1, f1), (n2, f2) in matchups:
            blotto_match(n1, f1, n2, f2, trial)
            connect4_ai_vs_ai(n1, f1, n2, f2, trial)

    # 2. AI vs BOTS (Blotto)
    log("\n" + "#"*60)
    log("PHASE 2: AI vs STANDARD BOTS (RESOURCE ALLOCATION)")
    log("#"*60)
    for trial in range(1, NUM_TRIALS + 1):
        for name, func in archs:
            blotto_match(name, func, "Uniform Bot", lambda r,
                         s: ({"move": [33, 33, 34]}, []), trial)
            blotto_match(name, func, "Random Bot", lambda r, s: (
                {"move": get_random_blotto()}, []), trial)

    # 3. AI vs ORACLE (Connect 4 Accuracy)
    log("\n" + "#"*60)
    log("PHASE 3: GRAVITY GRID OPTIMAL ACCURACY")
    log("#"*60)
    for trial in range(1, NUM_TRIALS + 1):
        for name, func in archs:
            test_connect4_accuracy(name, func, trial)
