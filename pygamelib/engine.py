"""
The game module contains the core classes for a game:

 * The Game object itself.
 * The Board object.
 * The Inventory object.

The Game object is what could be called the game engine.
It holds a lot of methods that helps taking care of some complex mechanics behind the
curtain.

The Board class is the base class for all levels.

.. autosummary::
   :toctree: .

   Board
   Game
   Inventory
"""
import pygamelib.board_items as board_items
import pygamelib.base as base
import pygamelib.actuators as actuators
import pygamelib.gfx.core as core
import pygamelib.constants as constants
import pygamelib.assets.graphics as graphics

from blessed import Terminal
import uuid
import random
import json

# We need to ignore that one as it is used by user to compare keys (i.e Utils.key.UP)
from readchar import readkey, key  # noqa: F401


class Board:
    """A class that represent a game board.

    The board is being represented by a square matrix.
    For the moment a board only support one player.

    The Board object is the base object to build a level :
        you create a Board and then you add BoardItems
        (or objects derived from BoardItem).

    :param name: the name of the Board
    :type name: str
    :param size: array [width,height] with width and height being int.
        The size of the board.
    :type size: list
    :param player_starting_position: array [row,column] with row and
        column being int. The coordinates at which Game will place the player
        on change_level().
    :type player_starting_position: list
    :param ui_borders: To set all the borders to the same value
    :type ui_borders: str
    :param ui_border_left: A string that represents the left border.
    :type ui_border_left: str
    :param ui_border_right: A string that represents the right border.
    :type ui_border_right: str
    :param ui_border_top: A string that represents the top border.
    :type ui_border_top: str
    :param ui_border_bottom: A string that represents the bottom border.
    :type ui_border_bottom: str
    :param ui_board_void_cell: A string that represents an empty cell. This
        option is going to be the model of the BoardItemVoid
        (see :class:`pygamelib.board_items.BoardItemVoid`)
    :type ui_board_void_cell: str
    :param parent: The parent object (usually the Game object).
    :type parent: :class:`~pygamelib.engine.Game`
    :param DISPLAY_SIZE_WARNINGS: A boolean to show or hide the warning about boards
        bigger than 80 rows and columns.
    :type DISPLAY_SIZE_WARNINGS: bool
    """

    def __init__(self, **kwargs):
        self.name = "Board"
        self.size = [10, 10]
        self.player_starting_position = [0, 0]
        self.ui_border_left = "|"
        self.ui_border_right = "|"
        self.ui_border_top = "-"
        self.ui_border_bottom = "-"
        self.ui_board_void_cell = " "
        self.ui_board_void_cell_sprixel = None
        self.DISPLAY_SIZE_WARNINGS = True
        self.parent = None
        # The overlapped matrix is used as an invisible layer were overlapped
        # restorable items are parked momentarily (until the cell they were on
        # is free again).
        self._overlapped_matrix = []
        # Setting class parameters
        for item in [
            "name",
            "size",
            "ui_border_bottom",
            "ui_border_top",
            "ui_border_left",
            "ui_border_right",
            "ui_board_void_cell",
            "ui_board_void_cell_sprixel",
            "player_starting_position",
            "DISPLAY_SIZE_WARNINGS",
            "parent",
        ]:
            if item in kwargs:
                setattr(self, item, kwargs[item])
        # if ui_borders is set then set all borders to that value
        if "ui_borders" in kwargs.keys():
            for item in [
                "ui_border_bottom",
                "ui_border_top",
                "ui_border_left",
                "ui_border_right",
            ]:
                setattr(self, item, kwargs["ui_borders"])
        # Now checking for board's data sanity
        try:
            self.check_sanity()
        except base.PglException as error:
            raise error

        # Init the list of movable and immovable objects
        self._movables = set()
        self._immovables = set()
        # If sanity check passed then, initialize the board
        self.init_board()

    def __str__(self):
        return (
            "----------------\n"
            f"Board name: {self.name}\n"
            f"Board size: {self.size}\n"
            f"Borders: '{self.ui_border_left}','{self.ui_border_right}','"
            f"{self.ui_border_top}','{self.ui_border_bottom}',\n"
            f"Board void cell: '{self.ui_board_void_cell}'\n"
            f"Player starting position: {self.player_starting_position}\n"
            "----------------"
        )

    def init_board(self):
        """
        Initialize the board with BoardItemVoid that uses ui_board_void_cell
        as model.

        Example::

            myboard.init_board()
        """
        if self.ui_board_void_cell_sprixel is not None and isinstance(
            self.ui_board_void_cell_sprixel, core.Sprixel
        ):
            self._matrix = [
                [
                    board_items.BoardItemVoid(
                        sprixel=self.ui_board_void_cell_sprixel, parent=self
                    )
                    for i in range(0, self.size[0], 1)
                ]
                for j in range(0, self.size[1], 1)
            ]
        else:
            self._matrix = [
                [
                    board_items.BoardItemVoid(
                        model=self.ui_board_void_cell, parent=self
                    )
                    for i in range(0, self.size[0], 1)
                ]
                for j in range(0, self.size[1], 1)
            ]
        self._overlapped_matrix = [
            [None for i in range(0, self.size[0], 1)] for j in range(0, self.size[1], 1)
        ]

    def generate_void_cell(self):
        """This method return a void cell.

        If ui_board_void_cell_sprixel is defined it uses it, otherwise use
        ui_board_void_cell to generate the void item.

        :return: A void board item
        :rtype: :class:`~pygamelib.board_items.BoardItemVoid`

        Example::

            board.generate_void_cell()
        """
        if self.ui_board_void_cell_sprixel is not None and isinstance(
            self.ui_board_void_cell_sprixel, core.Sprixel
        ):
            return board_items.BoardItemVoid(
                sprixel=self.ui_board_void_cell_sprixel,
                model=self.ui_board_void_cell_sprixel.model,
                parent=self,
            )
        else:
            return board_items.BoardItemVoid(model=self.ui_board_void_cell, parent=self)

    def init_cell(self, row, column):
        """
        Initialize a specific cell of the board with BoardItemVoid that
        uses ui_board_void_cell as model.

        :param row: the row coordinate.
        :type row: int
        :param column: the column coordinate.
        :type column: int

        Example::

            myboard.init_cell(2,3)
        """
        self._matrix[row][column] = self.generate_void_cell()

    def check_sanity(self):
        """Check the board sanity.

        This is essentially an internal method called by the constructor.
        """
        sanity_check = 0
        if type(self.size) is list:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO", ("The 'size' parameter must be a list.")
            )
        if len(self.size) == 2:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO",
                ("The 'size' parameter must be a list of 2 elements."),
            )
        if type(self.size[0]) is int:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO",
                ("The first element of the 'size' list must be an integer."),
            )
        if type(self.size[1]) is int:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO",
                ("The second element of the 'size' list must be an integer."),
            )
        if type(self.name) is str:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO", "The 'name' parameter must be a string."
            )
        if type(self.ui_border_bottom) is str:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO",
                ("The 'ui_border_bottom' parameter must be a string."),
            )
        if type(self.ui_border_top) is str:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO", ("The 'ui_border_top' parameter must be a string.")
            )
        if type(self.ui_border_left) is str:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO", ("The 'ui_border_left' parameter must be a string.")
            )
        if type(self.ui_border_right) is str:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO", ("The 'ui_border_right' parameter must be a string.")
            )
        if type(self.ui_board_void_cell) is str:
            sanity_check += 1
        else:
            raise base.PglException(
                "SANITY_CHECK_KO",
                ("The 'ui_board_void_cell' parameter must be a string."),
            )
        if self.ui_board_void_cell_sprixel is not None and isinstance(
            self.ui_board_void_cell, core.Sprixel
        ):
            sanity_check += 1
        elif self.ui_board_void_cell_sprixel is not None and not isinstance(
            self.ui_board_void_cell_sprixel, core.Sprixel
        ):
            raise base.PglException(
                "SANITY_CHECK_KO",
                ("The 'ui_board_void_cell_sprixel' parameter must be a Sprixel."),
            )
        else:
            sanity_check += 1
        if self.size[0] > 80:
            if self.DISPLAY_SIZE_WARNINGS:
                base.Text.warn(
                    (
                        f"The first dimension of your board is {self.size[0]}. "
                        "It is a good practice to keep it at a maximum of 80 for "
                        "compatibility with older terminals."
                    )
                )

        if self.size[1] > 80:
            if self.DISPLAY_SIZE_WARNINGS:
                base.Text.warn(
                    (
                        f"The second dimension of your board is {self.size[1]}. "
                        "It is a good practice to keep it at a maximum of 80 for "
                        "compatibility with older terminals."
                    )
                )

        # If all sanity check clears return True else raise a general error.
        # I have no idea how the general error could ever occur but...
        # better safe than sorry!
        if sanity_check == 11:
            return True
        else:
            raise base.PglException("SANITY_CHECK_KO", "The board data are not valid.")

    def width(self):
        """A convenience method to get the width of the Board.

        It is absolutely equivalent to access to board.size[0].

        :return: The width of the board.
        :rtype: int

        Example::

            if board.size[0] != board.width():
                print('Houston, we have a problem...')
        """
        return self.size[0]

    def height(self):
        """A convenience method to get the height of the Board.

        It is absolutely equivalent to access to board.size[1].

        :return: The height of the board.
        :rtype: int

        Example::

            if board.size[1] != board.height():
                print('Houston, we have a problem...')
        """
        return self.size[1]

    def display_around(self, object, row_radius, column_radius):
        """Display only a part of the board.

        This method behaves like display() but only display a part of the board around
        an object (usually the player).
        Example::

            # This will display only a total of 30 cells vertically and
            # 60 cells horizontally.
            board.display_around(player, 15, 30)

        :param object: an item to center the view on (it has to be a subclass
            of BoardItem)
        :type object: :class:`~pygamelib.board_items.BoardItem`
        :param row_radius: The radius of display in number of rows showed. Remember that
            it is a radius not a diameter...
        :type row_radius: int
        :param column_radius: The radius of display in number of columns showed.
            Remember that... Well, same thing.
        :type column_radius: int

        It uses the same display algorithm than the regular display() method.
        """
        # First let's take care of the type checking
        if not isinstance(object, board_items.BoardItem):
            raise base.PglInvalidTypeException(
                "Board.display_around: object needs to be a BoardItem."
            )
        if type(row_radius) is not int or type(column_radius) is not int:
            raise base.PglInvalidTypeException(
                "Board.display_around: both row_radius and"
                " column_radius needs to be int."
            )
        # Now if the viewport is greater or equal to the board size, well we just need
        # a regular display()
        if self.size[1] <= 2 * row_radius and self.size[0] <= 2 * column_radius:
            return self.display()
        if self.size[0] <= 2 * column_radius:
            column_radius = round(self.size[0] / 2)
        if self.size[1] <= 2 * row_radius:
            row_radius = round(self.size[1] / 2)
        row_min_bound = 0
        row_max_bound = self.size[1]
        column_min_bound = 0
        column_max_bound = self.size[0]
        # Here we account for the dimension of the complex item to center the viewport
        # on it.
        pos_row = object.pos[0]
        pos_col = object.pos[1]
        if isinstance(object, board_items.BoardComplexItem):
            pos_row = object.pos[0] + int(object.height() / 2)
            pos_col = object.pos[1] + int(object.width() / 2)
        # Row
        if pos_row - row_radius >= 0:
            row_min_bound = pos_row - row_radius
        if pos_row + row_radius < row_max_bound:
            row_max_bound = pos_row + row_radius
        # Columns
        if pos_col - column_radius >= 0:
            column_min_bound = pos_col - column_radius
        if pos_col + column_radius < column_max_bound:
            column_max_bound = pos_col + column_radius
        # Now adjust boundaries so it looks fine at min and max
        if column_min_bound <= 0:
            column_min_bound = 0
            column_max_bound = 2 * column_radius
        if column_max_bound >= self.size[0]:
            column_max_bound = self.size[0]
            if (self.size[0] - 2 * column_radius) >= 0:
                column_min_bound = self.size[0] - 2 * column_radius
        if row_min_bound <= 0:
            row_min_bound = 0
            row_max_bound = 2 * row_radius
        if row_max_bound >= self.size[1]:
            row_max_bound = self.size[1]
            if (self.size[1] - 2 * row_radius) >= 0:
                row_min_bound = self.size[1] - 2 * row_radius
        if row_min_bound == 0:
            bt_size = column_radius * 2
            if bt_size >= self.size[0]:
                bt_size = self.size[0]
                if pos_col - column_radius > 0:
                    bt_size = self.size[0] - (pos_col - column_radius)
            print(self.ui_border_top * bt_size, end="")
            if column_min_bound <= 0 and column_max_bound >= self.size[0]:
                print(self.ui_border_top * 2, end="")
            elif column_min_bound <= 0 or column_max_bound >= self.size[0]:
                print(self.ui_border_top, end="")
            print("\r")
        for row in self._matrix[row_min_bound:row_max_bound]:
            if column_min_bound == 0:
                print(self.ui_border_left, end="")
            for y in row[column_min_bound:column_max_bound]:
                if (
                    isinstance(y, board_items.BoardItemVoid)
                    and y.model != self.ui_board_void_cell
                ):
                    y.model = self.ui_board_void_cell
                    y.sprixel = self.ui_board_void_cell_sprixel
                print(y, end="")
            if column_max_bound >= self.size[0]:
                print(self.ui_border_right, end="")
            print("\r")
        if row_max_bound >= self.size[1]:
            bb_size = column_radius * 2
            if bb_size >= self.size[0]:
                bb_size = self.size[0]
                if pos_col - column_radius > 0:
                    bb_size = self.size[0] - (pos_col - column_radius)
            print(self.ui_border_bottom * bb_size, end="")
            if column_min_bound <= 0 and column_max_bound >= self.size[0]:
                print(self.ui_border_bottom * 2, end="")
            elif column_min_bound <= 0 or column_max_bound >= self.size[0]:
                print(self.ui_border_bottom, end="")
            print("\r")

    def display(self):
        """Display the entire board.

        This method display the Board (as in print()), taking care of
        displaying the borders, and everything inside.

        It uses the __str__ method of the item, which by default uses (in order)
        BoardItem.sprixel and (if no sprixel is defined) BoardItem.model. If you want to
        override this behavior you have to subclass BoardItem.
        """
        # # Debug: print the overlapped matrix
        # for row in self._overlapped_matrix:
        #     print(self.ui_border_left, end="")
        #     for column in row:
        #         if (
        #             isinstance(column, board_items.BoardItemVoid)
        #             and column.model != self.ui_board_void_cell
        #         ):
        #             column.model = self.ui_board_void_cell
        #         elif column is None:
        #             print(" ", end="")
        #         else:
        #             print(column, end="\x1b[0m")
        #     print(self.ui_border_right + "\x1b[0m\r")
        # print("\x1b[0m")
        # # eod
        print(
            "".join(
                [
                    self.ui_border_top * len(self._matrix[0]),
                    self.ui_border_top * 2,
                    "\r",
                ]
            )
        )
        for row in self._matrix:
            print(self.ui_border_left, end="")
            for column in row:
                if (
                    isinstance(column, board_items.BoardItemVoid)
                    and column.model != self.ui_board_void_cell
                ):
                    if isinstance(self.ui_board_void_cell, core.Sprixel):
                        column.sprixel = self.ui_board_void_cell_sprixel
                        column.model = self.ui_board_void_cell_sprixel.model
                    else:
                        column.model = self.ui_board_void_cell
                print(column, end="")
            print(self.ui_border_right + "\r")
        print(
            "".join(
                [
                    self.ui_border_bottom * len(self._matrix[0]),
                    self.ui_border_bottom * 2,
                    "\r",
                ]
            )
        )

    def item(self, row, column):
        """
        Return the item at the row, column position if within
        board's boundaries.

        :rtype: pygamelib.board_items.BoardItem

        :raise PglOutOfBoardBoundException: if row or column are
            out of bound.
        """
        if row < self.size[1] and column < self.size[0]:
            return self._matrix[row][column]
        else:
            raise base.PglOutOfBoardBoundException(
                (
                    f"There is no item at coordinates [{row},{column}] "
                    "because it's out of the board boundaries "
                    f"({self.size[0]}x{self.size[1]})."
                )
            )

    def place_item(self, item, row, column):
        """
        Place an item at coordinates row and column.

        If row or column are our of the board boundaries,
        an PglOutOfBoardBoundException is raised.

        If the item is not a subclass of BoardItem, an PglInvalidTypeException

        .. warning:: Nothing prevents you from placing an object on top of
            another. Be sure to check that. This method will check for items that
            are both overlappable **and** restorable to save them, but that's
            the extend of it.
        """
        if row < self.size[1] and column < self.size[0]:
            if isinstance(item, board_items.BoardComplexItem):
                for ir in range(0, item.size[1]):
                    for ic in range(0, item.size[0]):
                        if not isinstance(item.item(ir, ic), board_items.BoardItemVoid):
                            self.place_item(item.item(ir, ic), row + ir, column + ic)
                item.store_position(row, column)
            elif isinstance(item, board_items.BoardItem):
                # If we are about to place the item on a overlappable and
                # restorable we store it to be restored
                # when the Movable will move.
                existing_item = self._matrix[row][column]
                if (
                    isinstance(existing_item, board_items.Immovable)
                    and existing_item.restorable()
                    and existing_item.overlappable()
                ):
                    # Let's save the item on the hidden layer
                    self._overlapped_matrix[row][column] = self._matrix[row][column]
                    if (
                        item.sprixel is not None
                        and self._overlapped_matrix[row][column].sprixel is not None
                        and item.sprixel.is_bg_transparent
                    ):
                        item.sprixel.bg_color = self._overlapped_matrix[row][
                            column
                        ].sprixel.bg_color
                # Place the item on the board
                self._matrix[row][column] = item
                # Take ownership of the item (if item doesn't have parent)
                if item.parent is None:
                    item.parent = self
                item.store_position(row, column)
                if isinstance(item, board_items.Movable):
                    if isinstance(item.parent, board_items.BoardComplexItem):
                        self._movables.add(item.parent)
                    else:
                        self._movables.add(item)
                elif isinstance(item, board_items.Immovable):
                    if isinstance(item.parent, board_items.BoardComplexItem):
                        self._immovables.add(item.parent)
                    else:
                        self._immovables.add(item)
            else:
                raise base.PglInvalidTypeException(
                    "The item passed in argument is not a subclass of BoardItem"
                )
        else:
            raise base.PglOutOfBoardBoundException(
                f"Cannot place item at coordinates [{row},{column}] because "
                f"it's out of the board boundaries ({self.size[0]}x{self.size[1]})."
            )

    def _move_complex(self, item, direction, step=1):
        if isinstance(item, board_items.Movable) and item.can_move():
            # If direction is not a vector, transform into one
            if not isinstance(direction, base.Vector2D):
                direction = base.Vector2D.from_direction(direction, step)

            projected_position = item.position_as_vector() + direction
            if (
                projected_position is not None
                and projected_position.row >= 0
                and projected_position.column >= 0
                and (projected_position.row + item.height() - 1) < self.size[1]
                and (projected_position.column + item.width() - 1) < self.size[0]
            ):
                can_draw = True
                for orow in range(0, item.size[1]):
                    for ocol in range(0, item.size[0]):
                        new_row = projected_position.row + orow
                        new_column = projected_position.column + ocol
                        # Check all items within the surface
                        if isinstance(
                            self._matrix[new_row][new_column], board_items.Actionable
                        ):
                            if (
                                isinstance(item, board_items.Player)
                                and (
                                    (
                                        self._matrix[new_row][new_column].perm
                                        == constants.PLAYER_AUTHORIZED
                                    )
                                    or (
                                        self._matrix[new_row][new_column].perm
                                        == constants.ALL_CHARACTERS_AUTHORIZED
                                    )
                                )
                            ) or (
                                isinstance(item, board_items.NPC)
                                and (
                                    (
                                        self._matrix[new_row][new_column].perm
                                        == constants.NPC_AUTHORIZED
                                    )
                                    or (
                                        self._matrix[new_row][new_column].perm
                                        == constants.ALL_CHARACTERS_AUTHORIZED
                                    )
                                )
                                or (
                                    self._matrix[new_row][new_column].perm
                                    == constants.ALL_MOVABLE_AUTHORIZED
                                )
                            ):
                                self._matrix[new_row][new_column].activate()
                        # Now I need to put the rest of the code here...
                        if (
                            not self._matrix[new_row][new_column].overlappable()
                            and self._matrix[new_row][new_column].pickable()
                            and isinstance(item, board_items.Movable)
                            and item.has_inventory()
                        ):
                            # Put the item in the inventory
                            item.inventory.add_item(self._matrix[new_row][new_column])
                            # And then clear the cell (this is usefull for the next one)
                            self.clear_cell(new_row, new_column)
                            # Finally we check if the destination is overlappable
                        if (
                            self._matrix[new_row][new_column].parent != item
                            and not self._matrix[new_row][new_column].overlappable()
                        ):
                            can_draw = False
                            break
                if can_draw:
                    for row in range(0, item.size[1], 1):
                        for col in range(0, item.size[0], 1):
                            if (
                                self._overlapped_matrix[item.pos[0] + row][
                                    item.pos[1] + col
                                ]
                                is not None
                            ):
                                self.place_item(
                                    self._overlapped_matrix[item.pos[0] + row][
                                        item.pos[1] + col
                                    ],
                                    item.pos[0] + row,
                                    item.pos[1] + col,
                                )
                                self._overlapped_matrix[item.pos[0] + row][
                                    item.pos[1] + col
                                ] = None
                            # else:
                            #     self.place_item(
                            #         self.generate_void_cell(),
                            #         item.pos[0] + row,
                            #         item.pos[1] + col,
                            #     )
                    self.place_item(
                        item, projected_position.row, projected_position.column,
                    )
        else:
            raise base.PglObjectIsNotMovableException(
                (
                    f"Item '{item.name}' at position [{item.pos[0]}, "
                    f"{item.pos[1]}] is not a subclass of Movable, "
                    f"therefor it cannot be moved."
                )
            )

    def move(self, item, direction, step=1):
        """
        Board.move() is a routing function. It does 2 things:

         1 - If the direction is a :class:`~pygamelib.base.Vector2D`, round the
            values to the nearest integer (as move works with entire board cells).
         2 - route toward the right moving function depending if the item is complex or
            not.

        Move an item in the specified direction for a number of steps.

        :param item: an item to move (it has to be a subclass of Movable)
        :type item: pygamelib.board_items.Movable
        :param direction: a direction from :ref:`constants-module`
        :type direction: pygamelib.constants or :class:`~pygamelib.base.Vector2D`
        :param step: the number of steps to move the item.
        :type step: int

        If the number of steps is greater than the Board, the item will
        be move to the maximum possible position.

        If the item is not a subclass of Movable, an PglObjectIsNotMovableException
        exception (see :class:`pygamelib.base.PglObjectIsNotMovableException`).

        Example::

            board.move(player,constants.UP,1)

        .. Important:: if the move is successfull, an empty BoardItemVoid
            (see :class:`pygamelib.boards_item.BoardItemVoid`) will be put at the
            departure position (unless the movable item is over an overlappable
            item). If the movable item is over an overlappable item, the
            overlapped item is restored.

        .. Important:: Also important: If the direction is a
           :class:`~pygamelib.base.Vector2D`, the values will be rounded to the
           nearest integer (as move works with entire board cells). It allows for
           movement accumulation before actually moving.

        .. todo:: check all types!

        """
        if isinstance(direction, base.Vector2D):
            # If direction is a vector, round the numbers to the next integer.
            direction.row = round(direction.row)
            direction.column = round(direction.column)
        if isinstance(item, board_items.BoardComplexItem):
            return self._move_complex(item, direction, step)
        else:
            return self._move_simple(item, direction, step)

    def _move_simple(self, item, direction, step=1):
        if isinstance(item, board_items.Movable) and item.can_move():

            # if direction not in dir(Constants):
            #     raise base.PglInvalidTypeException('In Board.move(item, direction,
            # step), direction must be a direction contant from the
            # pygamelib.constants module')

            new_row = None
            new_column = None
            if isinstance(direction, base.Vector2D):
                new_row = item.pos[0] + direction.row
                new_column = item.pos[1] + direction.column
            else:
                if direction == constants.UP:
                    new_row = item.pos[0] - step
                    new_column = item.pos[1]
                elif direction == constants.DOWN:
                    new_row = item.pos[0] + step
                    new_column = item.pos[1]
                elif direction == constants.LEFT:
                    new_row = item.pos[0]
                    new_column = item.pos[1] - step
                elif direction == constants.RIGHT:
                    new_row = item.pos[0]
                    new_column = item.pos[1] + step
                elif direction == constants.DRUP:
                    new_row = item.pos[0] - step
                    new_column = item.pos[1] + step
                elif direction == constants.DRDOWN:
                    new_row = item.pos[0] + step
                    new_column = item.pos[1] + step
                elif direction == constants.DLUP:
                    new_row = item.pos[0] - step
                    new_column = item.pos[1] - step
                elif direction == constants.DLDOWN:
                    new_row = item.pos[0] + step
                    new_column = item.pos[1] - step
            # First of all we check if the new coordinates are within the board
            if (
                new_row is not None
                and new_column is not None
                and new_row >= 0
                and new_column >= 0
                and new_row < self.size[1]
                and new_column < self.size[0]
            ):
                # Then, we check if the item is actionable and if so, if the item
                # is allowed to activate it.
                if isinstance(
                    self._matrix[new_row][new_column], board_items.Actionable
                ):
                    if (
                        isinstance(item, board_items.Player)
                        and (
                            (
                                self._matrix[new_row][new_column].perm
                                == constants.PLAYER_AUTHORIZED
                            )
                            or (
                                self._matrix[new_row][new_column].perm
                                == constants.ALL_CHARACTERS_AUTHORIZED
                            )
                        )
                    ) or (
                        isinstance(item, board_items.NPC)
                        and (
                            (
                                self._matrix[new_row][new_column].perm
                                == constants.NPC_AUTHORIZED
                            )
                            or (
                                self._matrix[new_row][new_column].perm
                                == constants.ALL_CHARACTERS_AUTHORIZED
                            )
                        )
                    ):
                        self._matrix[new_row][new_column].activate()
                # Now we check if the destination contains a pickable item.
                # Note: I'm not sure why I decided that pickables were not overlapable.
                if (
                    not self._matrix[new_row][new_column].overlappable()
                    and self._matrix[new_row][new_column].pickable()
                    and isinstance(item, board_items.Movable)
                    and item.has_inventory()
                ):
                    # Put the item in the inventory
                    item.inventory.add_item(self._matrix[new_row][new_column])
                    # And then clear the cell (this is usefull for the next one)
                    self.clear_cell(new_row, new_column)
                # Finally we check if the destination is overlappable
                if self._matrix[new_row][new_column].overlappable():
                    # And if it is, we check if the destination is restorable
                    if (
                        not isinstance(
                            self._matrix[new_row][new_column], board_items.BoardItemVoid
                        )
                        and isinstance(
                            self._matrix[new_row][new_column], board_items.Immovable
                        )
                        and self._matrix[new_row][new_column].restorable()
                    ):
                        # If so, we save the item on the hidden layer
                        self._overlapped_matrix[new_row][new_column] = self._matrix[
                            new_row
                        ][new_column]
                    if (
                        item.sprixel is not None
                        and self._matrix[new_row][new_column].sprixel is not None
                        and item.sprixel.is_bg_transparent
                    ):
                        item.sprixel.bg_color = self._matrix[new_row][
                            new_column
                        ].sprixel.bg_color
                    # Finally instead of just placing a BoardItemVoid on
                    # the departure position we first make sure there
                    # is no overlapping object to restore.
                    overlapped_item = self._overlapped_matrix[item.pos[0]][item.pos[1]]
                    if (
                        overlapped_item is not None
                        and isinstance(overlapped_item, board_items.Immovable)
                        and overlapped_item.restorable()
                        and (
                            overlapped_item.pos[0] != new_row
                            or overlapped_item.pos[1] != new_column
                        )
                    ):
                        self.place_item(
                            overlapped_item,
                            overlapped_item.pos[0],
                            overlapped_item.pos[1],
                        )
                        self._overlapped_matrix[item.pos[0]][item.pos[1]] = None
                    else:
                        self.place_item(
                            self.generate_void_cell(), item.pos[0], item.pos[1],
                        )
                    self.place_item(item, new_row, new_column)
        else:
            raise base.PglObjectIsNotMovableException(
                (
                    f"Item '{item.name}' at position [{item.pos[0]}, "
                    f"{item.pos[1]}] is not a subclass of Movable, "
                    f"therefor it cannot be moved."
                )
            )

    def clear_cell(self, row, column):
        """Clear cell (row, column)

        This method clears a cell, meaning it position a
        void_cell BoardItemVoid at these coordinates.

        :param row: The row of the item to remove
        :type row: int
        :param column: The column of the item to remove
        :type column: int

        Example::

            myboard.clear_cell(3,4)

        .. WARNING:: This method does not check the content before,
            it *will* overwrite the content.

        .. Important:: This method test if something is left on the overlapped layer.
           If so, it restore what was overlapped instead of creating a new void item.

        """
        if self._matrix[row][column] in self._movables:
            self._movables.discard(self._matrix[row][column])
        elif self._matrix[row][column] in self._immovables:
            self._immovables.discard(self._matrix[row][column])
        self._matrix[row][column] = None
        if self._overlapped_matrix[row][column] is not None:
            self._matrix[row][column] = self._overlapped_matrix[row][column]
            self._overlapped_matrix[row][column] = None
        else:
            self.init_cell(row, column)

    def get_movables(self, **kwargs):
        """Return a list of all the Movable objects in the Board.

        See :class:`pygamelib.board_items.Movable` for more on a Movable object.

        :param ``**kwargs``: an optional dictionnary with keys matching
            Movables class members and value being something contained
            in that member.
        :return: A list of Movable items

        Example::

            for m in myboard.get_movables():
                print(m.name)

            # Get all the Movable objects that has a type that contains "foe"
            foes = myboard.get_movables(type="foe")
        """
        if kwargs:
            retvals = []
            for item in self._movables:
                counter = 0
                for (arg_key, arg_value) in kwargs.items():
                    if arg_value in getattr(item, arg_key):
                        counter += 1
                if counter == len(kwargs):
                    retvals.append(item)
            return retvals
        else:
            return list(self._movables)

    def get_immovables(self, **kwargs):
        """Return a list of all the Immovable objects in the Board.

        See :class:`pygamelib.board_items.Immovable` for more on
            an Immovable object.

        :param ``**kwargs``: an optional dictionnary with keys matching
            Immovables class members and value being something
            **contained** in that member.
        :return: A list of Immovable items

        Example::

            for m in myboard.get_immovables():
                print(m.name)

            # Get all the Immovable objects that type contains "wall"
                AND name contains fire
            walls = myboard.get_immovables(type="wall",name="fire")

        """
        if kwargs:
            retvals = []
            for item in self._immovables:
                counter = 0
                for (arg_key, arg_value) in kwargs.items():
                    if arg_value in getattr(item, arg_key):
                        counter += 1
                if counter == len(kwargs):
                    retvals.append(item)
            return retvals
        else:
            return list(self._immovables)


class Game:
    """A class that serve as a game engine.

    This object is the central system that allow the management of a game. It holds
    boards (see :class:`pygamelib.engine.Board`), associate it to level, takes care of
    level changing, etc.

    :param name: The Game name.
    :type name: str
    :param boards: A dictionnary of boards with the level number as key and a board
        reference as value.
    :type boards: dict
    :param menu: A dictionnary of menus with a category (str) as key and another
        dictionnary (key: a shortcut, value: a description) as value.
    :type menu: dict
    :param current_level: The current level.
    :type current_level: int
    :param enable_partial_display: A boolean to tell the Game object to enable or not
        partial display of boards. Default: False.
    :type enable_partial_display: bool
    :param partial_display_viewport: A 2 int elements array that gives the **radius**
        of the partial display in number of row and column. Please see
        :func:`~pygamelib.engine.Board.display_around()`.
    :type partial_display_viewport: list

    .. note:: The game object has an object_library member that is always an empty array
        except just after loading a board. In this case, if the board have a "library"
        field, it is going to be used to populate object_library. This library is
        accessible through the Game object mainly so people have access to it across
        different Boards during level design in the editor. That architecture decision
        is debatable.

    .. note:: The constructor of Game takes care of initializing the terminal to
        properly render the colors on Windows.

    .. important:: The Game object automatically assumes ownership over the Player.

    """

    def __init__(
        self,
        name="Game",
        boards={},
        menu={},
        current_level=None,
        enable_partial_display=False,
        partial_display_viewport=None,
    ):
        self.name = name
        self._boards = boards
        self._menu = menu
        self.current_level = current_level
        self.player = None
        self.state = constants.RUNNING
        self.enable_partial_display = enable_partial_display
        self.partial_display_viewport = partial_display_viewport
        self._config = None
        self._configuration = None
        self._configuration_internals = None
        self.object_library = []
        self.terminal = Terminal()
        self.screen = core.Screen(self.terminal)
        base.init()

    def add_menu_entry(self, category, shortcut, message, data=None):
        """Add a new entry to the menu.

        Add another shortcut and message to the specified category.

        Categories help organize the different sections of a menu or dialogues.

        :param category: The category to which the entry should be added.
        :type category: str
        :param shortcut: A shortcut (usually one key) to display.
        :type shortcut: str
        :param message: a message that explains what the shortcut does.
        :type message: str
        :param data: a data that you can get from the menu object.
        :type message: various

        The shortcut and data is optional.

        Example::

            game.add_menu_entry('main_menu','d','Go right',constants.RIGHT)
            game.add_menu_entry('main_menu',None,'-----------------')
            game.add_menu_entry('main_menu','v','Change game speed')

        """
        if category in self._menu.keys():
            self._menu[category].append(
                {"shortcut": shortcut, "message": message, "data": data}
            )
        else:
            self._menu[category] = [
                {"shortcut": shortcut, "message": message, "data": data}
            ]

    def delete_menu_category(self, category=None):
        """Delete an entire category from the menu.

        That function removes the entire list of messages that are attached to the
        category.

        :param category: The category to delete.
        :type category: str
        :raise PglInvalidTypeException: If the category is not a string

        .. important:: If the entry have no shortcut it's advised not to try to update
            unless you have only one NoneType as a shortcut.

        Example::

            game.add_menu_entry('main_menu','d','Go right')
            game.update_menu_entry('main_menu','d','Go LEFT',constants.LEFT)

        """
        if type(category) is str and category in self._menu:
            del self._menu[category]
        else:
            raise base.PglInvalidTypeException(
                "in Game.delete_menu_entry(): category cannot be anything else but a"
                "string."
            )

    def update_menu_entry(self, category, shortcut, message, data=None):
        """Update an entry of the menu.

        Update the message associated to a category and a shortcut.

        :param category: The category in which the entry is located.
        :type category: str
        :param shortcut: The shortcut of the entry you want to update.
        :type shortcut: str
        :param message: a message that explains what the shortcut does.
        :type message: str
        :param data: a data that you can get from the menu object.
        :type message: various

        .. important:: If the entry have no shortcut it's advised not to try to update
            unless you have only one NoneType as a shortcut.

        Example::

            game.add_menu_entry('main_menu','d','Go right')
            game.update_menu_entry('main_menu','d','Go LEFT',constants.LEFT)

        """
        for e in self._menu[category]:
            if e["shortcut"] == shortcut:
                e["message"] = message
                if data is not None:
                    e["data"] = data

    def get_menu_entry(self, category, shortcut):
        """Get an entry of the menu.

        This method return a dictionnary with 3 entries :
            * shortcut
            * message
            * data

        :param category: The category in which the entry is located.
        :type category: str
        :param shortcut: The shortcut of the entry you want to get.
        :type shortcut: str
        :return: The menu entry or None if none was found
        :rtype: dict

        Example::

            ent = game.get_menu_entry('main_menu','d')
            game.move_player(int(ent['data']),1)

        """
        if category in self._menu:
            for e in self._menu[category]:
                if e["shortcut"] == shortcut:
                    return e
        return None

    def display_menu(
        self, category, orientation=constants.ORIENTATION_VERTICAL, paginate=10
    ):
        """Display the menu.

        This method display the whole menu for a given category.

        :param category: The category to display. **Mandatory** parameter.
        :type category: str
        :param orientation: The shortcut of the entry you want to get.
        :type orientation: :class:`pygamelib.constants`
        :param paginate: pagination parameter (how many items to display before
                        changing line or page).
        :type paginate: int

        Example::

            game.display_menu('main_menu')
            game.display_menu('main_menu', constants.ORIENTATION_HORIZONTAL, 5)

        """
        line_end = "\n"
        if orientation == constants.ORIENTATION_HORIZONTAL:
            line_end = " | "
        if category not in self._menu:
            raise base.PglException(
                "invalid_menu_category",
                f"The '{category}' category is not registered in the menu. Did you add"
                f"a menu entry in that category with Game.add_menu_entry('{category}',"
                f"'some shortcut','some message') ? If yes, then you should check "
                f"for typos.",
            )
        pagination_counter = 1
        for k in self._menu[category]:
            if k["shortcut"] is None:
                print(k["message"], end=line_end)
            else:
                print(f"{k['shortcut']} - {k['message']}", end=line_end)
                pagination_counter += 1
                if pagination_counter > paginate:
                    print("")
                    pagination_counter = 1

    def clear_screen(self):
        """
        Clear the whole screen (i.e: remove everything written in terminal)

        .. deprecated:: 1.2.0
           Starting 1.2.0 we are using the pygamelib.gfx.core.Screen object to manage
           the screen. That function is a simple forward and is kept for backward
           compatibility only. You should use Game.screen.clear()
        """
        self.screen.clear()

    def get_key(self):
        """Reads the next key-stroke returning it as a string.

        Example::

            key = Utils.get_key()
            if key == Utils.key.UP:
                print("Up")
            elif key == "q"
                exit()

        .. note:: See `readkey` documentation in `readchar` package.
        """
        return readkey()

    def load_config(self, filename, section="main"):
        """
        Load a configuration file from the disk.
        The configuration file must respect the INI syntax.
        The goal of these methods is to simplify configuration files management.

        :param filename: The filename to load. does not check for existence.
        :type filename: str
        :param section: The section to put the read config file into. This allow for
            multiple files for multiple purpose. Section is a human readable unique
            identifier.
        :type section: str
        :raise FileNotFoundError: If filename is not found on the disk.
        :raise json.decoder.JSONDecodeError: If filename could not be decoded as JSON.
        :returns: The parsed data.
        :rtype: dict

        .. warning:: **breaking changes:** before v1.1.0 that method use to load file
            using the configparser module. This have been dumped in favor of json files.
            Since that methods was apparently not used, there is no backward
            compatibility.

        Example::

            mygame.load_config('game_controls.json','game_control')

        """
        if self._configuration is None:
            self._configuration = {}
        if self._configuration_internals is None:
            self._configuration_internals = {}

        if section not in self._configuration_internals:
            self._configuration_internals[section] = {}

        with open(filename) as config_file:
            config_content = json.load(config_file)
            if section not in self._configuration.keys():
                self._configuration[section] = config_content
                self._configuration_internals[section]["loaded_from"] = filename
                return config_content

    def config(self, section="main"):
        """Get the content of a previously loaded configuration section.

        :param section: The name of the section.
        :type section: str

        Example::

            if mygame.config('main')['pgl-version-required'] < 10200:
                print('The pygamelib version 1.2.0 or greater is required.')
                exit()
        """
        if section in self._configuration:
            return self._configuration[section]

    def create_config(self, section):
        """Initialize a new config section.

        The new section is a dictionary.

        :param section: The name of the new section.
        :type section: str

        Example::

            if mygame.config('high_scores') is None:
                mygame.create_config('high_scores')
            mygame.config('high_scores')['first_place'] = mygame.player.name
        """
        if self._configuration is None:
            self._configuration = {}
        if self._configuration_internals is None:
            self._configuration_internals = {}
        self._configuration[section] = {}
        self._configuration_internals[section] = {}

    def save_config(self, section=None, filename=None, append=False):
        """
        Save a configuration section.

        :param section: The name of the section to save on disk.
        :type section: str
        :param filename: The file to write in. If not provided it will write in the file
            that was used to load the given section. If section was not loaded from a
            file, save will raise an exception.
        :type filename: str
        :param append: Do we need to append to the file or replace the content
            (True = append, False = replace)
        :type append: bool

        Example::

            mygame.save_config('game_controls', 'data/game_controls.json')
        """
        if section is None:
            raise base.PglInvalidTypeException(
                "Game.save_config: section cannot be None."
            )
        elif section not in self._configuration:
            raise base.PglException(
                "unknown section", f"section {section} does not exists."
            )
        if (
            filename is None
            and "loaded_from" not in self._configuration_internals[section]
        ):
            raise base.PglInvalidTypeException(
                "filename cannot be None if section is new or was loaded manually."
            )
        elif filename is None:
            filename = self._configuration_internals[section]["loaded_from"]
        mode = "w"
        if append:
            mode = "a"
        with open(filename, mode) as file:
            json.dump(self._configuration[section], file)

    def add_board(self, level_number, board):
        """Add a board for the level number.

        This method associate a Board (:class:`pygamelib.engine.Board`) to a level
        number.

        Example::

            game.add_board(1,myboard)

        :param level_number: the level number to associate the board to.
        :type level_number: int
        :param board: a Board object corresponding to the level number.
        :type board: pygamelib.engine.Board

        :raises PglInvalidTypeException: If either of these parameters are not of the
            correct type.
        """
        if type(level_number) is int:
            if isinstance(board, Board):
                # Add the board to our list
                self._boards[level_number] = {
                    "board": board,
                    "npcs": [],
                    "projectiles": [],
                }
                # Taking ownership
                board.parent = self
            else:
                raise base.PglInvalidTypeException(
                    "The board paramater must be a pygamelib.engine.Board() object."
                )
        else:
            raise base.PglInvalidTypeException("The level number must be an int.")

    def get_board(self, level_number):
        """
        This method returns the board associated with a level number.
        :param level_number: The number of the level.
        :type level_number: int

        :raises PglInvalidTypeException: if the level_number is not an int.

        Example::

            level1_board = mygame.get_board(1)
        """
        if type(level_number) is int:
            return self._boards[level_number]["board"]
        else:
            raise base.PglInvalidTypeException("The level number must be an int.")

    def current_board(self):
        """
        This method return the board object corresponding to the current_level.

        Example::

            game.current_board().display()

        If current_level is set to a value with no corresponding board a PglException
        exception is raised with an invalid_level error.
        """
        if self.current_level in self._boards.keys():
            return self._boards[self.current_level]["board"]
        else:
            raise base.PglInvalidLevelException(
                "The current level does not correspond to any board."
            )

    def change_level(self, level_number):
        """
        Change the current level, load the board and place the player to the right
        place.

        Example::

            game.change_level(1)

        :param level_number: the level number to change to.
        :type level_number: int

        :raises base.PglInvalidTypeException: If parameter is not an int.
        """
        if type(level_number) is int:
            if self.player is None:
                raise base.PglException(
                    "undefined_player",
                    "Game.player is undefined. We cannot change level without a player."
                    " Please set player in your Game object: mygame.player = Player()",
                )
            # If it's not already the case, taking ownership of player
            if self.player.parent != self:
                self.player.parent = self
            if level_number in self._boards.keys():
                if self.player.pos[0] is not None or self.player.pos[1] is not None:
                    self._boards[self.current_level]["board"].clear_cell(
                        self.player.pos[0], self.player.pos[1]
                    )
                self.current_level = level_number
                b = self._boards[self.current_level]["board"]
                b.place_item(
                    self.player,
                    b.player_starting_position[0],
                    b.player_starting_position[1],
                )
            else:
                raise base.PglInvalidLevelException(
                    f"Impossible to change level to an unassociated level (level number"
                    f" {level_number} is not associated with any board).\nHave you "
                    f"called:\ngame.add_board({level_number},Board()) ?"
                )
        else:
            raise base.PglInvalidTypeException(
                "level_number needs to be an int in change_level(level_number)."
            )

    def add_npc(self, level_number, npc, row=None, column=None):
        """
        Add a NPC to the game. It will be placed on the board corresponding to the
        level_number. If row and column are not None, the NPC is placed at these
        coordinates. Else, it's randomly placed in an empty cell.

        Example::

            game.add_npc(1,my_evil_npc,5,2)

        :param level_number: the level number of the board.
        :type level_number: int
        :param npc: the NPC to place.
        :type npc: pygamelib.board_items.NPC
        :param row: the row coordinate to place the NPC at.
        :type row: int
        :param column: the column coordinate to place the NPC at.
        :type column: int

        If either of these parameters are not of the correct type, a
        PglInvalidTypeException exception is raised.

        .. Important:: If the NPC does not have an actuator, this method is going to
            affect a pygamelib.actuators.RandomActuator() to
            npc.actuator. And if npc.step == None, this method sets it to 1
        """
        if type(level_number) is int:
            if isinstance(npc, board_items.NPC):
                if row is None or column is None:
                    retry = 0
                    while True:
                        if row is None:
                            row = random.randint(
                                0, self._boards[level_number]["board"].size[1] - 1
                            )
                        if column is None:
                            column = random.randint(
                                0, self._boards[level_number]["board"].size[0] - 1
                            )
                        if isinstance(
                            self._boards[level_number]["board"].item(row, column),
                            board_items.BoardItemVoid,
                        ):
                            break
                        else:
                            row = None
                            column = None
                            retry += 1
                if type(row) is int:
                    if type(column) is int:
                        if npc.actuator is None:
                            npc.actuator = actuators.RandomActuator(
                                moveset=[
                                    constants.UP,
                                    constants.DOWN,
                                    constants.LEFT,
                                    constants.RIGHT,
                                ]
                            )
                        if npc.step is None:
                            npc.step = 1
                        self._boards[level_number]["board"].place_item(npc, row, column)
                        self._boards[level_number]["npcs"].append(npc)
                    else:
                        raise base.PglInvalidTypeException("column must be an int.")
                else:
                    raise base.PglInvalidTypeException("row must be an int.")
            else:
                raise base.PglInvalidTypeException(
                    "The npc paramater must be a pygamelib.board_items.NPC() object."
                )
        else:
            raise base.PglInvalidTypeException("The level number must be an int.")

    def actuate_npcs(self, level_number):
        """Actuate all NPCs on a given level

        This method actuate all NPCs on a board associated with a level. At the moment
        it means moving the NPCs but as the Actuators become more capable this method
        will evolve to allow more choice (like attack use objects, etc.)

        :param level_number: The number of the level to actuate NPCs in.
        :type int:

        Example::

            mygame.actuate_npcs(1)

        .. note:: This method only move NPCs when their actuator state is RUNNING. If it
            is PAUSED or STOPPED, theNPC is not moved.
        """
        if self.state == constants.RUNNING:
            if type(level_number) is int:
                if level_number in self._boards.keys():
                    for npc in self._boards[level_number]["npcs"]:
                        if npc.actuator.state == constants.RUNNING:
                            self._boards[level_number]["board"].move(
                                npc, npc.actuator.next_move(), npc.step
                            )
                else:
                    raise base.PglInvalidLevelException(
                        f"Impossible to actuate NPCs for this level (level number "
                        f"{level_number} is not associated with any board)."
                    )
            else:
                raise base.PglInvalidTypeException(
                    "In actuate_npcs(level_number) the level_number must be an int."
                )

    def add_projectile(self, level_number, projectile, row=None, column=None):
        """
        Add a Projectile to the game. It will be placed on the board corresponding to
        level_number. Neither row nor column can be None.

        Example::

            game.add_projectile(1, fireball, 5, 2)

        :param level_number: the level number of the board.
        :type level_number: int
        :param projectile: the Projectile to place.
        :type projectile: :class:`~pygamelib.board_items.Projectile`
        :param row: the row coordinate to place the Projectile at.
        :type row: int
        :param column: the column coordinate to place the Projectile at.
        :type column: int

        If either of these parameters are not of the correct type, a
        PglInvalidTypeException exception is raised.

        .. Important:: If the Projectile does not have an actuator, this method is going
            to affect pygamelib.actuators.RandomActuator(moveset=[RIGHT])
            to projectile.actuator. And if projectile.step == None, this method sets it
            to 1.
        """
        if type(level_number) is int:
            if isinstance(projectile, board_items.Projectile):
                if row is None or column is None:
                    raise base.PglInvalidTypeException(
                        "In Game.add_projectile neither row nor column can be None."
                    )
                if type(row) is int:
                    if type(column) is int:
                        # If we're trying to send a projectile out of the board's bounds
                        # We do nothing and return.
                        if (
                            row >= self._boards[level_number]["board"].size[1]
                            or column >= self._boards[level_number]["board"].size[0]
                            or row < 0
                            or column < 0
                        ):
                            return
                        # If there is something were we should put the projectile,
                        # then we consider it an immediate hit.
                        check_object = self._boards[level_number]["board"].item(
                            row, column
                        )
                        if not isinstance(check_object, board_items.BoardItemVoid):
                            if projectile.is_aoe:
                                # AoE is easy, just return everything in range
                                projectile.hit(
                                    self.neighbors(projectile.aoe_radius, check_object)
                                )
                                return
                            else:
                                projectile.hit([check_object])
                                return
                        if projectile.actuator is None:
                            projectile.actuator = actuators.RandomActuator(
                                moveset=[constants.RIGHT]
                            )
                        if projectile.step is None:
                            projectile.step = 1
                        self._boards[level_number]["board"].place_item(
                            projectile, row, column
                        )
                        self._boards[level_number]["projectiles"].append(projectile)
                    else:
                        raise base.PglInvalidTypeException("column must be an int.")
                else:
                    raise base.PglInvalidTypeException("row must be an int.")
            else:
                raise base.PglInvalidTypeException(
                    "The projectile paramater must be a "
                    "pygamelib.board_items.Projectile() object."
                )
        else:
            raise base.PglInvalidTypeException("The level number must be an int.")

    def remove_npc(self, level_number, npc):
        """This methods remove the NPC from the level in parameter.

        :param level: The number of the level from where the NPC is to be removed.
        :type level: int
        :param npc: The NPC object to remove.
        :type npc: :class:`~pygamelib.board_items.NPC`

        Example::

            mygame.remove_npc(1, dead_npc)
        """
        self._boards[level_number]["npcs"].remove(npc)
        self.current_board().clear_cell(npc.pos[0], npc.pos[1])

    def actuate_projectiles(self, level_number):
        """Actuate all Projectiles on a given level

        This method actuate all Projectiles on a board associated with a level.
        This method differs from actuate_npcs() as some logic is involved with
        projectiles that NPC do not have.
        This method decrease the available range by projectile.step each time it's
        called.
        It also detects potential collisions.
        If the available range falls to 0 or a collision is detected the projectile
        hit_callback is called.

        :param level_number: The number of the level to actuate Projectiles in.
        :type int:

        Example::

            mygame.actuate_projectiles(1)

        .. note:: This method only move Projectiles when their actuator state is
            RUNNING. If it is PAUSED or STOPPED, the Projectile is not moved.
        """
        if self.state == constants.RUNNING:
            if type(level_number) is int:
                if level_number in self._boards.keys():
                    board = self._boards[level_number]["board"]
                    for proj in self._boards[level_number]["projectiles"]:
                        if proj.actuator.state == constants.RUNNING:
                            if proj.range > 0:
                                init_position = proj.pos
                                direction = proj.actuator.next_move()
                                board.move(proj, direction, proj.step)
                                proj.range -= proj.step
                                # If range was positive and position did not change
                                # it means something is blocking the projectile path
                                # in other words: we detected a collision.
                                if proj.pos == init_position:
                                    if proj.is_aoe:
                                        # AoE is easy, just return everything in range
                                        proj.hit(self.neighbors(proj.aoe_radius, proj))
                                    else:
                                        # directional hit requires us to get the item
                                        # that blocked our path
                                        proj.hit([board_items.BoardItemVoid()])
                                        new_x = None
                                        new_y = None
                                        if direction == constants.UP:
                                            new_x = proj.pos[0] - proj.step
                                            new_y = proj.pos[1]
                                        elif direction == constants.DOWN:
                                            new_x = proj.pos[0] + proj.step
                                            new_y = proj.pos[1]
                                        elif direction == constants.LEFT:
                                            new_x = proj.pos[0]
                                            new_y = proj.pos[1] - proj.step
                                        elif direction == constants.RIGHT:
                                            new_x = proj.pos[0]
                                            new_y = proj.pos[1] + proj.step
                                        elif direction == constants.DRUP:
                                            new_x = proj.pos[0] - proj.step
                                            new_y = proj.pos[1] + proj.step
                                        elif direction == constants.DRDOWN:
                                            new_x = proj.pos[0] + proj.step
                                            new_y = proj.pos[1] + proj.step
                                        elif direction == constants.DLUP:
                                            new_x = proj.pos[0] - proj.step
                                            new_y = proj.pos[1] - proj.step
                                        elif direction == constants.DLDOWN:
                                            new_x = proj.pos[0] + proj.step
                                            new_y = proj.pos[1] - proj.step
                                        if (
                                            new_x is not None
                                            and new_y is not None
                                            and new_x >= 0
                                            and new_y >= 0
                                            and new_x < board.size[1]
                                            and new_y < board.size[0]
                                        ):
                                            proj.hit([board.item(new_x, new_y)])
                            elif proj.range == 0:
                                if proj.is_aoe:
                                    proj.hit(self.neighbors(proj.aoe_radius, proj))
                                else:
                                    proj.hit([board_items.BoardItemVoid()])
                            else:
                                self._boards[level_number]["projectiles"].remove(proj)
                                board.clear_cell(proj.pos[0], proj.pos[1])
                        elif proj.actuator.state == constants.STOPPED:
                            self._boards[level_number]["projectiles"].remove(proj)
                            board.clear_cell(proj.pos[0], proj.pos[1])
                else:
                    raise base.PglInvalidLevelException(
                        f"Impossible to actuate NPCs for this level (level number "
                        f"{level_number} is not associated with any board)."
                    )
            else:
                raise base.PglInvalidTypeException(
                    "In actuate_npcs(level_number) the level_number must be an int."
                )

    def animate_items(self, level_number):
        """That method goes through all the BoardItems of a given map and call
        Animation.next_frame()
        :param level_number: The number of the level to animate items in.
        :type level_number: int

        :raise: :class:`pygamelib.base.PglInvalidLevelException`
            class:`pygamelib.base.PglInvalidTypeException`

        Example::

            mygame.animate_items(1)
        """
        if self.state == constants.RUNNING:
            if type(level_number) is int:
                if level_number in self._boards.keys():
                    for item in self._boards[level_number]["board"].get_immovables():
                        if item.animation is not None:
                            item.animation.next_frame()
                    for item in self._boards[level_number]["board"].get_movables():
                        if item.animation is not None:
                            item.animation.next_frame()
                else:
                    raise base.PglInvalidLevelException(
                        "Impossible to animate items for this level (level number "
                        f"{level_number} is not associated with any board)."
                    )
            else:
                raise base.PglInvalidTypeException(
                    "In animate_items(level_number) the level_number must be an int."
                )

    def display_player_stats(
        self, life_model=graphics.RED_RECT, void_model=graphics.BLACK_RECT
    ):
        """Display the player name and health.

        This method print the Player name, a health bar (20 blocks of life_model). When
        life is missing the complement (20-life missing) is printed using void_model.
        It also display the inventory value as "Score".

        :param life_model: The character(s) that should be used to represent the
            *remaining* life.
        :type life_model: str
        :param void_model: The character(s) that should be used to represent the
            *lost* life.
        :type void_model: str

        .. note:: This method might change in the future. Particularly it could take a
            template of what to display.

        """
        if self.player is None:
            return ""
        info = ""
        info += f" {self.player.name}"
        nb_blocks = int((self.player.hp / self.player.max_hp) * 20)
        info += " [" + life_model * nb_blocks + void_model * (20 - nb_blocks) + "]"
        info += "     Score: " + str(self.player.inventory.value())
        print(info)

    def move_player(self, direction, step):
        """
        Easy wrapper for Board.move().

        Example::

            mygame.move_player(constants.RIGHT,1)
        """
        if self.state == constants.RUNNING:
            self._boards[self.current_level]["board"].move(self.player, direction, step)

    def display_board(self):
        """Display the current board.

        The behavior of that function is dependant on how you configured this object.
        If you set enable_partial_display to True AND partial_display_viewport is set
        to a correct value, it will call Game.current_board().display_around() with the
        correct parameters.
        The partial display will be centered on the player (Game.player).
        Otherwise it will just call Game.current_board().display().

        Example::

            mygame.enable_partial_display = True
            # Number of rows, number of column (on each side, total viewport
            # will be 20x20 in that case).
            mygame.partial_display_viewport = [10, 10]
            # This will call Game.current_board().display_around()
            mygame.display()
            mygame.enable_partial_display = False
            # This will call Game.current_board().display()
            mygame.display()
        """
        if (
            self.enable_partial_display
            and self.partial_display_viewport is not None
            and type(self.partial_display_viewport) is list
        ):
            # display_around(self, object, p_row, p_col)
            self.current_board().display_around(
                self.player,
                self.partial_display_viewport[0],
                self.partial_display_viewport[1],
            )
        else:
            self.current_board().display()

    def neighbors(self, radius=1, object=None):
        """Get a list of neighbors (non void item) around an object.

        This method returns a list of objects that are all around an object between the
        position of an object and all the cells at **radius**.

        :param radius: The radius in which non void item should be included
        :type radius: int
        :param object: The central object. The neighbors are calculated for that object.
            If None, the player is the object.
        :type object: pygamelib.board_items.BoardItem
        :return: A list of BoardItem. No BoardItemVoid is included.
        :raises PglInvalidTypeException: If radius is not an int.

        Example::

            for item in game.neighbors(2):
                print(f'{item.name} is around player at coordinates '
                    '({item.pos[0]},{item.pos[1]})')
        """
        if type(radius) is not int:
            raise base.PglInvalidTypeException(
                "In Game.neighbors(radius), radius must be an integer."
            )
        if object is None:
            object = self.player
        return_array = []
        for x in range(-radius, radius + 1, 1):
            for y in range(-radius, radius + 1, 1):
                if x == 0 and y == 0:
                    continue
                true_x = object.pos[0] + x
                true_y = object.pos[1] + y
                if (
                    true_x < self.current_board().size[1]
                    and true_y < self.current_board().size[0]
                ) and not isinstance(
                    self.current_board().item(true_x, true_y), board_items.BoardItemVoid
                ):
                    return_array.append(self.current_board().item(true_x, true_y))
        return return_array

    def load_board(self, filename, lvl_number=0):
        """Load a saved board

        Load a Board saved on the disk as a JSON file. This method creates a new Board
        object, populate it with all the elements (except a Player) and then return it.

        If the filename argument is not an existing file, the open function is going to
        raise an exception.

        This method, load the board from the JSON file, populate it with all BoardItem
        included, check for sanity, init the board with BoardItemVoid and then associate
        the freshly created board to a lvl_number.
        It then create the NPCs and add them to the board.

        :param filename: The file to load
        :type filename: str
        :param lvl_number: The level number to associate the board to. Default is 0.
        :type lvl_number: int
        :returns: a newly created board (see :class:`pygamelib.engine.Board`)

        Example::

            mynewboard = game.load_board( 'awesome_level.json', 1 )
            game.change_level( 1 )
        """
        with open(filename, "r") as f:
            data = json.load(f)
        local_board = Board()
        data_keys = data.keys()
        if "name" in data_keys:
            local_board.name = data["name"]
        if "size" in data_keys:
            local_board.size = data["size"]
        if "player_starting_position" in data_keys:
            local_board.player_starting_position = data["player_starting_position"]
        if "ui_border_top" in data_keys:
            local_board.ui_border_top = data["ui_border_top"]
        if "ui_border_bottom" in data_keys:
            local_board.ui_border_bottom = data["ui_border_bottom"]
        if "ui_border_left" in data_keys:
            local_board.ui_border_left = data["ui_border_left"]
        if "ui_border_right" in data_keys:
            local_board.ui_border_right = data["ui_border_right"]
        if "ui_board_void_cell" in data_keys:
            local_board.ui_board_void_cell = data["ui_board_void_cell"]
        # Now we need to recheck for board sanity
        local_board.check_sanity()
        # and re-initialize the board (mainly to attribute a new model to the void cells
        # as it's not dynamic).
        local_board.init_board()
        # Then add board to the game
        self.add_board(lvl_number, local_board)

        # Now load the library if any
        if "library" in data_keys:
            self.object_library = []
            for e in data["library"]:
                self.object_library.append(Game._ref2obj(e))
        # Now let's place the good stuff on the board
        if "map_data" in data_keys:
            for pos_x in data["map_data"].keys():
                x = int(pos_x)
                for pos_y in data["map_data"][pos_x].keys():
                    y = int(pos_y)
                    ref = data["map_data"][pos_x][pos_y]
                    obj_keys = ref.keys()
                    if "object" in obj_keys:
                        o = Game._ref2obj(ref)
                        if not isinstance(o, board_items.NPC) and not isinstance(
                            o, board_items.BoardItemVoid
                        ):
                            local_board.place_item(o, x, y)
                        elif isinstance(o, board_items.NPC):
                            self.add_npc(lvl_number, o, x, y)
                            if isinstance(o.actuator, actuators.PathFinder):
                                o.actuator.game = self
                                o.actuator.add_waypoint(x, y)

                    else:
                        base.Text.warn(
                            f"while loading the board in {filename}, at coordinates "
                            f'[{pos_x},{pos_y}] there is an entry without "object" '
                            "attribute. NOT LOADED."
                        )
        return local_board

    def save_board(self, lvl_number, filename):
        """Save a board to a JSON file

        This method saves a Board and everything in it but the BoardItemVoid.

        Not check are done on the filename, if anything happen you get the exceptions
        from open().

        :param lvl_number: The level number to get the board from.
        :type lvl_number: int
        :param filename: The path to the file to save the data to.
        :type filename: str

        :raises PglInvalidTypeException: If any parameter is not of the right type
        :raises PglInvalidLevelException: If the level is not associated with a Board.

        Example::

            game.save_board( 1, 'hac-maps/level1.json')

        If Game.object_library is not an empty array, it will be saved also.
        """
        if type(lvl_number) is not int:
            raise base.PglInvalidTypeException(
                "lvl_number must be an int in Game.save_board()"
            )
        if type(filename) is not str:
            raise base.PglInvalidTypeException(
                "filename must be a str in Game.save_board()"
            )
        if lvl_number not in self._boards:
            raise base.PglInvalidLevelException(
                f"lvl_number {lvl_number}"
                " does not correspond to any level associated with a board in "
                "Game.save_board()"
            )

        data = {}
        local_board = self._boards[lvl_number]["board"]
        data["name"] = local_board.name
        data["player_starting_position"] = local_board.player_starting_position
        data["ui_border_left"] = local_board.ui_border_left
        data["ui_border_right"] = local_board.ui_border_right
        data["ui_border_top"] = local_board.ui_border_top
        data["ui_border_bottom"] = local_board.ui_border_bottom
        data["ui_board_void_cell"] = local_board.ui_board_void_cell
        data["size"] = local_board.size
        data["map_data"] = {}

        if len(self.object_library) > 0:
            data["library"] = []
            for o in self.object_library:
                data["library"].append(Game._obj2ref(o))

        # Now we need to run through all the cells to store
        # anything that is not a BoardItemVoid
        for x in self.current_board()._matrix:
            for y in x:
                if not isinstance(y, board_items.BoardItemVoid) and not isinstance(
                    y, board_items.Player
                ):
                    # print(f"Item: name={y.name} pos={y.pos} type={y.type}")
                    if str(y.pos[0]) not in data["map_data"].keys():
                        data["map_data"][str(y.pos[0])] = {}

                    data["map_data"][str(y.pos[0])][str(y.pos[1])] = Game._obj2ref(y)
        with open(filename, "w") as f:
            json.dump(data, f)

    def start(self):
        """Set the game engine state to RUNNING.

        The game has to be RUNNING for actuate_npcs() and move_player() to do anything.

        Example::

            mygame.start()
        """
        self.state = constants.RUNNING

    def pause(self):
        """Set the game engine state to PAUSE.

        Example::

            mygame.pause()
        """
        self.state = constants.PAUSED

    def stop(self):

        """Set the game engine state to STOPPED.

        Example::

            mygame.stop()
        """
        self.state = constants.STOPPED

    # Here are some utility functions not really meant to be used outside of the Game
    # object itself.
    @staticmethod
    def _obj2ref(obj):
        ref = {
            "object": str(obj.__class__),
            "name": obj.name,
            "pos": obj.pos,
            "model": obj.model,
            "type": obj.type,
        }

        if isinstance(obj, board_items.Wall):
            ref["inventory_space"] = obj.inventory_space()
        elif isinstance(obj, board_items.Treasure):
            ref["value"] = obj.value
            ref["inventory_space"] = obj.inventory_space()
        elif isinstance(obj, board_items.GenericActionableStructure) or isinstance(
            obj, board_items.GenericStructure
        ):
            ref["value"] = obj.value
            ref["inventory_space"] = obj.inventory_space()
            ref["overlappable"] = obj.overlappable()
            ref["pickable"] = obj.pickable()
            ref["restorable"] = obj.restorable()
        elif isinstance(obj, board_items.Door):
            ref["value"] = obj.value
            ref["inventory_space"] = obj.inventory_space()
            ref["overlappable"] = obj.overlappable()
            ref["pickable"] = obj.pickable()
            ref["restorable"] = obj.restorable()
        elif isinstance(obj, board_items.NPC):
            ref["hp"] = obj.hp
            ref["max_hp"] = obj.max_hp
            ref["step"] = obj.step
            ref["remaining_lives"] = obj.remaining_lives
            ref["attack_power"] = obj.attack_power
            if obj.actuator is not None:
                if isinstance(obj.actuator, actuators.RandomActuator):
                    ref["actuator"] = {
                        "type": "RandomActuator",
                        "moveset": obj.actuator.moveset,
                    }
                elif isinstance(obj.actuator, actuators.PatrolActuator):
                    ref["actuator"] = {
                        "type": "PatrolActuator",
                        "path": obj.actuator.path,
                    }
                elif isinstance(obj.actuator, actuators.PathActuator):
                    ref["actuator"] = {
                        "type": "PathActuator",
                        "path": obj.actuator.path,
                    }
                elif isinstance(obj.actuator, actuators.PathFinder):
                    ref["actuator"] = {
                        "type": "PathFinder",
                        "waypoints": obj.actuator.waypoints,
                        "circle_waypoints": obj.actuator.circle_waypoints,
                    }
        return ref

    @staticmethod
    def _string_to_constant(s):
        if type(s) is int:
            return s
        elif s == "UP":
            return constants.UP
        elif s == "DOWN":
            return constants.DOWN
        elif s == "RIGHT":
            return constants.RIGHT
        elif s == "LEFT":
            return constants.LEFT
        elif s == "DRUP":
            return constants.DRUP
        elif s == "DRDOWN":
            return constants.DRDOWN
        elif s == "DLDOWN":
            return constants.DLDOWN
        elif s == "DLUP":
            return constants.DLUP

    @staticmethod
    def _ref2obj(ref):
        obj_keys = ref.keys()
        local_object = board_items.BoardItemVoid()
        if "Wall" in ref["object"]:
            local_object = board_items.Wall()
        elif "Treasure" in ref["object"]:
            local_object = board_items.Treasure()
            if "value" in obj_keys:
                local_object.value = ref["value"]
            # size is deprecated in favor of inventory_space.
            # This is kept for backward compatibility and silent migration.
            if "size" in obj_keys:
                local_object._inventory_space = ref["size"]
            if "inventory_space" in obj_keys:
                local_object._inventory_space = ref["inventory_space"]
        elif "GenericStructure" in ref["object"]:
            local_object = board_items.GenericStructure()
            if "value" in obj_keys:
                local_object.value = ref["value"]
            # size is deprecated in favor of inventory_space.
            # This is kept for backward compatibility and silent migration.
            if "size" in obj_keys:
                local_object._inventory_space = ref["size"]
            if "inventory_space" in obj_keys:
                local_object._inventory_space = ref["inventory_space"]
            if "pickable" in obj_keys:
                local_object.set_pickable(ref["pickable"])
            if "overlappable" in obj_keys:
                local_object.set_overlappable(ref["overlappable"])
        elif "Door" in ref["object"]:
            local_object = board_items.Door()
            if "value" in obj_keys:
                local_object.value = ref["value"]
            # size is deprecated in favor of inventory_space.
            # This is kept for backward compatibility and silent migration.
            if "size" in obj_keys:
                local_object._inventory_space = ref["size"]
            if "inventory_space" in obj_keys:
                local_object._inventory_space = ref["inventory_space"]
            if "pickable" in obj_keys:
                local_object.set_pickable(ref["pickable"])
            if "overlappable" in obj_keys:
                local_object.set_overlappable(ref["overlappable"])
            if "restorable" in obj_keys:
                local_object.set_restorable(ref["restorable"])
        elif "GenericActionableStructure" in ref["object"]:
            local_object = board_items.GenericActionableStructure()
            if "value" in obj_keys:
                local_object.value = ref["value"]
            # size is deprecated in favor of inventory_space.
            # This is kept for backward compatibility and silent migration.
            if "size" in obj_keys:
                local_object._inventory_space = ref["size"]
            if "inventory_space" in obj_keys:
                local_object._inventory_space = ref["inventory_space"]
            if "pickable" in obj_keys:
                local_object.set_pickable(ref["pickable"])
            if "overlappable" in obj_keys:
                local_object.set_overlappable(ref["overlappable"])
        elif "NPC" in ref["object"]:
            local_object = board_items.NPC()
            if "value" in obj_keys:
                local_object.value = ref["value"]
            # size is deprecated in favor of inventory_space.
            # This is kept for backward compatibility and silent migration.
            if "size" in obj_keys:
                local_object._inventory_space = ref["size"]
            if "inventory_space" in obj_keys:
                local_object._inventory_space = ref["inventory_space"]
            if "hp" in obj_keys:
                local_object.hp = ref["hp"]
            if "max_hp" in obj_keys:
                local_object.max_hp = ref["max_hp"]
            if "step" in obj_keys:
                local_object.step = ref["step"]
            if "remaining_lives" in obj_keys:
                local_object.remaining_lives = ref["remaining_lives"]
            if "attack_power" in obj_keys:
                local_object.attack_power = ref["attack_power"]
            if "actuator" in obj_keys:
                if "RandomActuator" in ref["actuator"]["type"]:
                    local_object.actuator = actuators.RandomActuator(moveset=[])
                    if "moveset" in ref["actuator"].keys():
                        for m in ref["actuator"]["moveset"]:
                            local_object.actuator.moveset.append(
                                Game._string_to_constant(m)
                            )
                elif "PathActuator" in ref["actuator"]["type"]:
                    local_object.actuator = actuators.PathActuator(path=[])
                    if "path" in ref["actuator"].keys():
                        for m in ref["actuator"]["path"]:
                            local_object.actuator.path.append(
                                Game._string_to_constant(m)
                            )
                elif "PatrolActuator" in ref["actuator"]["type"]:
                    local_object.actuator = actuators.PatrolActuator(path=[])
                    if "path" in ref["actuator"].keys():
                        for m in ref["actuator"]["path"]:
                            local_object.actuator.path.append(
                                Game._string_to_constant(m)
                            )
                elif "PathFinder" in ref["actuator"]["type"]:
                    local_object.actuator = actuators.PathFinder(
                        game=Game(), parent=local_object
                    )
                    if "circle_waypoints" in ref["actuator"].keys():
                        local_object.actuator.circle_waypoints = ref["actuator"][
                            "circle_waypoints"
                        ]
                    if "waypoints" in ref["actuator"].keys():
                        for m in ref["actuator"]["waypoints"]:
                            local_object.actuator.add_waypoint(m[0], m[1])
        # Now what remains is what is common to all BoardItem
        if not isinstance(local_object, board_items.BoardItemVoid):
            if "name" in obj_keys:
                local_object.name = ref["name"]
            if "model" in obj_keys:
                local_object.model = ref["model"]
            if "type" in obj_keys:
                local_object.type = ref["type"]
        return local_object


class Inventory:
    """A class that represent the Player (or NPC) inventory.

    This class is pretty straightforward: it is an object container, you can add, get
    and remove items and you can get a value from the objects in the inventory.

    The constructor takes only one parameter: the maximum size of the inventory. Each
    :class:`~pygamelib.board_items.BoardItem` that is going to be put in the inventory
    has a size (default is 1), the total addition of all these size cannot exceed
    max_size.

    :param max_size: The maximum size of the inventory. Deafult value: 10.
    :type max_size: int
    :param parent: The parent object (usually a BoardItem).

    .. note:: You can print() the inventory. This is mostly useful for debug as you want
        to have a better display in your game.

    .. warning:: The :class:`~pygamelib.engine.Game` engine and
        :class:`~pygamelib.board_items.Player` takes care to initiate an inventory for
        the player, you don't need to do it.

    """

    def __init__(self, max_size=10, parent=None):
        self.max_size = max_size
        self.__items = {}
        self.parent = parent

    def __str__(self):
        s = "=============\n"
        s += "= inventory =\n"
        s += "============="
        types = {}
        for k in self.__items.keys():
            if self.__items[k].type in types.keys():
                types[self.__items[k].type]["size"] += self.__items[k].inventory_space()
            else:
                types[self.__items[k].type] = {
                    "size": self.__items[k].inventory_space(),
                    "model": self.__items[k].model,
                }
        for k in types.keys():
            s += f"\n{types[k]['model']} : {types[k]['size']}"
        return s

    def add_item(self, item):
        """Add an item to the inventory.

        This method will add an item to the inventory unless:

         * it is not an instance of :class:`~pygamelib.board_items.BoardItem`,
         * you try to add an item that is not pickable,
         * there is no more space left in the inventory (i.e: the cumulated size of the
           inventory + your item.size is greater than the inventory max_size)

        :param item: the item you want to add
        :type item: :class:`~pygamelib.board_items.BoardItem`
        :raises: PglInventoryException, PglInvalidTypeException

        Example::

            item = Treasure(model=Sprites.MONEY_BAG,size=2,name='Money bag')
            try:
                mygame.player.inventory.add_item(item)
            expect PglInventoryException as e:
                if e.error == 'not_enough_space':
                    print(f"Impossible to add {item.name} to the inventory, there is no"
                    "space left in it!")
                    print(e.message)
                elif e.error == 'not_pickable':
                    print(e.message)

        .. warning:: if you try to add more than one item with the same name (or if the
            name is empty), this function will automatically change the name of the item
            by adding a UUID to it.

        """
        if isinstance(item, board_items.BoardItem):
            if item.pickable():
                if (
                    item.name is None
                    or item.name == ""
                    or item.name in self.__items.keys()
                ):
                    item.name += "_" + uuid.uuid4().hex
                if (
                    hasattr(item, "_inventory_space")
                    and self.max_size >= self.size() + item.inventory_space()
                ):
                    self.__items[item.name] = item
                else:
                    raise base.PglInventoryException(
                        "not_enough_space",
                        "There is not enough space left in the inventory. Max. size: "
                        + str(self.max_size)
                        + ", current inventory size: "
                        + str(self.size())
                        + " and item size: "
                        + str(item.inventory_space()),
                    )
            else:
                raise base.PglInventoryException(
                    "not_pickable",
                    f"The item (name='{item.name}') is not pickable. Make sure to only "
                    "add pickable objects to the inventory.",
                )
        else:
            raise base.PglInvalidTypeException(
                "The item is not an instance of BoardItem. The item is of type: "
                + type(item)
            )

    def size(self):
        """
        Return the cumulated size of the inventory.
        It can be used in the UI to display the size compared to max_size for example.

        :return: size of inventory
        :rtype: int

        Example::

            print(f"Inventory: {mygame.player.inventory.size()}/"
            "{mygame.player.inventory.max_size}")
        """
        val = 0
        for k in self.__items.keys():
            if hasattr(self.__items[k], "_inventory_space"):
                val += self.__items[k].inventory_space()
        return val

    def empty(self):
        """Empty the inventory
        Example::

            if inventory.size() > 0:
                inventory.empty()
        """
        self.__items = {}

    def value(self):
        """
        Return the cumulated value of the inventory.
        It can be used for scoring for example.

        :return: value of inventory
        :rtype: int

        Example::

            if inventory.value() >= 10:
                print('Victory!')
                break
        """
        val = 0
        for k in self.__items.keys():
            if hasattr(self.__items[k], "value"):
                val += self.__items[k].value
        return val

    def items_name(self):
        """Return the list of all items names in the inventory.

        :return: a list of string representing the items names.
        :rtype: list

        """
        return self.__items.keys()

    def search(self, query):
        """Search for objects in the inventory.

        All objects that matches the query are going to be returned.
        :param query: the query that items in the inventory have to match to be returned
        :type name: str
        :returns: a table of BoardItems.
        :rtype: list

        Example::

            for item in game.player.inventory.search('mighty'):
                print(f"This is a mighty item: {item.name}")
        """
        return [item for ikey, item in self.__items.items() if query in ikey]

    def get_item(self, name):
        """Return the item corresponding to the name given in argument.

        :param name: the name of the item you want to get.
        :type name: str
        :return: An item.
        :rtype: :class:`~pygamelib.board_items.BoardItem`
        :raises: PglInventoryException

        .. note:: in case an execpetion is raised, the error will be
            'no_item_by_that_name' and the message is giving the specifics.

        .. seealso:: :class:`pygamelib.base.PglInventoryException`.

        Example::

            life_container = mygame.player.inventory.get_item('heart_1')
            if isinstance(life_container,GenericActionableStructure):
                life_container.action(life_container.action_parameters)

        .. note:: Please note that the item object reference is returned but nothing is
            changed in the inventory. The item hasn't been removed.

        """
        if name in self.__items.keys():
            return self.__items[name]
        else:
            raise base.PglInventoryException(
                "no_item_by_that_name",
                f'There is no item named "{name}" in the inventory.',
            )

    def delete_item(self, name):
        """Delete the item corresponding to the name given in argument.

        :param name: the name of the item you want to delete.
        :type name: str

        .. note:: in case an execpetion is raised, the error will be
            'no_item_by_that_name' and the message is giving the specifics.

        .. seealso:: :class:`pygamelib.base.PglInventoryException`.

        Example::

            life_container = mygame.player.inventory.get_item('heart_1')
            if isinstance(life_container,GenericActionableStructure):
                life_container.action(life_container.action_parameters)
                mygame.player.inventory.delete_item('heart_1')

        """
        if name in self.__items.keys():
            del self.__items[name]
        else:
            raise base.PglInventoryException(
                "no_item_by_that_name",
                f'There is no item named "{name}" in the inventory.',
            )