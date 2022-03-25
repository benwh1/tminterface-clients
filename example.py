import sys
from tminterface.client import run_client
from clients.press_forward import PressForwardClient

n = sys.argv[1]

run_client(
    PressForwardClient(
        start_time=0,
        max_length=90000,
        num_clients=4,
        client_num=n,
        goals=[
            # Some part of the map which is difficult to reach
            lambda a: 500 < a.position[0] < 550
        ],
        extra_time=60000,
        restarts=[
            # Fell into water
            lambda a: a.position[1] < 9
        ],
        check_frequency=100,
        client_name=f"PressForwardClient{n}"
    ),
    server_name=f"TMInterface{n}"
)
