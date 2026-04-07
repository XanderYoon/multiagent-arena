from agents import call_llm, extract_json
from collections import Counter

SYS = """You are a highly logical, strict Game Theory AI. 
CRITICAL RULES:
1. You MUST output ONLY valid JSON format. No conversational text.
2. For Gravity Grid: 'move' MUST be a single integer from the valid columns list.
3. For Simultaneous Resource Game: 'move' MUST be a list of exactly 3 integers.
4. MATH CHECK: In the Resource Game, your 3 integers MUST sum to EXACTLY 100. If they equal 99 or 101, you are terminated.
Format: {"reasoning": "string", "move": int_or_list}"""


def run_single_agent(rules, state):
    out = extract_json(call_llm(SYS, f"Rules: {rules}\nState: {state}"))
    return out if out else {"move": None}, ["Single Call"]


def run_parallel_agent(rules, state):
    moves = []
    for _ in range(3):
        data = extract_json(call_llm(SYS, f"Rules: {rules}\nState: {state}"))
        if data and "move" in data:
            moves.append(tuple(data['move']) if isinstance(
                data['move'], list) else data['move'])
    if not moves:
        return {"move": None}, ["All Failed"]
    best = Counter(moves).most_common(1)[0][0]
    return {"move": list(best) if isinstance(best, tuple) else best}, [f"Votes: {moves}"]


def run_hierarchical_agent(rules, state):
    # 1. Reasoner
    r_out = extract_json(call_llm(
        SYS + " You are the Reasoner. Draft the initial strategy for our team to win.", f"Rules: {rules}\nState: {state}"))

    # 2. Critic
    c_prompt = f"Rules: {rules}\nState: {state}\nReasoner suggested: {r_out}\nCritique this move. Is the math correct? Is it a legal move? Suggest improvements."
    c_out = extract_json(call_llm(SYS + " You are the Critic.", c_prompt))

    # 3. Manager
    m_prompt = (f"Rules: {rules}\nState: {state}\n"
                f"Reasoner's proposal: {r_out}\nCritic's feedback: {c_out}\n"
                f"You are the Impartial Executive Auditor. Both the Reasoner and the Critic can make strategic mistakes or break fundamental game rules (e.g., math summation errors or choosing full/invalid columns). "
                f"Your task is to independently verify the rules and the board state. "
                f"You may adopt the Reasoner's move, the Critic's move, or synthesize a completely new optimal move yourself if both are flawed. "
                f"Make the final, rule-compliant decision for our team to win.")

    f_out = extract_json(
        call_llm(SYS + " You are the Executive Auditor.", m_prompt))

    return f_out if f_out else {"move": None}, [str(r_out), str(c_out), str(f_out)]
