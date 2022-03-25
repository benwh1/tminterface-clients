# Parameters

- `num_clients`: total number of clients running at once
- `client_num`: which client is this? (indexed from 0 to num_clients-1)
- `goals`: list of goals that you want to reach, e.g. reaching a certain position or velocity. Each goal is a function returning true or false that is applied to the simulation state
- `extra_time`: additional time allowed after reaching a checkpoint or goal
- `restarts`: list of functions like goals, but will give up and go to the next iteration
- `check_frequency`: how often (ms) to check for goals/restarts (checking every 10ms is slow)
- `client_name`: name of client (also used as log file name)

## LowInputClient

Parameters specific to LowInputClient:

- `initial_inputs`: inputs that are unchanged every iteration
- `start_iter`: which input iteration do we start from? Does nothing if `random` is true.
- `max_length`: max time allowed to reach the first goal/checkpoint before giving up and starting the next iteration
- `random`: try inputs randomly, or search all combinations?

## PressForwardClient

Parameters specific to PressForwardClient:

- `start_time`: waiting time (ms) of the first iteration
- `max_length`: max time (excluding waiting time) allowed to reach the first goal/checkpoint before giving up and starting the next iteration
