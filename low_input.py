import itertools
import logging
import random
import sys

from tminterface.client import Client
from tminterface.interface import TMInterface

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

        if "waiting_time" in kwargs:
            self.waiting_time = kwargs["waiting_time"]
        else:
            self.waiting_time = [0]

        if "time_first" in kwargs:
            self.time_first = kwargs["time_first"]
        else:
            self.time_first = False

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
            self.check_frequency = 500

        if "ordered_goals" in kwargs:
            self.ordered_goals = kwargs["check_frequency"]
        else:
            self.ordered_goals = True

        if "client_name" in kwargs:
            self.client_name = kwargs["client_name"]
        else:
            self.client_name = f"LowInputClient{self.client_num}"

        # earliest non-constant input time, excluding waiting time
        mins = [min(i["time"]) for i in inputs if not (len(i["time"]) == 1 and len(i["value"]) == 1)]
        if mins == []:
            self.earliest_nonconstant_input_time = 0
        else:
            self.earliest_nonconstant_input_time = min(mins)

        # earliest input time, excluding waiting time
        self.earliest_input_time = min(min(i["time"]) for i in inputs)

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

        # create input iterator if we are not choosing inputs randomly
        if not self.random:
            self.input_iter = itertools.product(self.waiting_time)
            for i in self.inputs:
                if self.time_first:
                    self.input_iter = itertools.product(self.input_iter, i["value"], i["time"])
                else:
                    self.input_iter = itertools.product(self.input_iter, i["time"], i["value"])
            for i in range(self.client_num):
                next(self.input_iter)

        # initialise things
        self.iter = 0
        self.best_time = 10**10
        self.min_waiting_time = min(self.waiting_time)
        self.start_state = None
        self.start_state_time = -2600

        self.next_iter(iface)

    def on_simulation_step(self, iface: TMInterface, t: int):
        if len(self.waiting_time) == 1:
            # no waiting time changes, we will never have to rewind back to before the first input
            next_start_state_time = self.min_waiting_time + self.earliest_nonconstant_input_time - 20
        else:
            # we will eventually have to rewind to before the first input, so we have to make start_state
            # earlier than this point
            next_start_state_time = self.min_waiting_time - 20

        if t == next_start_state_time:
            # start state time has changed, so we can set a new state
            if self.start_state_time != t:
                self.log(f"Setting start state to time t={t}")
                self.start_state = iface.get_simulation_state()
                self.start_state_time = t

        if t >= self.max_iter_time:
            self.log(f"Reached max time (t={t}), continuing to next iteration")
            self.next_iter(iface)

        if (len(self.goals) > 0 or len(self.restarts) > 0) and t % self.check_frequency == 0 and t >= next_start_state_time:
            state = iface.get_simulation_state()

            for (i, g) in enumerate(self.goals):
                if not self.goals_reached[i]:
                    if g(state):
                        self.log(f"Reached goal {i+1} at time = {t}")
                        self.goals_reached[i] = True
                        self.max_iter_time += self.extra_time
                        iface.set_simulation_time_limit(min(self.max_iter_time, 2**31-1))
                    if self.ordered_goals:
                        break

            for r in self.restarts:
                if r(state):
                    self.next_iter(iface)

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        iface.prevent_simulation_finish()
        t = iface.get_simulation_state().race_time

        self.log(f"Reached checkpoint {current}/{target} at time = {t}")
        self.max_iter_time += self.extra_time
        iface.set_simulation_time_limit(min(self.max_iter_time, 2**31-1))

        if current == target and t < self.best_time:
            self.log(f"New best finish time: {t} (previous best: {self.best_time})")
            self.best_time = t

    def next_input_sequence(self, iface: TMInterface):
        if self.random:
            waiting_time = random.choice(self.waiting_time)
            value = [random.choice(i["value"]) for i in self.inputs]
            time = [random.choice(i["time"]) for i in self.inputs]
        else:
            for i in range(self.num_clients-1):
                next(self.input_iter)
            next_seq = list(_flatten(next(self.input_iter)))

            waiting_time = next_seq[0]
            if self.time_first:
                value = next_seq[1::2]
                time = next_seq[2::2]
            else:
                value = next_seq[2::2]
                time = next_seq[1::2]

            if waiting_time > self.min_waiting_time:
                self.min_waiting_time = waiting_time

        events = iface.get_event_buffer()
        events.clear()
        for i in range(len(self.inputs)):
            events.add(waiting_time + time[i], self.inputs[i]["type"], value[i])
        iface.set_event_buffer(events)

        self.log("Next input sequence:")
        self.log(events.to_commands_str())

    def next_iter(self, iface: TMInterface):
        self.next_input_sequence(iface)

        self.iter += 1
        self.goals_reached = [False] * len(self.goals)
        self.max_iter_time = self.max_length + self.min_waiting_time + self.earliest_nonconstant_input_time

        self.log(f"Starting iteration {self.iter}")

        if self.start_state is not None:
            iface.rewind_to_state(self.start_state)

        iface.set_simulation_time_limit(min(self.max_iter_time, 2**31-1))
