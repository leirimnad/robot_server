import pytest

from robot_server.server.map import RobotMap, Action, Rotation
from robot_server.bridge.thread_event import MapState


def test_rotation_from_coordinate():
    assert Rotation.from_coordinate((0, 1)) == [Rotation.UP]
    assert Rotation.from_coordinate((1, 0)) == [Rotation.RIGHT]
    assert Rotation.from_coordinate((0, -1)) == [Rotation.DOWN]
    assert Rotation.from_coordinate((-1, 0)) == [Rotation.LEFT]


def test_rotation_opposite():
    assert Rotation.opposite(Rotation.UP) == Rotation.DOWN
    assert Rotation.opposite(Rotation.RIGHT) == Rotation.LEFT
    assert Rotation.opposite(Rotation.DOWN) == Rotation.UP
    assert Rotation.opposite(Rotation.LEFT) == Rotation.RIGHT


def test_rotation_turn_for():
    assert Rotation.UP.turn_for([Rotation.UP]) is None
    assert Rotation.UP.turn_for([Rotation.RIGHT]) == Action.TURN_RIGHT
    assert Rotation.UP.turn_for([Rotation.DOWN]) in [Action.TURN_RIGHT, Action.TURN_LEFT]
    assert Rotation.UP.turn_for([Rotation.LEFT]) == Action.TURN_LEFT
    assert Rotation.RIGHT.turn_for([Rotation.UP]) == Action.TURN_LEFT
    assert Rotation.RIGHT.turn_for([Rotation.RIGHT]) is None
    assert Rotation.RIGHT.turn_for([Rotation.DOWN]) == Action.TURN_RIGHT
    assert Rotation.RIGHT.turn_for([Rotation.LEFT]) in [Action.TURN_RIGHT, Action.TURN_LEFT]
    assert Rotation.DOWN.turn_for([Rotation.UP]) in [Action.TURN_RIGHT, Action.TURN_LEFT]
    assert Rotation.DOWN.turn_for([Rotation.RIGHT]) == Action.TURN_LEFT
    assert Rotation.DOWN.turn_for([Rotation.DOWN]) is None
    assert Rotation.DOWN.turn_for([Rotation.LEFT]) == Action.TURN_RIGHT
    assert Rotation.LEFT.turn_for([Rotation.UP]) == Action.TURN_RIGHT
    assert Rotation.LEFT.turn_for([Rotation.RIGHT]) in [Action.TURN_RIGHT, Action.TURN_LEFT]


@pytest.fixture(scope="function")
def initial_map():
    return RobotMap()


def test_initial_map(initial_map):
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    assert initial_map.position is None
    assert initial_map.rotation is None
    assert initial_map.previous_action is None


def test_first_move(initial_map):
    res = initial_map.update_position((0, -1))
    assert initial_map.position == (0, -1)
    assert initial_map.rotation is None
    assert initial_map.previous_action is Action.MOVE
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    assert res == Action.MOVE


def test_ideal_situation(initial_map):
    res_1 = initial_map.update_position((0, -1))
    assert res_1 == Action.MOVE
    initial_map.update_position((0, 0))
    assert initial_map.position == (0, 0)
    assert initial_map.rotation == Rotation.UP
    assert initial_map.previous_action == Action.MOVE
    assert initial_map.obstacles == []


def test_obstacle_1(initial_map):
    res_1 = initial_map.update_position((-1, -1))
    assert initial_map.position == (-1, -1)
    assert res_1 == Action.MOVE
    assert initial_map.rotation is None
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    res_2 = initial_map.update_position((-1, -1))
    assert initial_map.position == (-1, -1)
    assert res_2 == Action.TURN_RIGHT
    assert initial_map.rotation is None
    # obstacles are empty because the robot doesn't know its location
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    res_3 = initial_map.update_position((-1, -1))
    assert initial_map.position == (-1, -1)
    assert res_3 == Action.MOVE
    assert initial_map.rotation is None
    res_4 = initial_map.update_position((0, -1))
    assert initial_map.position == (0, -1)
    assert res_4 == Action.TURN_LEFT
    assert initial_map.rotation == Rotation.UP
    res_5 = initial_map.update_position((0, -1))
    assert initial_map.position == (0, -1)
    assert initial_map.rotation == Rotation.UP
    assert res_5 == Action.MOVE


def test_obstacle_2(initial_map):
    res = initial_map.update_position((-2, -2))
    assert res == Action.MOVE
    assert initial_map.rotation is None
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    res = initial_map.update_position((-2, -2))
    assert res == Action.TURN_RIGHT
    assert initial_map.rotation is None
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    res = initial_map.update_position((-2, -2))
    assert res == Action.MOVE
    assert initial_map.rotation is None
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    res = initial_map.update_position((-1, -2))
    assert res == Action.MOVE
    assert initial_map.rotation == Rotation.RIGHT
    assert initial_map.banned_positions == []
    assert initial_map.obstacles == []
    res = initial_map.update_position((-1, -2))
    assert res in (Action.TURN_LEFT, Action.TURN_RIGHT)
    assert initial_map.rotation != Rotation.RIGHT
    assert initial_map.banned_positions == [(0, -2)]
    assert initial_map.obstacles == [(0, -2)]


def test_map_state(initial_map):
    state: MapState = initial_map.get_map_state()
    assert state.position is None
    assert state.rotation is None
    assert state.obstacles == []
    initial_map.update_position((0, -1))
    state = initial_map.get_map_state()
    assert state.position == (0, -1)
    assert state.rotation is None
    assert state.obstacles == []
    initial_map.update_position((0, 0))
    state = initial_map.get_map_state()
    assert state.position == (0, 0)
    assert state.rotation == MapState.Rotation.UP
    assert state.obstacles == []
