import pygamelib.gfx.core as gfx_core
import pygamelib.board_items as board_items
import pygamelib.assets.graphics as graphics
import pygamelib.constants as constants

import random
import uuid


class BaseParticle(board_items.Movable):
    def __init__(self, **kwargs):
        board_items.Movable.__init__(self, **kwargs)
        self.size = [1, 1]
        self.name = str(uuid.uuid4())
        self.type = "base_particle"
        self.sprixel = gfx_core.Sprixel(graphics.GeometricShapes.BULLET)
        if "bg_color" in kwargs:
            self.sprixel.bg_color = kwargs["bg_color"]
        if "fg_color" in kwargs:
            self.sprixel.fg_color = kwargs["fg_color"]
        if "model" in kwargs:
            self.sprixel.model = kwargs["model"]
        self.directions = [constants.UP, constants.DLUP, constants.DRUP]
        self.ttl = 5
        for item in ["ttl", "sprixel", "name", "type", "directions"]:
            if item in kwargs:
                setattr(self, item, kwargs[item])

    def direction(self):
        return random.choice(self.directions)

    def pickable(self):
        """
        A particle is not pickable by default. So that method returns False.
        """
        return False

    def overlappable(self):
        """
        Overlapable always return true. As by definition a particle is overlapable.
        """
        return True

    def size(self):
        """
        The size of a particle is the result of size[0]*size[1].
        """
        return self.size[0] * self.size[1]