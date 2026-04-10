import copy
import random
from abc import ABC, abstractmethod


class GameEnvironment(ABC):
    def __init__(self, seed=None):
        self.seed = seed
        self.rng = random.Random(seed)

    def reseed(self, seed):
        self.seed = seed
        self.rng = random.Random(seed)

    @abstractmethod
    def reset(self, seed=None):
        raise NotImplementedError

    @abstractmethod
    def get_state(self):
        raise NotImplementedError

    @abstractmethod
    def get_valid_actions(self):
        raise NotImplementedError

    @abstractmethod
    def apply_action(self, action, player=None):
        raise NotImplementedError

    @abstractmethod
    def is_terminal(self):
        raise NotImplementedError

    @abstractmethod
    def get_winner(self):
        raise NotImplementedError

    @abstractmethod
    def get_metrics_context(self):
        raise NotImplementedError


def evaluate_blotto(p1, p2, pts):
    s1, s2 = 0, 0
    for index in range(len(pts)):
        if p1[index] > p2[index]:
            s1 += pts[index]
        elif p2[index] > p1[index]:
            s2 += pts[index]
    return s1, s2


def get_random_blotto(troop_budget=100, battlefields=3, rng=None):
    generator = rng or random
    allocation = []
    remaining = troop_budget
    for _ in range(max(battlefields - 1, 0)):
        value = generator.randint(0, remaining)
        allocation.append(value)
        remaining -= value
    allocation.append(remaining)
    generator.shuffle(allocation)
    return allocation


def normalize_blotto_allocation(allocation, troop_budget, battlefields):
    if not isinstance(allocation, list):
        return None
    if len(allocation) != battlefields:
        return None
    if any(not isinstance(value, int) for value in allocation):
        return None
    if any(value < 0 for value in allocation):
        return None
    if sum(allocation) != troop_budget:
        return None
    return list(allocation)


def allocate_proportionally(weights, troop_budget):
    if troop_budget < 0:
        raise ValueError("troop_budget must be non-negative")
    if not weights:
        return []
    total_weight = sum(max(weight, 0) for weight in weights)
    if total_weight == 0:
        base = [troop_budget // len(weights) for _ in weights]
        for index in range(troop_budget - sum(base)):
            base[index % len(base)] += 1
        return base

    raw_targets = [(max(weight, 0) / total_weight) * troop_budget for weight in weights]
    allocation = [int(target) for target in raw_targets]
    remainder = troop_budget - sum(allocation)
    fractions = sorted(
        enumerate(raw_targets),
        key=lambda item: (item[1] - int(item[1]), item[1]),
        reverse=True,
    )
    for index in range(remainder):
        allocation[fractions[index % len(fractions)][0]] += 1
    return allocation


def heuristic_high_value_blotto(points, troop_budget):
    adjusted = [(point ** 2) for point in points]
    return allocate_proportionally(adjusted, troop_budget)


def approximate_blotto_equilibrium(points, troop_budget):
    return allocate_proportionally(points, troop_budget)


def blotto_nash_distance(allocation, points, troop_budget):
    normalized = normalize_blotto_allocation(allocation, troop_budget, len(points))
    if normalized is None:
        return None
    equilibrium = approximate_blotto_equilibrium(points, troop_budget)
    distance = sum(abs(a - b) for a, b in zip(normalized, equilibrium))
    max_distance = 2 * troop_budget if troop_budget > 0 else 1
    return {
        "equilibrium_allocation": equilibrium,
        "l1_distance": distance,
        "normalized_l1_distance": distance / max_distance,
    }


class BlottoEnvironment(GameEnvironment):
    def __init__(
        self,
        battlefields=3,
        troop_budget=100,
        point_range=(10, 50),
        fixed_points=None,
        point_policy="random_range",
        discrete=True,
        seed=None,
    ):
        super().__init__(seed=seed)
        self.battlefields = battlefields
        self.troop_budget = troop_budget
        self.point_range = tuple(point_range)
        self.fixed_points = list(fixed_points) if fixed_points is not None else None
        self.point_policy = "fixed" if self.fixed_points is not None and point_policy == "random_range" else point_policy
        self.discrete = discrete
        self.reset(seed=seed)

    def reset(self, seed=None):
        if seed is not None:
            self.reseed(seed)
        if self.point_policy == "fixed":
            if self.fixed_points is None:
                raise ValueError("fixed point policy requires fixed_points")
            self.points = list(self.fixed_points)
        else:
            low, high = self.point_range
            self.points = [self.rng.randint(low, high) for _ in range(self.battlefields)]
        self.actions = {}
        self.invalid_actions = {}
        self.scores = None
        self.winner = None
        return self.get_state()

    def validate_action(self, action):
        normalized = normalize_blotto_allocation(action, self.troop_budget, self.battlefields)
        if normalized is None:
            if not isinstance(action, list):
                return False, "allocation_not_list"
            if len(action) != self.battlefields:
                return False, "allocation_wrong_length"
            if any(not isinstance(value, int) for value in action):
                return False, "allocation_non_integer"
            if any(value < 0 for value in action):
                return False, "allocation_negative"
            return False, "allocation_wrong_sum"
        return True, None

    def get_state(self):
        zone_labels = [f"Zone {chr(ord('A') + index)}: {self.points[index]}" for index in range(self.battlefields)]
        return {
            "description": "Zone Point Values: " + ", ".join(zone_labels),
            "snapshot": self.serialize_state(),
        }

    def serialize_state(self):
        return {
            "points": list(self.points),
            "point_policy": self.point_policy,
            "troop_budget": self.troop_budget,
            "battlefields": self.battlefields,
            "discrete": self.discrete,
            "submitted_actions": {player: list(action) for player, action in self.actions.items()},
            "invalid_actions": dict(self.invalid_actions),
        }

    def get_valid_actions(self):
        return {
            "type": "allocation",
            "battlefields": self.battlefields,
            "troop_budget": self.troop_budget,
            "constraints": {
                "length": self.battlefields,
                "sum": self.troop_budget,
                "non_negative": True,
                "integer_only": True,
            },
            "discrete": self.discrete,
        }

    def apply_action(self, action, player=None):
        player_name = player or f"player_{len(self.actions) + 1}"
        is_valid, reason = self.validate_action(action)
        if not is_valid:
            self.invalid_actions[player_name] = reason
            return {"valid": False, "reason": reason}

        self.actions[player_name] = list(action)
        if len(self.actions) >= 2:
            players = list(self.actions.keys())[:2]
            self.scores = evaluate_blotto(self.actions[players[0]], self.actions[players[1]], self.points)
            if self.scores[0] > self.scores[1]:
                self.winner = players[0]
            elif self.scores[1] > self.scores[0]:
                self.winner = players[1]
            else:
                self.winner = "TIE"
        return {"valid": True, "reason": None}

    def is_terminal(self):
        return len(self.actions) >= 2

    def get_winner(self):
        return self.winner

    def get_metrics_context(self):
        return {
            "points": list(self.points),
            "scores": self.scores,
            "invalid_actions": dict(self.invalid_actions),
            "equilibrium_allocation": approximate_blotto_equilibrium(self.points, self.troop_budget),
            "nash_distance": {
                player: blotto_nash_distance(action, self.points, self.troop_budget)
                for player, action in self.actions.items()
            },
        }

    def sample_random_allocation(self):
        return get_random_blotto(self.troop_budget, self.battlefields, self.rng)

    def sample_uniform_allocation(self):
        return allocate_proportionally([1] * self.battlefields, self.troop_budget)

    def sample_high_value_targeting_allocation(self):
        return heuristic_high_value_blotto(self.points, self.troop_budget)

    def sample_nash_approx_allocation(self):
        return approximate_blotto_equilibrium(self.points, self.troop_budget)


def create_board(rows=6, cols=7):
    return [[0 for _ in range(cols)] for _ in range(rows)]


def get_valid_cols(board):
    return [column for column in range(len(board[0])) if board[0][column] == 0]


def print_board(board):
    symbols = {0: ".", 1: "X", 2: "O"}
    header = "Col: " + " ".join(str(column) for column in range(len(board[0])))
    rows = "\n".join("     " + " ".join(symbols[cell] for cell in row) for row in board)
    return header + "\n" + rows


def drop_piece(board, col, player):
    for row in range(len(board) - 1, -1, -1):
        if board[row][col] == 0:
            board[row][col] = player
            return True
    return False


def next_open_row(board, col):
    for row in range(len(board) - 1, -1, -1):
        if board[row][col] == 0:
            return row
    return None


def check_win(board, player, connect_length=4):
    rows = len(board)
    cols = len(board[0])

    for row in range(rows):
        for col in range(cols - connect_length + 1):
            if all(board[row][col + offset] == player for offset in range(connect_length)):
                return True
    for row in range(rows - connect_length + 1):
        for col in range(cols):
            if all(board[row + offset][col] == player for offset in range(connect_length)):
                return True
    for row in range(rows - connect_length + 1):
        for col in range(cols - connect_length + 1):
            if all(board[row + offset][col + offset] == player for offset in range(connect_length)):
                return True
            if all(board[row + connect_length - 1 - offset][col + offset] == player for offset in range(connect_length)):
                return True
    return False


def score_window(window, player, connect_length=4):
    opponent = 1 if player == 2 else 2
    player_count = window.count(player)
    opponent_count = window.count(opponent)
    empty_count = window.count(0)

    if player_count == connect_length:
        return 100000
    if opponent_count == connect_length:
        return -100000
    if player_count == connect_length - 1 and empty_count == 1:
        return 100
    if player_count == connect_length - 2 and empty_count == 2:
        return 10
    if opponent_count == connect_length - 1 and empty_count == 1:
        return -120
    if opponent_count == connect_length - 2 and empty_count == 2:
        return -12
    return 0


def evaluate_connect4_board(board, player, connect_length=4):
    opponent = 1 if player == 2 else 2
    rows = len(board)
    cols = len(board[0])
    score = 0

    center_col = cols // 2
    center_values = [board[row][center_col] for row in range(rows)]
    score += center_values.count(player) * 6
    score -= center_values.count(opponent) * 4

    for row in range(rows):
        for col in range(cols - connect_length + 1):
            score += score_window([board[row][col + offset] for offset in range(connect_length)], player, connect_length)

    for row in range(rows - connect_length + 1):
        for col in range(cols):
            score += score_window([board[row + offset][col] for offset in range(connect_length)], player, connect_length)

    for row in range(rows - connect_length + 1):
        for col in range(cols - connect_length + 1):
            score += score_window(
                [board[row + offset][col + offset] for offset in range(connect_length)],
                player,
                connect_length,
            )
            score += score_window(
                [board[row + connect_length - 1 - offset][col + offset] for offset in range(connect_length)],
                player,
                connect_length,
            )
    return score


class Connect4Environment(GameEnvironment):
    def __init__(self, rows=6, columns=7, connect_length=4, seed=None):
        super().__init__(seed=seed)
        self.rows = rows
        self.columns = columns
        self.connect_length = connect_length
        self.reset(seed=seed)

    def reset(self, seed=None):
        if seed is not None:
            self.reseed(seed)
        self.board = create_board(self.rows, self.columns)
        self.current_player = 1
        self.invalid_actions = []
        self.turn_history = []
        self.winner = None
        return self.get_state()

    def validate_action(self, action, player=None):
        if not isinstance(action, int):
            return False, "move_not_integer"
        if action < 0 or action >= self.columns:
            return False, "move_out_of_bounds"
        if action not in self.get_valid_actions():
            return False, "column_full"
        expected_player = player if player is not None else self.current_player
        if expected_player not in (1, 2):
            return False, "invalid_player"
        return True, None

    def get_state(self):
        valid_columns = self.get_valid_actions()
        description = (
            print_board(self.board)
            + "\nOrientation: rows are listed top to bottom; pieces fall to the lowest empty slot in the chosen column."
            + f"\nCurrent Player: {self.current_player}"
            + f"\nValid Columns to play: {valid_columns}"
        )
        return {
            "description": description,
            "snapshot": self.serialize_state(),
        }

    def serialize_state(self):
        return {
            "board": copy.deepcopy(self.board),
            "rows": self.rows,
            "columns": self.columns,
            "connect_length": self.connect_length,
            "current_player": self.current_player,
            "valid_columns": self.get_valid_actions(),
            "rendered_board": print_board(self.board),
            "winner": self.winner,
            "turn_history": copy.deepcopy(self.turn_history),
            "invalid_actions": copy.deepcopy(self.invalid_actions),
        }

    def get_valid_actions(self):
        return get_valid_cols(self.board)

    def apply_action(self, action, player=None):
        acting_player = player if player is not None else self.current_player
        is_valid, reason = self.validate_action(action, acting_player)
        if not is_valid:
            self.invalid_actions.append(
                {"player": acting_player, "action": action, "reason": reason}
            )
            return {"valid": False, "reason": reason}

        drop_piece(self.board, action, acting_player)
        self.turn_history.append({"player": acting_player, "action": action})
        if check_win(self.board, acting_player, self.connect_length):
            self.winner = acting_player
        elif not self.get_valid_actions():
            self.winner = "DRAW"
        else:
            self.current_player = 2 if acting_player == 1 else 1
        return {"valid": True, "reason": None}

    def is_terminal(self):
        return self.winner is not None

    def get_winner(self):
        return self.winner

    def get_metrics_context(self):
        return {
            "invalid_actions": copy.deepcopy(self.invalid_actions),
            "turn_count": len(self.turn_history),
            "valid_columns": self.get_valid_actions(),
        }


def minimax_solver(board, depth, alpha, beta, maximizing, connect_length=4, max_player=2, min_player=1):
    valid = get_valid_cols(board)
    if check_win(board, min_player, connect_length):
        return None, -100000
    if check_win(board, max_player, connect_length):
        return None, 100000
    if depth == 0 or not valid:
        return None, evaluate_connect4_board(board, max_player, connect_length)

    best_col = valid[0]
    if maximizing:
        value = -float("inf")
        for col in valid:
            temp = copy.deepcopy(board)
            drop_piece(temp, col, max_player)
            score = minimax_solver(
                temp, depth - 1, alpha, beta, False, connect_length, max_player, min_player
            )[1]
            if score > value:
                value, best_col = score, col
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return best_col, value

    value = float("inf")
    for col in valid:
        temp = copy.deepcopy(board)
        drop_piece(temp, col, min_player)
        score = minimax_solver(
            temp, depth - 1, alpha, beta, True, connect_length, max_player, min_player
        )[1]
        if score < value:
            value, best_col = score, col
        beta = min(beta, value)
        if alpha >= beta:
            break
    return best_col, value


def oracle_analysis(board, depth, connect_length=4, max_player=2, min_player=1):
    valid = get_valid_cols(board)
    move_scores = {}
    if not valid:
        return {
            "best_moves": [],
            "best_score": 0,
            "move_scores": move_scores,
        }

    for col in valid:
        temp = copy.deepcopy(board)
        drop_piece(temp, col, max_player)
        if check_win(temp, max_player, connect_length):
            move_scores[col] = 100000
            continue
        move_scores[col] = minimax_solver(
            temp,
            max(depth - 1, 0),
            -float("inf"),
            float("inf"),
            False,
            connect_length,
            max_player,
            min_player,
        )[1]

    best_score = max(move_scores.values())
    best_moves = sorted([move for move, score in move_scores.items() if score == best_score])
    return {
        "best_moves": best_moves,
        "best_score": best_score,
        "move_scores": move_scores,
    }
