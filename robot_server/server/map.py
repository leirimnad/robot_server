from enum import Enum
from typing import Optional


class Action(Enum):
    MOVE = 0
    TURN_RIGHT = 1
    TURN_LEFT = 2


class Rotation(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

    @classmethod
    def from_coordinate(cls, pos) -> list:
        res = []
        if pos[1] > 0:
            res.append(cls.UP)
        if pos[0] > 0:
            res.append(cls.RIGHT)
        if pos[1] < 0:
            res.append(cls.DOWN)
        if pos[0] < 0:
            res.append(cls.LEFT)
        return res

    def to_coordinate(self) -> tuple:
        return ((0, 1), (1, 0), (0, -1), (-1, 0))[self.value]

    @classmethod
    def opposite(cls, rotation):
        return cls((rotation.value + 2) % 4)

    def turn_for(self, rotations: list) -> Optional[Action]:
        nums = list((self.value - rotation.value + 4) % 4 for rotation in rotations)
        if 0 in nums:
            return None
        if 1 in nums:
            return Action.TURN_LEFT
        if 3 in nums:
            return Action.TURN_RIGHT
        return Action.TURN_LEFT  # if several turns needed


class RobotMap:
    def __init__(self):
        self.position = None
        self.rotation = None
        self.previous_action = None
        self.banned_positions = []

    def update_position(self, position: tuple) -> Action:
        res = self._update_position(position)
        self.previous_action = res
        if self.rotation is not None:
            if res == Action.TURN_LEFT:
                self.rotation = Rotation((self.rotation.value + 3) % 4)
            elif res == Action.TURN_RIGHT:
                self.rotation = Rotation((self.rotation.value + 1) % 4)
        return res

    def _update_position(self, new_position: tuple) -> Action:
        prev_position = self.position
        self.position = new_position

        def add_lists(list_a, list_b, b_mult=1) -> tuple:
            return list_a[0] + b_mult * list_b[0], list_a[1] + b_mult * list_b[1]

        if prev_position is None:
            return Action.MOVE
        elif self.rotation is None:  # determine rotation
            coordinate = add_lists(new_position, prev_position, b_mult=-1)
            if coordinate == (0, 0):
                if self.previous_action == Action.MOVE:  # unable to determine rotation due to an obstacle
                    return Action.TURN_RIGHT
                else:
                    return Action.MOVE

            self.rotation = Rotation.from_coordinate(coordinate)[0]

        next_position = add_lists(new_position, self.rotation.to_coordinate())
        available_rotations = set(map(Rotation.opposite, Rotation.from_coordinate(new_position)))

        if prev_position == new_position and self.previous_action == Action.MOVE:  # obstacle
            self.banned_positions.append(next_position)
            available_rotations.remove(self.rotation)

        available_rotations = list(filter(
            lambda rot: add_lists(new_position, rot.to_coordinate()) not in self.banned_positions,
            available_rotations))  # filter for rotations leading to a banned position

        if len(available_rotations) == 0:
            if next_position in self.banned_positions:
                return Action.TURN_RIGHT  # turn to bypass an obstacle
            else:
                self.banned_positions.append(self.position)
                return Action.MOVE  # move from an obstacle

        if self.rotation not in available_rotations:
            return self.rotation.turn_for(available_rotations)
        return Action.MOVE
