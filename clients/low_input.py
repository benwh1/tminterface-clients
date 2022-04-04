import itertools
import random
import logging
import sys

from tminterface.interface import TMInterface
from tminterface.client import Client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME

def _flatten(data):
    if isinstance(data, tuple):
        if len(data) == 0:
            return ()
        else:
            return _flatten(data[0]) + _flatten(data[1:])
    else:
        return (data,)

class LowInputClient(Client):
    def __init__(self, inputs, **kwargs) -> None:
        self.inputs = inputs

        if "initial_inputs" in kwargs:
            self.initial_inputs = kwargs["initial_inputs"]
        else:
            self.initial_inputs = []

        if "start_iter" in kwargs:
            self.start_iter = kwargs["start_iter"]
        else:
            self.start_iter = 0

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

        if "random" in kwargs:
            self.random = kwargs["random"]
        else:
            self.random = False

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
            self.client_name = "LowInputClient"

        self.earliest_input_time = min([x["time"].start for x in inputs])

        logger = logging.getLogger(self.client_name)

        file_handler = logging.FileHandler(filename=f"{self.client_name}.txt")
        file_formatter = logging.Formatter(f"[%(levelname)s][%(asctime)s][%(filename)s, %(funcName)s, %(lineno)d][{self.client_name}] %(message)s")
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
        self.log(f"Connected to {iface.server_name}")

    def on_simulation_begin(self, iface: TMInterface):
        iface.remove_state_validation()

        events = iface.get_event_buffer()
        events.clear()
        events.add(0, BINARY_ACCELERATE_NAME, True)
        for (time, input_type, value) in self.initial_inputs:
            events.add(time, input_type, value)
        iface.set_event_buffer(events)

        if not self.random:
            self.input_iter = itertools.product()
            for i in self.inputs:
                self.input_iter = itertools.product(self.input_iter, i["steer"], i["time"])
            for i in range(self.start_iter):
                next(self.input_iter)
            for i in range(self.client_num):
                next(self.input_iter)

        self.initial_events = events
        self.iter = self.start_iter
        self.goals_reached = [False] * len(self.goals)
        self.best_time = 10**10
        self.max_iter_length = self.max_length
        self.doing_start = True

        iface.set_simulation_time_limit(self.max_iter_length)

    def on_simulation_step(self, iface: TMInterface, t: int):
        if t == self.earliest_input_time - 20 and self.doing_start:
            self.start_state = iface.get_simulation_state()
            self.doing_start = False

        if t == self.max_iter_length:
            self.next_iter(iface)

        if (len(self.goals) > 0 or len(self.restarts) > 0) and t % self.check_frequency == 0:
            state = iface.get_simulation_state()

            for (i, g) in enumerate(self.goals):
                if g(state) and not self.goals_reached[i]:
                    self.log(f"Reached goal {i+1} at time = {t}")
                    self.goals_reached[i] = True
                    self.max_iter_length += self.extra_time
                    iface.set_simulation_time_limit(self.max_iter_length)

            for r in self.restarts:
                if r(state):
                    self.next_iter(iface)

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        iface.prevent_simulation_finish()
        t = iface.get_simulation_state().race_time

        self.log(f"Reached checkpoint {current}/{target} at time = {t}")
        self.max_iter_length += self.extra_time
        iface.set_simulation_time_limit(self.max_iter_length)

        if current == target and t < self.best_time:
            self.log(f"New best finish time: {t} (previous best: {self.best_time})")
            self.best_time = t

    def next_input_sequence(self, iface: TMInterface):
        if self.random:
            steer = [random.randrange(i["steer"].start, i["steer"].stop, i["steer"].step) for i in self.inputs]
            time = [random.randrange(i["time"].start, i["time"].stop, i["time"].step) for i in self.inputs]
        else:
            for i in range(self.num_clients-1):
                next(self.input_iter)
            next_seq = list(_flatten(next(self.input_iter)))
            steer = next_seq[0::2]
            time = next_seq[1::2]

        events = self.initial_events.copy()
        for i in range(len(steer)):
            events.add(time[i], ANALOG_STEER_NAME, steer[i])
        iface.set_event_buffer(events)

        self.log(f"Next input sequence:")
        self.log(events.to_commands_str())

    def next_iter(self, iface: TMInterface):
        self.iter += 1
        self.max_iter_length = self.max_length
        self.goals_reached = [False] * len(self.goals)

        self.next_input_sequence(iface)
        iface.rewind_to_state(self.start_state)
        iface.set_simulation_time_limit(self.max_iter_length)
