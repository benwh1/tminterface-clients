# Parameters

- `inputs`: list of inputs to search in the form `{"time": time, "type": type, "value": value}` where `time` and `value` are either lists or ranges, and `type` is a TMI constant like `BINARY_ACCELERATE_NAME`, etc.
- `waiting time`: amount of time to wait before the first input. This should be a list or range. In each iteration, the waiting time will be added to the time value of all inputs in `inputs`.
- `time_first`: when checking all possible combinations of inputs, should `time` be varied first or `value`? If this is `True`, the inputs across many iterations may look like this: `0 steer 1000`, `10 steer 1000`, `20 steer 1000`, ..., `0 steer 1001`, etc. If `False`, the `value` will vary first, and the inputs will look like `0 steer 1000`, `0 steer 1001`, ..., `10 steer 1000`, `10 steer 1001`, etc.
- `max_length`: maximum amount of time allowed per iteration, starting from the time of the first input in that iteration (excluding inputs that are always the same for every iteration, and ignoring how `waiting_time` can change the inputs).
- `num_clients`: total number of clients running at once.
- `client_num`: TMI server ID (e.g. 0 for TMInterface0, etc.).
- `random`: exhaustively check all possible input combinations, or choose input sequences randomly?
- `goals`: list of goals/triggers that you want to reach, e.g. reaching a certain position or velocity. Each goal is a function returning true or false that is applied to the simulation state.
- `extra_time`: bonus time added to max_length after reaching a checkpoint or goal.
- `restarts`: list of functions like goals, but will give up and go to the next iteration when one is reached.
- `check_frequency`: how often (ms) to check for goals/restarts (checking every 10ms is slow)
- `ordered_goals`: must the goals be completed in order? If `True`, then e.g. the second goal will not be marked as completed when it is reached, unless the first goal has already been completed.
- `client_name`: name of client (also used as log file name).

# How to use

Run `python client.py n` where `n` is the the TMI server ID (see `client_num` above).
