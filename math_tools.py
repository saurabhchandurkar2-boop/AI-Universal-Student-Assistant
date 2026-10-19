"""
Exact maths for the assistant (no AI model involved).

Small language models often get arithmetic wrong, so numbers are computed here
with plain Python instead:

  safe_eval(expr, variables)      evaluate an expression safely
  try_chat_calculation(message)   answer a chat message that is just a calculation
  FORMULAS / solve(...)           formula library: pick the unknown, get the value
                                  and the working
"""
import ast
import math
import operator
import re

# --------------------------------------------------------------------------
# Safe expression evaluator (no eval(), only whitelisted syntax)
# --------------------------------------------------------------------------

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sind": lambda x: math.sin(math.radians(x)),
    "cosd": lambda x: math.cos(math.radians(x)),
    "tand": lambda x: math.tan(math.radians(x)),
    "log": math.log10,
    "log10": math.log10,
    "ln": math.log,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "factorial": lambda x: math.factorial(int(x)),
    "radians": math.radians,
    "degrees": math.degrees,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}

_MAX_EXPONENT = 1000
_MAX_FACTORIAL = 170


def _normalize(expr: str) -> str:
    expr = expr.strip()
    for old, new in (
        ("×", "*"), ("÷", "/"), ("−", "-"), ("–", "-"),
        ("²", "**2"), ("³", "**3"), ("√", "sqrt"), ("π", "pi"),
        ("^", "**"),
    ):
        expr = expr.replace(old, new)
    # 1,000.5 -> 1000.5 (thousands separators)
    expr = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", expr)
    # sqrt 16 -> sqrt(16)
    expr = re.sub(r"\bsqrt\s+(\d+(?:\.\d+)?)", r"sqrt(\1)", expr)
    # 20% of 150 -> (20/100)*150
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*of\s*", r"(\1/100)*", expr, flags=re.IGNORECASE)
    # 20% -> (20/100)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", expr)
    return expr


def _eval_node(node, variables):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Only numbers are allowed.")

    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise ValueError(f"Unknown name: {node.id}")

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand, variables))

    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError("Exponent is too large.")
        return _BIN_OPS[type(node.op)](left, right)

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name not in _FUNCTIONS or node.keywords:
            raise ValueError(f"Unknown function: {name}")
        args = [_eval_node(a, variables) for a in node.args]
        if name == "factorial" and args and args[0] > _MAX_FACTORIAL:
            raise ValueError("Number is too large for factorial.")
        return _FUNCTIONS[name](*args)

    raise ValueError("This expression is not supported.")


def safe_eval(expr: str, variables: dict = None) -> float:
    """Evaluate a maths expression. Raises ValueError with a clear message."""
    variables = variables or {}
    try:
        tree = ast.parse(_normalize(expr), mode="eval")
    except SyntaxError:
        raise ValueError("Could not read this expression.")
    try:
        return _eval_node(tree, variables)
    except ZeroDivisionError:
        raise ValueError("Division by zero.")
    except OverflowError:
        raise ValueError("The result is too large.")
    except ValueError as error:
        if "math domain error" in str(error):
            raise ValueError("No real answer (maths domain error).")
        raise
    except (TypeError, ArithmeticError) as error:
        raise ValueError(f"Could not calculate this: {error}")


def format_number(value) -> str:
    """Readable number: up to 10 significant digits, no trailing zeros."""
    if isinstance(value, complex):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if value == 0:
        return "0"
    if abs(value) >= 1e12 or abs(value) < 1e-6:
        return f"{value:.6e}"
    text = f"{value:.10g}"
    return text


# --------------------------------------------------------------------------
# Chat shortcut
# --------------------------------------------------------------------------

_PREFIX = re.compile(
    r"^\s*(?:please\s+)?(?:calculate|calc|compute|evaluate|solve|find|"
    r"what\s+is|what's|whats)\s*[:\-]?\s*",
    re.IGNORECASE,
)
_ALLOWED_CHARS = re.compile(r"^[0-9a-zA-Zπ√+\-−–*/^%().,×÷²³\s]+$")


def try_chat_calculation(message: str):
    """If the message is just a calculation, return the answer text, else None."""
    if not message or len(message) > 200:
        return None

    text = _PREFIX.sub("", message).strip().rstrip("?=. ").strip()
    if not text or not _ALLOWED_CHARS.match(text):
        return None
    if not re.search(r"\d", text):
        return None
    # A lone number is not a calculation.
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
        return None
    if not re.search(r"[-+*/^%×÷²³√]|\w\(", text):
        return None

    try:
        result = safe_eval(text)
    except ValueError as error:
        if str(error).startswith("Division by zero"):
            return f"`{text}` is undefined, because it divides by zero."
        return None
    if isinstance(result, complex):
        return None

    reply = f"`{text}` = **{format_number(result)}**\n\nCalculated exactly by the built-in calculator."
    if re.search(r"\b(sin|cos|tan)\(", text):
        reply += " Angles are in radians. Use sind, cosd or tand for degrees."
    return reply


# --------------------------------------------------------------------------
# Formula library
# --------------------------------------------------------------------------
# Each formula lists its variables and, for each variable, an expression that
# solves for it using the other variables.

FORMULAS = {
    "ohms_law": {
        "name": "Ohm's law",
        "equation": "V = I × R",
        "vars": {"V": "Voltage (volts)", "I": "Current (amperes)", "R": "Resistance (ohms)"},
        "solve": {"V": "I*R", "I": "V/R", "R": "V/I"},
    },
    "electric_power": {
        "name": "Electric power",
        "equation": "P = V × I",
        "vars": {"P": "Power (watts)", "V": "Voltage (volts)", "I": "Current (amperes)"},
        "solve": {"P": "V*I", "V": "P/I", "I": "P/V"},
    },
    "newton_second": {
        "name": "Newton's second law",
        "equation": "F = m × a",
        "vars": {"F": "Force (newtons)", "m": "Mass (kg)", "a": "Acceleration (m/s²)"},
        "solve": {"F": "m*a", "m": "F/a", "a": "F/m"},
    },
    "speed": {
        "name": "Speed, distance and time",
        "equation": "v = d / t",
        "vars": {"v": "Speed (m/s)", "d": "Distance (m)", "t": "Time (s)"},
        "solve": {"v": "d/t", "d": "v*t", "t": "d/v"},
    },
    "kinematics_v": {
        "name": "Final velocity",
        "equation": "v = u + a × t",
        "vars": {"v": "Final velocity (m/s)", "u": "Initial velocity (m/s)",
                 "a": "Acceleration (m/s²)", "t": "Time (s)"},
        "solve": {"v": "u+a*t", "u": "v-a*t", "a": "(v-u)/t", "t": "(v-u)/a"},
    },
    "kinematics_s": {
        "name": "Displacement",
        "equation": "s = u × t + ½ × a × t²",
        "vars": {"s": "Displacement (m)", "u": "Initial velocity (m/s)",
                 "a": "Acceleration (m/s²)", "t": "Time (s)"},
        "solve": {"s": "u*t+0.5*a*t**2", "u": "(s-0.5*a*t**2)/t", "a": "2*(s-u*t)/t**2"},
    },
    "kinematics_v2": {
        "name": "Velocity from displacement",
        "equation": "v² = u² + 2 × a × s",
        "vars": {"v": "Final velocity (m/s)", "u": "Initial velocity (m/s)",
                 "a": "Acceleration (m/s²)", "s": "Displacement (m)"},
        "solve": {"v": "sqrt(u**2+2*a*s)", "u": "sqrt(v**2-2*a*s)",
                  "a": "(v**2-u**2)/(2*s)", "s": "(v**2-u**2)/(2*a)"},
    },
    "work": {
        "name": "Work done",
        "equation": "W = F × d",
        "vars": {"W": "Work (joules)", "F": "Force (newtons)", "d": "Distance (m)"},
        "solve": {"W": "F*d", "F": "W/d", "d": "W/F"},
    },
    "kinetic_energy": {
        "name": "Kinetic energy",
        "equation": "KE = ½ × m × v²",
        "vars": {"KE": "Kinetic energy (joules)", "m": "Mass (kg)", "v": "Speed (m/s)"},
        "solve": {"KE": "0.5*m*v**2", "m": "2*KE/v**2", "v": "sqrt(2*KE/m)"},
    },
    "potential_energy": {
        "name": "Potential energy",
        "equation": "PE = m × g × h",
        "vars": {"PE": "Potential energy (joules)", "m": "Mass (kg)",
                 "g": "Gravity (m/s²)", "h": "Height (m)"},
        "defaults": {"g": 9.81},
        "solve": {"PE": "m*g*h", "m": "PE/(g*h)", "h": "PE/(m*g)", "g": "PE/(m*h)"},
    },
    "density": {
        "name": "Density",
        "equation": "ρ = m / V",
        "vars": {"rho": "Density (kg/m³)", "m": "Mass (kg)", "V": "Volume (m³)"},
        "solve": {"rho": "m/V", "m": "rho*V", "V": "m/rho"},
    },
    "pythagoras": {
        "name": "Pythagoras theorem",
        "equation": "c² = a² + b²",
        "vars": {"a": "Side a", "b": "Side b", "c": "Hypotenuse c"},
        "solve": {"c": "sqrt(a**2+b**2)", "a": "sqrt(c**2-b**2)", "b": "sqrt(c**2-a**2)"},
    },
    "circle_area": {
        "name": "Area of a circle",
        "equation": "A = π × r²",
        "vars": {"A": "Area", "r": "Radius"},
        "solve": {"A": "pi*r**2", "r": "sqrt(A/pi)"},
    },
    "simple_interest": {
        "name": "Simple interest",
        "equation": "SI = P × r × t / 100",
        "vars": {"SI": "Interest", "P": "Principal", "r": "Rate (% per year)", "t": "Time (years)"},
        "solve": {"SI": "P*r*t/100", "P": "SI*100/(r*t)", "r": "SI*100/(P*t)", "t": "SI*100/(P*r)"},
    },
    "compound_interest": {
        "name": "Compound interest",
        "equation": "A = P × (1 + r/100)ⁿ",
        "vars": {"A": "Final amount", "P": "Principal", "r": "Rate (% per period)", "n": "Number of periods"},
        "solve": {"A": "P*(1+r/100)**n", "P": "A/(1+r/100)**n",
                  "n": "ln(A/P)/ln(1+r/100)", "r": "((A/P)**(1/n)-1)*100"},
    },
    "percentage": {
        "name": "Percentage of marks",
        "equation": "percentage = obtained / total × 100",
        "vars": {"percentage": "Percentage (%)", "obtained": "Marks obtained", "total": "Total marks"},
        "solve": {"percentage": "obtained/total*100", "obtained": "percentage*total/100",
                  "total": "obtained*100/percentage"},
    },
}


def _substitute(expr: str, values: dict) -> str:
    def repl(match):
        name = match.group(0)
        if name in values:
            v = format_number(values[name])
            return f"({v})" if v.startswith("-") else v
        return name

    return re.sub(r"[A-Za-z_]\w*", repl, expr)


def solve(formula_key: str, solve_for: str, values: dict) -> dict:
    """Solve a library formula for one variable.

    values: numbers for every other variable.
    Returns {"value": float, "working": [str, ...]} or raises ValueError.
    """
    formula = FORMULAS[formula_key]
    if solve_for not in formula["solve"]:
        raise ValueError(f"This formula cannot solve for {solve_for}.")

    expr = formula["solve"][solve_for]
    needed = [v for v in formula["vars"] if v != solve_for and re.search(rf"\b{v}\b", expr)]
    missing = [v for v in needed if values.get(v) is None]
    if missing:
        raise ValueError("Enter a value for: " + ", ".join(missing))

    numbers = {v: float(values[v]) for v in needed}
    try:
        result = safe_eval(expr, numbers)
    except ValueError as error:
        raise ValueError(f"{error} Check the values you entered.")
    if isinstance(result, complex) or (isinstance(result, float) and math.isnan(result)):
        raise ValueError("No real answer for these values. Check the values you entered.")

    working = [
        f"Formula: {formula['equation']}",
        f"Solve for {solve_for}: {solve_for} = {expr}",
        f"Substitute: {solve_for} = {_substitute(expr, numbers)}",
        f"Answer: {solve_for} = {format_number(result)}",
    ]
    return {"value": result, "working": working}
