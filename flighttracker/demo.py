"""Recorded flights for --demo, so the project runs without a receiver, internet feed or hardware."""

from itertools import cycle

from .feed import Aircraft
from .lookup import Details

FLIGHTS: list[tuple[Aircraft, Details]] = [
    (
        Aircraft("400a1b", "BAW117", 51.52, -0.35, 9200, 310, 6.4, "B77W", "G-STBH"),
        Details("British Airways", "BAW", "LHR", "London Heathrow", "JFK", "John F Kennedy Intl", "Boeing 777 36NER", destination_lat=40.6398, destination_lon=-73.7789),
    ),
    (
        Aircraft("406b2c", "EZY8421", 51.61, -0.18, 4300, 190, 11.8, "A320", "G-UZHA"),
        Details("easyJet", "EZY", "LGW", "London Gatwick", "EDI", "Edinburgh", "Airbus A320 214", destination_lat=55.95, destination_lon=-3.3725),
    ),
    (
        Aircraft("4ca2d1", "RYR6AK", 51.44, -0.02, 6100, 250, 9.1, "B738", "EI-FZA"),
        Details("Ryanair", "RYR", "STN", "London Stansted", "DUB", "Dublin", "Boeing 737 8AS", destination_lat=53.4213, destination_lon=-6.2701),
    ),
    (
        Aircraft("484c3e", "KLM1000", 51.58, 0.04, 11800, 380, 14.3, "E190", "PH-EZA"),
        Details("KLM Royal Dutch Airlines", "KLM", "AMS", "Amsterdam Schiphol", "LCY", "London City", "Embraer ERJ 190STD", destination_lat=51.5053, destination_lon=0.0553),
    ),
    (
        Aircraft("896194", "UAE7", 51.49, -0.28, 14500, 450, 4.7, "A388", "A6-EOB"),
        Details("Emirates", "UAE", "DXB", "Dubai Intl", "LHR", "London Heathrow", "Airbus A380 861", destination_lat=51.4706, destination_lon=-0.4619),
    ),
]


def flights():
    """Endless cycle of (aircraft, details), one per display update."""
    return cycle(FLIGHTS)
