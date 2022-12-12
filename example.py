import sys

from tminterface.client import run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME

from low_input import LowInputClient

n = int(sys.argv[1])

run_client(
    LowInputClient(
        inputs=[
            # 0 press up
            {"time": [0], "type": BINARY_ACCELERATE_NAME, "value": [True]},
            # [0 to 2000] steer [20000 to 25000]
            {"time": range(0, 2000, 10), "type": ANALOG_STEER_NAME, "value": range(20000, 25000, 1)},
        ],
        # Wait [0 to 200] before the first input
        waiting_time=range(0, 200, 10),
        # Simulate for 5s after the first non-constant input
        max_length=5000,
        # Number of TMI instances that will be used
        num_clients=1,
        # Server number (e.g. 0 for TMInterface0)
        client_num=n,
        # Choose inputs randomly, or exhaustively check every combination?
        random=True,
        # Extra time added to max_length when a checkpoint or goal is reached
        extra_time=10000,
        # List of goals (triggers)
        goals=[
            # Maybe some hard-to-reach position on the track
            lambda a: a.position[0] < 300 and a.position[2] > 500,
        ],
        # List of triggers that will cause the iteration to end early
        restarts=[
            # Fell into water
            lambda a: a.position[1] < 9
        ],
        # How often are goal and restarts checked?
        check_frequency=500,
        # Must the goals be completed in order?
        ordered_goals=False,
    ),

    server_name=f"TMInterface{n}"
)
