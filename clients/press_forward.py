import logging
import sys

from tminterface.interface import TMInterface
from tminterface.client import Client
from tminterface.constants import BINARY_ACCELERATE_NAME

class PressForwardClient(Client):
    def __init__(self, **kwargs) -> None:
        if "start_time" in kwargs:
            self.start_time = kwargs["start_time"]
        else:
            self.start_time = 0

        if "max_length" in kwargs:
            self.max_length = kwargs["max_length"]
        else:
            self.max_length = 120000

        if "num_clients" in kwargs:
            self.num_clients = kwargs["num_clients"]
        else:
            self.num_clients = 1

        if "client_num" in kwargs:
            self.client_num = kwargs["client_num"]
        else:
            self.client_num = 0

        if "extra_time" in kwargs:
            self.extra_time = kwargs["extra_time"]
        else:
            self.extra_time = 0

        if "goals" in kwargs:
            self.goals = kwargs["goals"]
        else:
            self.goals = []

        if "restarts" in kwargs:
            self.restarts = kwargs["restarts"]
        else:
            self.restarts = []

        if "check_frequency" in kwargs:
            self.check_frequency = kwargs["check_frequency"]
        else:
            self.check_frequency = 100

        if "client_name" in kwargs:
            self.client_name = kwargs["client_name"]
        else:
            self.client_name = "PressForwardClient"

        logger = logging.getLogger(self.client_name)
        
        file_handler = logging.FileHandler(filename=self.client_name)
        file_formatter = logging.Formatter("[%(levelname)s][%(asctime)s][%(filename)s, %(funcName)s, %(lineno)d] %(message)s")
        file_handler.setFormatter(file_formatter)
        
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_formatter = logging.Formatter("%(message)s")
        stdout_handler.setFormatter(stdout_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stdout_handler)
        logger.setLevel(logging.DEBUG)

        self.logger = logger
        self.log = self.logger.info

    def on_registered(self, iface: TMInterface) -> None:
        self.log(f"[{self.client_name}] Connected to {iface.server_name}")

    def on_simulation_begin(self, iface: TMInterface):
        iface.remove_state_validation()

        events = iface.get_event_buffer()
        events.clear()
        iface.set_event_buffer(events)

        self.iter = 0
        self.goals_achieved = [False] * len(self.goals)
        self.best_time = 10**10
        self.iter_start_time = self.start_time + 10 * (self.num_clients * self.iter + self.client_num)
        self.max_iter_length = self.max_length + self.iter_start_time
        iface.set_simulation_time_limit(self.max_iter_length)

    def on_simulation_step(self, iface: TMInterface, t: int):
        if t == self.iter_start_time - 20:
            self.start_state = iface.get_simulation_state()

        if t == self.max_iter_length:
            self.next_iter(iface)

        if (len(self.goals) > 0 or len(self.restarts) > 0) and t % self.check_frequency == 0:
            state = iface.get_simulation_state()

            for (i, g) in enumerate(self.goals):
                if g(state) and not self.goals[i]:
                    self.log(f"[{self.client_name}] Reached goal {i+1} at time = {t}")
                    self.goals[i] = True
                    self.max_iter_length += self.extra_time 
                    iface.set_simulation_time_limit(self.max_iter_length)

            for r in self.restarts:
                if r(state):
                    self.next_iter(iface)

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        iface.prevent_simulation_finish()
        t = iface.get_simulation_state().race_time

        self.log(f"[{self.client_name}] Reached checkpoint {current}/{target} at time = {t}")
        self.max_iter_length += self.extra_time
        iface.set_simulation_time_limit(self.max_iter_length)
        
        if current == target and t < self.best_time:
            self.log(f"[{self.client_name}] New best finish time: {t} (previous best: {self.best_time})")
            self.best_time = t

    def next_input_sequence(self, iface: TMInterface):
        events = iface.get_event_buffer()
        events.clear()
        events.add(self.iter_start_time, BINARY_ACCELERATE_NAME, True)
        iface.set_event_buffer(events)

        self.log(f"[{self.client_name}] Next input sequence:")
        self.log(events.to_commands_str())

    def next_iter(self, iface: TMInterface):
        self.iter += 1
        self.iter_start_time = self.start_time + 10 * (self.num_clients * self.iter + self.client_num)
        self.max_iter_length = self.max_length + self.iter_start_time
        self.goals_reached = [False] * len(self.goals)

        self.next_input_sequence(iface)
        iface.rewind_to_state(self.start_state)
        iface.set_simulation_time_limit(self.max_iter_length)
