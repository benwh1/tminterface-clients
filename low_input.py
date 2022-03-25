import itertools
import random
import logging
import sys

from tminterface.interface import TMInterface
from tminterface.client import Client
from tminterface.constants import ANALOG_STEER_NAME

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
            self.start_iter = []

        if "max_length" in kwargs:
            self.max_length = kwargs["max_length"]
        else:
            self.max_length = 120000

        # Arithmetic progression of inputs. (a,b) searches every a'th input starting from b
        # e.g. use (1,0) for all possible inputs, or (2,0) and (2,1) for all inputs across two clients.
        if "ap" in kwargs:
            self.ap = kwargs["ap"]
        else:
            self.ap = (1,0)

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

        if "name" in kwargs:
            self.name = kwargs["name"]
        else:
            self.name = "LowInputClient"

        self.earliest_input_time = min(inputs, key=lambda x: x["time"][0])

        logger = logging.getLogger(self.name)

        file_handler = logging.FileHandler(filename=self.name)
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
        self.log(f"[{self.name}] Connected to {iface.server_name}")

    def on_simulation_begin(self, iface: TMInterface):
        iface.remove_state_validation()

        events = iface.get_event_buffer()
        events.clear()
        for (time, input_type, value) in self.initial_inputs:
            events.add(time, input_type, value)
        iface.set_event_buffer(events)

        if not self.random:
            self.input_iter = itertools.product()
            for i in self.inputs:
                self.input_iter = itertools.product(self.input_iter, i["steer"], i["time"])
            for i in range(self.start_iter):
                next(self.input_iter)

        self.initial_events = events
        self.goals_achieved = [False] * len(self.goals)
        self.iter = self.start_iter
        self.best_time = 10**10
        self.doing_start = True
        self.max_iter_length = self.max_length + 10 * (self.ap[0] * self.iter + self.ap[1])

        iface.set_simulation_time_limit(self.max_iter_length)

    def on_simulation_step(self, iface: TMInterface, t: int):
        if t == self.earliest_input_time - 20 and self.doing_start:
            self.start_state = iface.get_simulation_state()
            self.doing_start = False

        if t == self.max_len:
            self.next_iter(iface)

        if len(self.goals) > 0 and t % 200 == 0:
            state = iface.get_simulation_state()
            for (i, g) in enumerate(self.goals):
                if g(state) and not self.goals[i]:
                    self.log(f"[{self.name}] Reached goal {i+1} at time = {t}")
                    self.goals[i] = True
                    self.max_iter_length += self.extra_time
                    iface.set_simulation_time_limit(self.max_iter_length)

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        iface.prevent_simulation_finish()
        t = iface.get_simulation_state().race_time

        self.log(f"[{self.name}] Reached checkpoint {current}/{target} at time = {t}")
        self.max_iter_length += self.extra_time
        iface.set_simulation_time_limit(self.max_iter_length)

        if current == target and t < self.best_time:
            self.log(f"[{self.name}] New best finish time: {t} (previous best: {self.best_time})")
            self.best_time = t

    def next_input_sequence(self, iface: TMInterface):
        if self.random:
            steer = [random.randrange(i["steer"].start, i["steer"].stop, i["steer"].step) for i in self.inputs]
            time = [random.randrange(i["time"].start, i["time"].stop, i["time"].step) for i in self.inputs]
        else:
            for i in range(self.ap[0]-1):
                next(self.input_iter)
            next_seq = list(_flatten(next(self.input_iter)))
            steer = next_seq[0::2]
            time = next_seq[1::2]

        events = self.initial_events.copy()
        for i in range(len(steer)):
            events.add(time[i], ANALOG_STEER_NAME, steer[i])
        iface.set_event_buffer(events)

        self.log(f"[{self.name}] Next input sequence:")
        self.log(events.to_commands_str())

    def next_iter(self, iface: TMInterface):
        self.iter += 1
        self.max_iter_length = self.max_length + 10 * (self.ap[0] * self.iter + self.ap[1])
        self.goals_reached = [False] * len(self.goals)

        self.next_input_sequence(iface)
        iface.rewind_to_state(self.start_state)
        iface.set_simulation_time_limit(self.max_iter_length)
