

from deckeditor import values


def spiral(direction: values.Direction):
	if direction == values.Direction.UP:
		_x = 0
		_y = -1
		dx = 1
		dy = 0

	elif direction == values.Direction.RIGHT:
		_x = 1
		_y = 0
		dx = 0
		dy = -1

	elif direction == values.Direction.DOWN:
		_x = 0
		_y = -1
		dx = -1
		dy = 0

	else:
		_x = -1
		_y = 0
		dx = 0
		dy = -1

	swaps = 0

	while True:

		yield _x, _y

		if _x == _y or _x == -_y:
			if swaps == 3:
				_x, _y = _x + dx, _y + dy
				yield _x, _y
				swaps = 0

			dx, dy = -dy, dx
			swaps += 1

		_x, _y = _x + dx, _y + dy