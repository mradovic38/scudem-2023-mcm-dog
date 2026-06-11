import math

from constants import RHO

OBJECTS = {
    "ball": {
        "mass_kg": 0.058,               # 58 grams
        "area_m2": math.pi * 0.033**2,  # 3.3 cm radius
        "c_d": 0.5,                     # sphere with fuzz
    },
    "sausage": {
        "mass_kg": 0.100,               # 100 grams
        "area_m2": 0.15 * 0.03,         # 15 cm long, 3 cm thick (thrown sideways)
        "c_d": 0.82,                    # cylinder in cross-flow
    },
    "pizza": {
        "mass_kg": 0.140,               # medium personal pizza
        "area_m2": 0.5 * 0.15 * 0.20,   # tumbling face-on
        "c_d": 1.12,                    # flat circular plate
    },
    "taco": {
        "mass_kg": 0.150,               # 150 grams
        "area_m2": 0.15 * 0.06,         # 15 cm long, 6 cm high
        "c_d": 1.0,                     # irregular open-cup shape
    },
    "steak": {
        "mass_kg": 0.300,               # 300 gram ribeye
        "area_m2": 0.20 * 0.10,         # 20 cm x 10 cm
        "c_d": 1.0,                     # flat rough slab
    },
    "fry": {
        "mass_kg": 0.003,
        "area_m2": 0.07 * 0.006,
        "c_d": 2.0,
    },
}


def simulated_drag(props):
    """Simplified drag term (c_d * rho * area) / (2 * mass) for one object."""
    return (props["c_d"] * RHO * props["area_m2"]) / (2 * props["mass_kg"])


# Drag coefficients used by the simulation, derived from the object properties.
DRAG_COEFFS = {name: simulated_drag(props) for name, props in OBJECTS.items()}


def print_drag_table():
    """Print the simulated drag coefficient for every defined object."""
    print("Real-life simulated drag coefficients:")
    print("-" * 50)
    for name, props in OBJECTS.items():
        print(
            f"{name.capitalize():<15} : {DRAG_COEFFS[name]:.4f}  "
            f"(Mass: {props['mass_kg']:>5}kg, Area: {props['area_m2']:.4f}m\u00b2)"
        )
