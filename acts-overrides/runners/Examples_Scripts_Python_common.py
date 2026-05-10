# Shared argparse + parameter-override helpers for the runner scripts.

import argparse
from enum import Enum

import yaml

import acts
import acts.examples


class AlgorithmChoice(Enum):
    Default = "Default"
    GridTriplet = "GridTriplet"
    SphericalGridTriplet = "SphericalGridTriplet"


class EnumAction(argparse.Action):
    def __init__(self, **kwargs):
        enum_type = kwargs.pop("enum", None)
        if enum_type is None:
            raise ValueError("enum must be assigned when using EnumAction")
        if not issubclass(enum_type, Enum):
            raise TypeError("enum must be an Enum when using EnumAction")
        kwargs.setdefault("choices", tuple(e.name for e in enum_type))
        super().__init__(**kwargs)
        self._enum = enum_type

    def __call__(self, parser, namespace, values, option_string=None):
        for e in self._enum:
            if e.name == values:
                setattr(namespace, self.dest, e)
                return
        raise ValueError(f"{values} is not a valid enum value.")


_LOG_LEVELS = {
    1: acts.logging.INFO,
    2: acts.logging.DEBUG,
    3: acts.logging.VERBOSE,
}


def log_level(level_int: int):
    return _LOG_LEVELS.get(level_int, acts.logging.INFO)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version",
        action=EnumAction,
        enum=AlgorithmChoice,
        default=AlgorithmChoice.Default,
        help="Seeding algorithm to use",
    )
    parser.add_argument("--events", type=int, default=50, help="Number of events")
    parser.add_argument("--threads", type=int, default=1, help="Number of threads")
    parser.add_argument(
        "--logging-level",
        type=int,
        default=1,
        help="1=INFO, 2=DEBUG, 3=VERBOSE",
    )
    parser.add_argument(
        "--parameters",
        type=str,
        default="",
        help='SphericalGridTriplet parameter overrides, e.g. --parameters "deltaEtaMax=0.25, etaMin=-4"',
    )


def _split_top_level_commas(text: str) -> list[str]:
    # Splits on commas only outside brackets/braces/parens/quotes.
    parts: list[str] = []
    current: list[str] = []
    depth_square = depth_curly = depth_round = 0
    in_single = in_double = escape = False
    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if ch == "[":
                depth_square += 1
            elif ch == "]":
                depth_square -= 1
            elif ch == "{":
                depth_curly += 1
            elif ch == "}":
                depth_curly -= 1
            elif ch == "(":
                depth_round += 1
            elif ch == ")":
                depth_round -= 1
            elif ch == "," and depth_square == depth_curly == depth_round == 0:
                piece = "".join(current).strip()
                if piece:
                    parts.append(piece)
                current = []
                continue
        current.append(ch)
    piece = "".join(current).strip()
    if piece:
        parts.append(piece)
    return parts


def parse_parameters(param_string: str) -> dict:
    # yaml.safe_load on each value so ints/floats/lists round-trip cleanly.
    if not param_string.strip():
        return {}
    params: dict = {}
    for item in _split_top_level_commas(param_string):
        if "=" not in item:
            raise ValueError(f"Invalid parameter '{item}'. Expected format key=value.")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        try:
            params[key] = yaml.safe_load(value)
        except Exception:
            params[key] = value
    return params


def override_namedtuple(nt, overrides: dict):
    # Only applies overrides whose keys exist as fields on the namedtuple.
    valid_fields = getattr(nt, "_fields", ())
    updates = {k: v for k, v in overrides.items() if k in valid_fields}
    return nt._replace(**updates) if updates else nt


def apply_eta_overrides(seed_finder_config, overrides: dict):
    if "etaMin" in overrides or "etaMax" in overrides:
        current = seed_finder_config.eta
        return seed_finder_config._replace(
            eta=(
                overrides.pop("etaMin", current[0]),
                overrides.pop("etaMax", current[1]),
            )
        )
    overrides.pop("etaMin", None)
    overrides.pop("etaMax", None)
    return seed_finder_config

