from enum import Enum


class FormationType(Enum):
    """
    FormationType

    Attributes:
        THREE_ONE_TWO_ONE_THREE (str): 3-1-2-1-3 team formation
        THREE_ONE_THREE_ONE_TWO (str):
        THREE_ONE_FOUR_TWO (str):
        THREE_TWO_TWO_ONE_TWO (str):
        THREE_TWO_TWO_TWO_ONE (str):
        THREE_TWO_THREE_TWO (str):
        THREE_THREE_TWO_TWO (str):
        THREE_TWO_FOUR_ONE (str):
        THREE_THREE_THREE_ONE (str):
        THREE_FOUR_ONE_TWO (str):
        THREE_FOUR_TWO_ONE (str):
        THREE_FOUR_THREE (str):
        THREE_FOUR_THREE_DIAMOND (str):
        THREE_FIVE_ONE_ONE (str):
        THREE_FIVE_TWO (str):
        FOUR_ONE_TWO_ONE_TWO (str):
        FOUR_ONE_TWO_TWO_ONE (str):
        FOUR_ONE_THREE_TWO (str):
        FOUR_ONE_FOUR_ONE (str):
        FOUR_TWO_ONE_TWO_ONE (str):
        FOUR_TWO_TWO_ONE_ONE (str):
        FOUR_TWO_TWO_TWO (str):
        FOUR_TWO_THREE_ONE (str):
        FOUR_TWO_FOUR_ZERO (str):
        FOUR_THREE_ONE_TWO (str):
        FOUR_THREE_TWO_ONE (str):
        FOUR_THREE_THREE (str):
        FOUR_FOUR_ONE_ONE (str):
        FOUR_FOUR_TWO (str):
        FOUR_FIVE_ONE (str):
        FIVE_TWO_TWO_ONE (str):
        FIVE_THREE_TWO (str):
        FIVE_FOUR_ONE (str):

    """

    THREE_ONE_TWO_ONE_THREE = "3-1-2-1-3"
    THREE_ONE_THREE_ONE_TWO = "3-1-3-1-2"
    THREE_ONE_FOUR_TWO = "3-1-4-2"
    THREE_TWO_TWO_ONE_TWO = "3-2-2-1-2"
    THREE_TWO_TWO_TWO_ONE = "3-2-2-2-1"
    THREE_TWO_THREE_TWO = "3-2-3-2"
    THREE_THREE_TWO_TWO = "3-3-2-2"
    THREE_TWO_FOUR_ONE = "3-2-4-1"
    THREE_THREE_THREE_ONE = "3-3-3-1"
    THREE_FOUR_ONE_TWO = "3-4-1-2"
    THREE_FOUR_TWO_ONE = "3-4-2-1"
    THREE_FOUR_THREE = "3-4-3"
    THREE_FOUR_THREE_DIAMOND = "3-4-3-d"
    THREE_FIVE_ONE_ONE = "3-5-1-1"
    THREE_FIVE_TWO = "3-5-2"
    FOUR_ONE_TWO_ONE_TWO = "4-1-2-1-2"
    FOUR_ONE_TWO_TWO_ONE = "4-1-2-2-1"
    FOUR_ONE_THREE_TWO = "4-1-3-2"
    FOUR_ONE_FOUR_ONE = "4-1-4-1"
    FOUR_TWO_ONE_TWO_ONE = "4-2-1-2-1"
    FOUR_TWO_TWO_ONE_ONE = "4-2-2-1-1"
    FOUR_TWO_TWO_TWO = "4-2-2-2"
    FOUR_TWO_THREE_ONE = "4-2-3-1"
    FOUR_TWO_FOUR_ZERO = "4-2-4-0"
    FOUR_THREE_ONE_TWO = "4-3-1-2"
    FOUR_THREE_TWO_ONE = "4-3-2-1"
    FOUR_THREE_THREE = "4-3-3"
    FOUR_FOUR_ONE_ONE = "4-4-1-1"
    FOUR_FOUR_TWO = "4-4-2"
    FOUR_FIVE_ONE = "4-5-1"
    FIVE_TWO_TWO_ONE = "5-2-2-1"
    FIVE_THREE_TWO = "5-3-2"
    FIVE_FOUR_ONE = "5-4-1"

    def __str__(self):
        return self.value
