"""
config.py — Configurable parameters for the Pesaje engine.
No dependency on models. Pure data.
"""
from dataclasses import dataclass, field
import json
import os


@dataclass
class PesajeConfig:
    match_tolerance: float = 30.0       # max weight diff to consider same physical can
    negative_tolerance: float = 100.0   # max acceptable negative sold (noise)
    decay_rate: float = 0.3             # confidence decay: 1/(1 + rate*distance)
    min_history: int = 3                # min shifts of history before inference activates
    max_history_window: int = 14        # max shifts to look back
    tara_range: tuple = (200, 600)      # empty can weight range (weak factor)
    vdp_table: dict = field(default_factory=lambda: {
        "KILO": 1000, "1/2": 500, "1/4": 250,
    })

    @staticmethod
    def default():
        return PesajeConfig()

    @staticmethod
    def load(path: str):
        if not path or not os.path.exists(path):
            return PesajeConfig.default()
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return PesajeConfig(**{k: v for k, v in data.items()
                               if k in PesajeConfig.__dataclass_fields__})
