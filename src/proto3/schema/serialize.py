"""Serialization helpers: to_dict, from_dict, to_json, from_json (S02-D3).

Free functions, not methods (SRP — dataclass = data, helper = policy).
Single place that handles custom types as they are introduced
(Polygon/Enum/datetime/numpy etc.).

Backward-compat: from_dict treats missing keys as default (S02-D4 extension policy).

Populated in P5 #4 (4.4).
"""
