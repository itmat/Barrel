from dataclasses import dataclass


@dataclass
class Infrastructure:
    pass


@dataclass
class Analysis:
    infrastructure: Infrastructure


@dataclass
class Configuration(Infrastructure):
    study: str = None
    analysis: str = None
